"""Verify Mercedes protobuf commands against EQE capabilities."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict

from sqlalchemy import select

from energy_core.config import Settings
from energy_core.db.models import SiteModel, VehicleModel
from energy_core.db.session import create_engine, create_session_factory
from energy_core.db.vehicle_repo import VehicleProviderRepository
from energy_core.secrets import SecretBox
from energy_core.vehicles.mercedes.commands.builder import (
    build_charging_action_command,
    build_set_target_soc_command,
    describe_client_message,
)
from energy_core.vehicles.mercedes.commands.features import MercedesCommandFeatures
from energy_core.vehicles.mercedes.mapping.vehicle_mapper import MercedesCapabilityMapper
from energy_core.vehicles.mercedes.provider import MercedesProvider
from energy_core.vehicles.vin import mask_vin


async def _resolve_vehicle(session_factory, site_slug: str, vehicle_id: int | None, vin_suffix: str | None) -> tuple[int, VehicleModel]:
    async with session_factory() as session:
        site = await session.scalar(select(SiteModel).where(SiteModel.slug == site_slug))
        if site is None:
            raise SystemExit(f"Site not found: {site_slug}")
        if vehicle_id is not None:
            vehicle = await session.get(VehicleModel, vehicle_id)
        else:
            vehicles = (
                await session.scalars(
                    select(VehicleModel).where(
                        VehicleModel.site_id == site.id,
                        VehicleModel.provider == "mercedes",
                        VehicleModel.enabled.is_(True),
                    )
                )
            ).all()
            if vin_suffix:
                vehicle = next((item for item in vehicles if item.vin and item.vin.endswith(vin_suffix)), None)
            else:
                vehicle = next((item for item in vehicles if item.model and "eqe" in item.model.lower()), None)
                if vehicle is None and vehicles:
                    vehicle = vehicles[-1]
        if vehicle is None or vehicle.site_id != site.id:
            raise SystemExit("Mercedes vehicle not found")
        return site.id, vehicle


async def run(args: argparse.Namespace) -> int:
    settings = Settings()
    engine = create_engine(settings)
    session_factory = create_session_factory(engine)
    secret_box = SecretBox.from_settings()
    site_id, vehicle = await _resolve_vehicle(session_factory, args.site, args.vehicle_id, args.vin_suffix)
    if not vehicle.vin:
        raise SystemExit("Vehicle VIN missing in database")

    async with session_factory() as session:
        repo = VehicleProviderRepository(session, secret_box=secret_box)
        row = await repo.get_for_site(site_id)
        if row is None:
            raise SystemExit("Mercedes integration not configured")
        token_bundle = repo.load_token_bundle(row)
        if token_bundle is None:
            raise SystemExit("Mercedes token unavailable")

    provider = MercedesProvider(
        region=row.region,
        device_guid=row.device_guid or None,
        token_bundle=token_bundle,
    )
    caps = await provider._rest.get_capabilities(vehicle.vin)  # noqa: SLF001
    command_caps = await provider._rest.get_command_capabilities(vehicle.vin)  # noqa: SLF001
    features = MercedesCommandFeatures.from_rest_payload(command_caps)
    mapped = MercedesCapabilityMapper.from_rest_payload(caps, command_payload=command_caps)

    print(f"Vehicle: id={vehicle.id} vin={mask_vin(vehicle.vin)} model={vehicle.model}")
    print("Command features:", json.dumps(asdict(features), sort_keys=True))
    print("Mapped capabilities:", json.dumps(asdict(mapped), sort_keys=True))
    print("Raw command capabilities:", json.dumps(command_caps)[:4000])

    if not features.supports_set_target_soc() and not features.supports_stop_charging():
        print("ERROR: EQE exposes no supported Mercedes command features.")
        return 2

    target_soc = args.target_soc
    set_payload, set_request_id = build_set_target_soc_command(
        vin=vehicle.vin,
        target_soc_percent=target_soc,
        features=features,
    )
    print(f"DRY set-target-soc payload: {describe_client_message(set_payload)} request_id={set_request_id}")

    if features.supports_start_charging():
        start_payload, start_request_id = build_charging_action_command(
            vin=vehicle.vin,
            action="start",
            features=features,
        )
        print(f"DRY start-charging payload: {describe_client_message(start_payload)} request_id={start_request_id}")
    if features.supports_stop_charging():
        stop_payload, stop_request_id = build_charging_action_command(
            vin=vehicle.vin,
            action="stop",
            features=features,
        )
        print(f"DRY stop-charging payload: {describe_client_message(stop_payload)} request_id={stop_request_id}")

    if args.execute is None:
        print("Dry-run complete. Re-run with --execute set-target-soc|start-charging|stop-charging to send live command.")
        await engine.dispose()
        return 0

    await provider.connect()
    try:
        if args.execute == "set-target-soc":
            payload, request_id = set_payload, set_request_id
        elif args.execute == "start-charging":
            payload, request_id = build_charging_action_command(
                vin=vehicle.vin,
                action="start",
                features=features,
            )
        elif args.execute == "stop-charging":
            payload, request_id = build_charging_action_command(
                vin=vehicle.vin,
                action="stop",
                features=features,
            )
        else:
            raise SystemExit(f"Unsupported execute action: {args.execute}")
        print(f"Sending {args.execute}: {describe_client_message(payload)}")
        status = await provider.send_command_and_wait(payload, request_id=request_id, timeout_seconds=args.timeout)
        print(
            "Command status:",
            json.dumps(
                {
                    "request_id": status.request_id,
                    "state": status.state,
                    "type_name": status.type_name,
                    "error_code": status.error_code,
                    "error_message": status.error_message,
                },
                sort_keys=True,
            ),
        )
        return 0 if status.state else 1
    finally:
        await provider.close()
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify Mercedes protobuf commands against EQE.")
    parser.add_argument("--site", default="akarp")
    parser.add_argument("--vehicle-id", type=int, default=None)
    parser.add_argument("--vin-suffix", default="1234", help="Last digits of EQE VIN when vehicle-id omitted.")
    parser.add_argument("--target-soc", type=int, default=80)
    parser.add_argument(
        "--execute",
        choices=("set-target-soc", "start-charging", "stop-charging"),
        default=None,
        help="Send one live command after dry-run checks.",
    )
    parser.add_argument("--timeout", type=float, default=45.0)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()
