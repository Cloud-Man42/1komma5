"""Simple SemVer dependency resolution."""

from __future__ import annotations

from packaging.version import InvalidVersion, Version

from energy_core.platform.modules.packages.errors import MISSING_DEPENDENCY, PackageError
from energy_core.platform.modules.packages.types import ModuleDependencySpec


def version_satisfies(version: str, version_range: str) -> bool:
    if version_range in ("*", ""):
        return True
    try:
        current = Version(version)
    except InvalidVersion:
        return False

    spec = version_range.strip()
    if spec.startswith(">="):
        try:
            return current >= Version(spec[2:].strip())
        except InvalidVersion:
            return False
    if spec.startswith("<"):
        try:
            return current < Version(spec[1:].strip())
        except InvalidVersion:
            return False
    if spec.startswith("^"):
        base = Version(spec[1:].strip())
        upper = Version(f"{base.major + 1}.0.0")
        return base <= current < upper
    try:
        return current == Version(spec)
    except InvalidVersion:
        return False


class PackageDependencyResolver:
    def resolve(
        self,
        manifest_deps: tuple[ModuleDependencySpec, ...],
        *,
        installed_versions: dict[str, str],
    ) -> None:
        for dep in manifest_deps:
            installed = installed_versions.get(dep.module_id)
            if installed is None:
                raise PackageError(
                    f"missing dependency {dep.module_id}",
                    code=MISSING_DEPENDENCY,
                )
            if not version_satisfies(installed, dep.version_range):
                raise PackageError(
                    f"dependency {dep.module_id} requires {dep.version_range}, installed {installed}",
                    code=MISSING_DEPENDENCY,
                )

    def detect_cycles(self, graph: dict[str, tuple[str, ...]]) -> None:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node: str) -> None:
            if node in visiting:
                from energy_core.platform.modules.packages.errors import DEPENDENCY_CYCLE

                raise PackageError(f"dependency cycle at {node}", code=DEPENDENCY_CYCLE)
            if node in visited:
                return
            visiting.add(node)
            for dep in graph.get(node, ()):
                visit(dep)
            visiting.remove(node)
            visited.add(node)

        for node in graph:
            visit(node)
