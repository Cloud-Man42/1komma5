"""Isolated module runtime manager."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from energy_core.config import Settings
from energy_core.db.installed_package_repo import InstalledPackageRepository
from energy_core.platform.modules.governance.evaluation_service import GovernanceEvaluationService
from energy_core.platform.modules.governance.policy_engine import ModuleInstallPolicyEngine
from energy_core.platform.modules.governance.types import PolicyAction
from energy_core.platform.modules.isolation.policy import requires_isolated_runtime, runtime_blocked_reason, tier_allows_runtime
from energy_core.platform.modules.isolation.repository import IsolatedRuntimeRepository
from energy_core.platform.modules.isolation.rpc.gateway import ModuleRpcGateway
from energy_core.platform.modules.isolation.security_monitor import RuntimeSecurityMonitor
from energy_core.platform.modules.isolation.supervisor import RuntimeSupervisor
from energy_core.platform.modules.isolation.sandbox import build_sandbox_launcher
from energy_core.platform.modules.isolation.sandbox.base import SandboxLaunchSpec, SandboxProcess
from energy_core.platform.modules.isolation.types import (
    IsolatedRuntimeState,
    RuntimeEventType,
    RuntimeStartRequest,
    RuntimeStartResult,
)
from energy_core.platform.modules.packages.integrity import compute_package_content_sha256
from energy_core.platform.modules.registry import ModuleDescriptor, default_module_registry

logger = logging.getLogger(__name__)


class IsolatedModuleRuntimeManager:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        *,
        rpc_gateway: ModuleRpcGateway | None = None,
    ) -> None:
        self._session = session
        self._settings = settings
        self._repo = IsolatedRuntimeRepository(session)
        self._launcher = build_sandbox_launcher(settings)
        self._processes: dict[str, SandboxProcess] = {}
        self._supervisor = RuntimeSupervisor(settings)
        self._security_monitor = RuntimeSecurityMonitor(session, settings)
        self._gateway = rpc_gateway or ModuleRpcGateway(
            settings,
            audit_callback=self._audit,
            heartbeat_callback=self._on_heartbeat,
            climate_publish_callback=self._publish_climate_readings,
        )

    def active_process(self, runtime_instance_id: str) -> SandboxProcess | None:
        return self._processes.get(runtime_instance_id)

    def drop_process(self, runtime_instance_id: str) -> None:
        self._processes.pop(runtime_instance_id, None)

    async def _on_heartbeat(self, runtime_instance_id: str) -> None:
        await self._repo.record_heartbeat(runtime_instance_id)
        self._supervisor.record_heartbeat(runtime_instance_id)

    async def supervise_tick(self) -> None:
        """One supervisor cycle: heartbeat enforcement, restarts, revocation scan."""
        await self._supervisor.supervise(self)
        await self._process_pending_restarts()
        await self._security_monitor.scan_active(self)

    @property
    def gateway(self) -> ModuleRpcGateway:
        return self._gateway

    async def _audit(self, **kwargs) -> None:
        await self._repo.record_event(
            runtime_instance_id=kwargs["runtime_instance_id"],
            event_type=kwargs["event_type"],
            module_id=kwargs["module_id"],
            site_id=kwargs["site_id"],
            detail=kwargs.get("detail"),
        )

    async def _publish_climate_readings(
        self,
        *,
        runtime_instance_id: str,
        module_id: str,
        site_id: int,
        readings: list,
    ) -> None:
        from datetime import datetime

        from energy_core.climate.repository import ClimateStateRepository
        from energy_core.contracts.climate.status import ClimateDeviceState

        repo = ClimateStateRepository(self._session)
        for item in readings:
            if not isinstance(item, dict):
                continue
            device_id = str(item.get("device_id") or item.get("external_device_id") or "")
            if not device_id:
                continue
            observed_raw = item.get("observed_at")
            observed_at = (
                datetime.fromisoformat(str(observed_raw).replace("Z", "+00:00"))
                if observed_raw
                else datetime.now(UTC)
            )
            state = ClimateDeviceState(
                device_id=device_id,
                site_id=site_id,
                observed_at=observed_at,
                display_name=item.get("display_name"),
                temperature_c=item.get("temperature_c"),
                humidity_percent=item.get("humidity_percent"),
                climate_mode=item.get("climate_mode"),
                target_temperature_c=item.get("target_temperature_c"),
                online=item.get("online"),
                source_quality=item.get("source_quality") or "LIVE",
                vendor=item.get("vendor"),
            )
            await repo.upsert_reading(site_id=site_id, module_id=module_id, state=state)
        await self._session.commit()

    async def start_runtime(self, request: RuntimeStartRequest) -> RuntimeStartResult:
        descriptor = default_module_registry.get(request.module_id)
        if descriptor is None:
            return RuntimeStartResult(ok=False, message="module not registered")

        package = await InstalledPackageRepository(self._session).get(request.module_id)
        if package is None:
            return RuntimeStartResult(ok=False, message="package not installed")

        publisher_id = request.publisher_id or package.publisher
        version = request.version or package.installed_version
        artifact_sha256 = request.artifact_sha256 or package.checksum_sha256

        from energy_core.platform.modules.runtime_authorization.service import RuntimeAuthorizationService

        auth_service = RuntimeAuthorizationService(self._session, self._settings)
        spawn_allowed = await auth_service.runtime_spawn_allowed(
            self._settings,
            module_id=request.module_id,
            version=version,
            artifact_sha256=artifact_sha256,
            publisher_id=publisher_id,
            site_id=request.site_id,
        )
        if not spawn_allowed:
            blocked = runtime_blocked_reason(self._settings) or "RUNTIME_NOT_AUTHORIZED"
            return RuntimeStartResult(ok=False, state=IsolatedRuntimeState.BLOCKED, message=blocked, reason_codes=(blocked,))

        manifest_permissions, manifest_capabilities = self._manifest_permissions_and_capabilities(
            Path(package.package_path)
        )
        provided_capabilities = manifest_capabilities or tuple(
            str(c.value if hasattr(c, "value") else c) for c in descriptor.capabilities_provided
        )

        eval_result = await GovernanceEvaluationService(self._session).evaluate(
            action=PolicyAction.RUN,
            module_id=request.module_id,
            publisher_id=publisher_id,
            permissions=manifest_permissions,
            provided_capabilities=provided_capabilities,
            marketplace_enabled=self._settings.marketplace_metadata_enabled,
            app_env_production=self._settings.is_production,
        )
        if eval_result.decision.value == "DENY":
            return RuntimeStartResult(
                ok=False,
                state=IsolatedRuntimeState.BLOCKED,
                message=eval_result.explanation or "policy denied",
                reason_codes=tuple(eval_result.reason_codes),
            )

        publisher_tier = eval_result.publisher_tier
        if not tier_allows_runtime(publisher_tier):
            return RuntimeStartResult(ok=False, state=IsolatedRuntimeState.BLOCKED, message="publisher tier denied")

        if not requires_isolated_runtime(descriptor, publisher_tier=publisher_tier):
            return RuntimeStartResult(ok=False, state=IsolatedRuntimeState.BLOCKED, message="module does not require isolation")

        if ModuleInstallPolicyEngine.CONTROL_ISOLATION_GATE_OPEN is False and eval_result.control_capable:
            return RuntimeStartResult(
                ok=False,
                state=IsolatedRuntimeState.BLOCKED,
                message="control isolation gate closed",
                reason_codes=("CONTROL_MODULE_ISOLATION_REQUIRED",),
            )

        digest_ok = await self._verify_package_digest(Path(package.package_path), artifact_sha256)
        if not digest_ok:
            return RuntimeStartResult(ok=False, state=IsolatedRuntimeState.QUARANTINED, message="artifact digest mismatch")

        permissions = manifest_permissions or self._permissions_from_descriptor(descriptor)
        record = await self._repo.create_instance(
            module_id=request.module_id,
            version=version,
            publisher_id=publisher_id,
            artifact_sha256=artifact_sha256.lower(),
            site_id=request.site_id,
            state=IsolatedRuntimeState.PREPARING,
            permissions_json=json.dumps(list(permissions)),
        )
        await self._repo.record_event(
            runtime_instance_id=record.runtime_instance_id,
            event_type=RuntimeEventType.PREPARE,
            module_id=record.module_id,
            site_id=record.site_id,
        )

        socket_dir = Path(self._settings.resolved_isolated_runtime_socket_dir())
        data_root = Path(self._settings.resolved_isolated_runtime_data_root())
        data_path = self._runtime_data_path(record, data_root)
        self._ensure_module_data_path(data_path)
        socket_dir.mkdir(parents=True, exist_ok=True)
        self._ensure_rpc_socket_dir(socket_dir)
        socket_path = socket_dir / f"{record.runtime_instance_id}.sock"
        bootstrap = self._resolve_bootstrap_script()
        sdk_path = self._resolve_sdk_path()

        from energy_core.platform.modules.isolation.broker_provisioner import RuntimeBrokerProvisioner

        site_config = await RuntimeBrokerProvisioner(self._session, self._settings).provision_for_runtime(
            gateway=self._gateway,
            module_id=record.module_id,
            site_id=record.site_id,
            package_path=Path(package.package_path),
        )

        startup_token = self._gateway.register_runtime(
            record,
            permissions=permissions,
            capabilities=provided_capabilities,
            site_config=site_config,
        )
        await self._gateway.start_server(str(socket_path))
        listen = self._gateway.listen_address() or str(socket_path)
        await self._repo.transition(
            record.runtime_instance_id,
            to_state=IsolatedRuntimeState.STARTING,
            socket_path=listen,
            package_path=package.package_path,
            data_path=str(data_path),
            sandbox_mode=self._settings.resolved_isolated_runtime_sandbox(),
        )

        spec = SandboxLaunchSpec(
            runtime_instance_id=record.runtime_instance_id,
            module_id=record.module_id,
            site_id=record.site_id,
            package_path=Path(package.package_path),
            data_path=data_path,
            socket_path=socket_path,
            rpc_address=listen,
            startup_token=startup_token,
            artifact_sha256=artifact_sha256.lower(),
            version=version,
            bootstrap_script=bootstrap,
            sdk_path=sdk_path,
        )
        try:
            proc = self._launcher.launch(spec)
            self._processes[record.runtime_instance_id] = proc
            await self._repo.transition(
                record.runtime_instance_id,
                to_state=IsolatedRuntimeState.HANDSHAKING,
                process_pid=proc.pid,
                process_identity=proc.process_identity,
                started_at=datetime.now(UTC),
            )
            await self._repo.record_event(
                runtime_instance_id=record.runtime_instance_id,
                event_type=RuntimeEventType.START,
                module_id=record.module_id,
                site_id=record.site_id,
                detail={"pid": proc.pid, "sandbox": proc.sandbox_mode},
            )
            ready = await self._wait_for_process_ready(record.runtime_instance_id, proc)
            if not ready:
                err = b""
                if proc.process.stderr is not None:
                    try:
                        err = proc.process.stderr.read(65536)
                    except Exception:
                        pass
                if err:
                    logger.error(
                        "runtime %s startup failed stderr: %s",
                        record.runtime_instance_id,
                        err.decode("utf-8", errors="replace"),
                    )
                await self.stop_runtime(record.runtime_instance_id, reason="startup timeout")
                return RuntimeStartResult(
                    ok=False,
                    runtime_instance_id=record.runtime_instance_id,
                    state=IsolatedRuntimeState.CRASHED,
                    message="startup timeout",
                )
            await self._repo.transition(record.runtime_instance_id, to_state=IsolatedRuntimeState.READY)
            await self._repo.transition(record.runtime_instance_id, to_state=IsolatedRuntimeState.RUNNING)
            await self._repo.record_event(
                runtime_instance_id=record.runtime_instance_id,
                event_type=RuntimeEventType.READY,
                module_id=record.module_id,
                site_id=record.site_id,
            )
            return RuntimeStartResult(
                ok=True,
                runtime_instance_id=record.runtime_instance_id,
                state=IsolatedRuntimeState.RUNNING,
                message="running",
            )
        except Exception as exc:
            logger.exception("runtime start failed: %s", exc)
            self._gateway.device_broker.revoke_runtime(record.runtime_instance_id)
            await self._repo.transition(
                record.runtime_instance_id,
                to_state=IsolatedRuntimeState.CRASHED,
                last_error=str(exc),
            )
            return RuntimeStartResult(
                ok=False,
                runtime_instance_id=record.runtime_instance_id,
                state=IsolatedRuntimeState.CRASHED,
                message=str(exc),
            )

    async def stop_runtime(self, runtime_instance_id: str, *, reason: str = "stop") -> None:
        proc = self._processes.pop(runtime_instance_id, None)
        record = await self._repo.get_by_instance_id(runtime_instance_id)
        if record is None:
            return
        await self._repo.transition(record.runtime_instance_id, to_state=IsolatedRuntimeState.STOPPING)
        if proc is not None:
            self._launcher.terminate(proc)
        self._gateway.unregister_runtime(runtime_instance_id)
        self._gateway.device_broker.revoke_runtime(runtime_instance_id)
        if record.socket_path:
            try:
                Path(record.socket_path).unlink(missing_ok=True)
            except OSError:
                pass
        await self._repo.revoke_leases(runtime_instance_id)
        await self._repo.transition(record.runtime_instance_id, to_state=IsolatedRuntimeState.STOPPED, last_error=reason)
        await self._repo.record_event(
            runtime_instance_id=runtime_instance_id,
            event_type=RuntimeEventType.STOP,
            module_id=record.module_id,
            site_id=record.site_id,
            detail={"reason": reason},
        )
        self._supervisor.clear_runtime(runtime_instance_id)

    async def restart_runtime_instance(self, runtime_instance_id: str) -> RuntimeStartResult:
        record = await self._repo.get_by_instance_id(runtime_instance_id)
        if record is None:
            return RuntimeStartResult(ok=False, message="runtime not found")
        if record.state != IsolatedRuntimeState.PREPARING:
            return RuntimeStartResult(ok=False, message=f"runtime not restartable from {record.state.value}")

        permissions = tuple(json.loads(record.permissions_json or "[]"))
        manifest_capabilities: tuple[str, ...] = ()
        if record.package_path:
            manifest_permissions, manifest_capabilities = self._manifest_permissions_and_capabilities(Path(record.package_path))
            if manifest_permissions:
                permissions = manifest_permissions

        self._gateway.unregister_runtime(runtime_instance_id)
        startup_token = self._gateway.register_runtime(
            record,
            permissions=permissions,
            capabilities=manifest_capabilities,
        )

        package_path = Path(record.package_path or "")
        data_path = Path(record.data_path or "")
        if not data_path:
            data_path = self._runtime_data_path(record, Path(self._settings.resolved_isolated_runtime_data_root()))
        socket_path = Path(record.socket_path) if record.socket_path else (
            Path(self._settings.resolved_isolated_runtime_socket_dir()) / f"{runtime_instance_id}.sock"
        )
        listen = self._gateway.listen_address()
        if listen is None:
            await self._gateway.start_server(str(socket_path))
            listen = self._gateway.listen_address() or str(socket_path)

        bootstrap = self._resolve_bootstrap_script()
        sdk_path = self._resolve_sdk_path()
        spec = SandboxLaunchSpec(
            runtime_instance_id=runtime_instance_id,
            module_id=record.module_id,
            site_id=record.site_id,
            package_path=package_path,
            data_path=data_path,
            socket_path=socket_path,
            rpc_address=listen,
            startup_token=startup_token,
            artifact_sha256=record.artifact_sha256,
            version=record.version,
            bootstrap_script=bootstrap,
            sdk_path=sdk_path,
        )
        try:
            await self._repo.transition(
                runtime_instance_id,
                to_state=IsolatedRuntimeState.STARTING,
                socket_path=listen,
                sandbox_mode=self._settings.resolved_isolated_runtime_sandbox(),
            )
            proc = self._launcher.launch(spec)
            self._processes[runtime_instance_id] = proc
            await self._repo.transition(
                runtime_instance_id,
                to_state=IsolatedRuntimeState.HANDSHAKING,
                process_pid=proc.pid,
                process_identity=proc.process_identity,
                started_at=datetime.now(UTC),
            )
            ready = await self._wait_for_process_ready(runtime_instance_id, proc)
            if not ready:
                await self.stop_runtime(runtime_instance_id, reason="restart handshake timeout")
                return RuntimeStartResult(
                    ok=False,
                    runtime_instance_id=runtime_instance_id,
                    state=IsolatedRuntimeState.CRASHED,
                    message="restart handshake timeout",
                )
            await self._repo.transition(runtime_instance_id, to_state=IsolatedRuntimeState.READY)
            await self._repo.transition(runtime_instance_id, to_state=IsolatedRuntimeState.RUNNING)
            return RuntimeStartResult(
                ok=True,
                runtime_instance_id=runtime_instance_id,
                state=IsolatedRuntimeState.RUNNING,
                message="restarted",
            )
        except Exception as exc:
            logger.exception("runtime restart failed: %s", exc)
            await self._repo.transition(
                runtime_instance_id,
                to_state=IsolatedRuntimeState.CRASHED,
                last_error=str(exc),
            )
            return RuntimeStartResult(ok=False, runtime_instance_id=runtime_instance_id, message=str(exc))

    async def _process_pending_restarts(self) -> None:
        for record in await self._repo.list_instances():
            if record.state == IsolatedRuntimeState.PREPARING and record.restart_count > 0:
                if record.runtime_instance_id in self._processes:
                    continue
                await self.restart_runtime_instance(record.runtime_instance_id)

    async def list_runtimes(self, *, site_id: int | None = None):
        return await self._repo.list_instances(site_id=site_id)

    async def get_runtime(self, runtime_instance_id: str):
        return await self._repo.get_by_instance_id(runtime_instance_id)

    async def _verify_package_digest(self, package_path: Path, expected: str) -> bool:
        archive = package_path
        if package_path.is_dir():
            import zipfile
            import tempfile

            tmp = package_path.parent / ".verify-runtime.zip"
            with zipfile.ZipFile(tmp, "w") as zf:
                for path in package_path.rglob("*"):
                    if path.is_file():
                        zf.write(path, path.relative_to(package_path).as_posix())
            archive = tmp
        try:
            actual = compute_package_content_sha256(archive)
            return actual.lower() == expected.lower()
        finally:
            if archive.name == ".verify-runtime.zip":
                archive.unlink(missing_ok=True)

    def _runtime_data_path(self, record, data_root: Path) -> Path:
        return data_root / record.module_id / str(record.site_id) / record.runtime_instance_id

    def _ensure_rpc_socket_dir(self, socket_dir: Path) -> None:
        if not hasattr(os, "geteuid") or os.geteuid() != 0:
            return
        module_uid = self._settings.isolated_runtime_module_uid
        module_gid = self._settings.isolated_runtime_module_gid
        for parent in socket_dir.parents:
            if not parent.exists():
                continue
            try:
                os.chmod(parent, (os.stat(parent).st_mode | 0o0111) & 0o777)
            except OSError:
                pass
            if parent.parent == parent:
                break
        try:
            os.chown(socket_dir, module_uid, module_gid)
            os.chmod(socket_dir, 0o700)
        except OSError:
            pass

    def _ensure_module_data_path(self, data_path: Path) -> None:
        data_path.mkdir(parents=True, exist_ok=True)
        if not hasattr(os, "geteuid") or os.geteuid() != 0:
            return
        module_uid = self._settings.isolated_runtime_module_uid
        module_gid = self._settings.isolated_runtime_module_gid
        for parent in data_path.parents:
            if not parent.exists():
                continue
            try:
                os.chmod(parent, (os.stat(parent).st_mode | 0o0111) & 0o777)
            except OSError:
                pass
            if parent.parent == parent:
                break
        try:
            os.chown(data_path, module_uid, module_gid)
            os.chmod(data_path, 0o700)
        except OSError:
            pass

    def _manifest_permissions_and_capabilities(self, package_path: Path) -> tuple[tuple[str, ...], tuple[str, ...]]:
        manifest_path = package_path / "manifest.json"
        if not manifest_path.exists():
            return (), ()
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        perms = tuple(str(p) for p in raw.get("permissions") or [])
        caps = tuple(str(c) for c in raw.get("provided_capabilities") or [])
        return perms, caps

    def _permissions_from_descriptor(self, descriptor: ModuleDescriptor) -> tuple[str, ...]:
        perms = set()
        for cap in descriptor.capabilities_provided:
            perms.add(str(cap.value if hasattr(cap, "value") else cap))
        return tuple(sorted(perms))

    def _resolve_bootstrap_script(self) -> Path:
        here = Path(__file__).resolve()
        for parent in here.parents:
            candidate = parent / "scripts" / "isolated_runtime_bootstrap.py"
            if candidate.exists():
                return candidate
        raise FileNotFoundError("isolated_runtime_bootstrap.py not found")

    def _resolve_sdk_path(self) -> Path:
        return Path(__file__).resolve().parents[4] / "emic_runtime_sdk"

    async def _wait_for_process_ready(self, runtime_instance_id: str, proc: SandboxProcess) -> bool:
        deadline = asyncio.get_event_loop().time() + self._settings.isolated_runtime_startup_timeout_seconds
        while asyncio.get_event_loop().time() < deadline:
            if self._gateway.is_process_ready(runtime_instance_id):
                return True
            if proc.process.poll() is not None:
                return False
            await asyncio.sleep(0.2)
        return False
