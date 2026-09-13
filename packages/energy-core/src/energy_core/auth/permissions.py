"""EMIC permission catalog and role mappings."""

from __future__ import annotations

from dataclasses import dataclass

PERMISSION_ALL = "*"

SYSTEM_ROLES = ("SUPER_ADMIN", "ADMIN", "OPERATOR", "USER", "VIEWER")


@dataclass(frozen=True, slots=True)
class PermissionDef:
    key: str
    name: str
    description: str
    group_name: str


PERMISSION_CATALOG: tuple[PermissionDef, ...] = (
    PermissionDef("users.read", "Read users", "View user list and details", "Users"),
    PermissionDef("users.create", "Create users", "Create new EMIC users", "Users"),
    PermissionDef("users.update", "Update users", "Edit user profiles and status", "Users"),
    PermissionDef("users.disable", "Disable users", "Enable or disable user accounts", "Users"),
    PermissionDef("users.roles.manage", "Manage user roles", "Assign or remove roles", "Users"),
    PermissionDef("users.sites.manage", "Manage user site access", "Grant or revoke site access", "Users"),
    PermissionDef("users.password.reset", "Reset passwords", "Admin password reset", "Users"),
    PermissionDef("roles.read", "Read roles", "View roles and permissions", "Roles"),
    PermissionDef("roles.manage", "Manage roles", "Create, edit, delete custom roles", "Roles"),
    PermissionDef("sites.read", "Read sites", "View site list and configuration", "Sites"),
    PermissionDef("sites.manage", "Manage sites", "Create and edit sites", "Sites"),
    PermissionDef("dashboard.read", "Read dashboard", "View dashboards and snapshots", "Dashboard"),
    PermissionDef("energy.read", "Read energy data", "View energy readings and stats", "Energy"),
    PermissionDef("energy.export", "Export energy data", "Export energy data", "Energy"),
    PermissionDef("battery.read", "Read battery", "View battery status", "Battery"),
    PermissionDef("battery.control", "Control battery", "Battery control operations", "Battery"),
    PermissionDef("solar.read", "Read solar", "View solar production and forecast", "Solar"),
    PermissionDef("charging.read", "Read charging", "View EV charger status", "Charging"),
    PermissionDef("charging.control", "Control charging", "EV charger control", "Charging"),
    PermissionDef("charging.schedule", "Schedule charging", "Smart charging schedules", "Charging"),
    PermissionDef("spa.read", "Read spa", "View spa status", "Spa"),
    PermissionDef("spa.control", "Control spa", "Spa control operations", "Spa"),
    PermissionDef("spa.schedule", "Schedule spa", "Spa scheduling", "Spa"),
    PermissionDef("vehicle.read", "Read vehicles", "View vehicle data", "Vehicles"),
    PermissionDef("vehicle.control", "Control vehicles", "Vehicle commands", "Vehicles"),
    PermissionDef("economy.read", "Read economy", "View economy and financial stats", "Economy"),
    PermissionDef("integration.read", "Read integrations", "View integration status", "Integrations"),
    PermissionDef("integration.manage", "Manage integrations", "Configure integrations", "Integrations"),
    PermissionDef("heartbeat.read", "Read Heartbeat", "View Heartbeat accounts and diagnostics", "Heartbeat"),
    PermissionDef("heartbeat.manage", "Manage Heartbeat", "Configure Heartbeat accounts", "Heartbeat"),
    PermissionDef("system.health.read", "Read system health", "View integration health", "System"),
    PermissionDef("system.diagnostics.read", "Read diagnostics", "View system diagnostics", "System"),
    PermissionDef("system.settings.manage", "Manage system settings", "System configuration", "System"),
    PermissionDef("audit.read", "Read audit log", "View audit events", "Audit"),
    PermissionDef("modules.read", "Read modules", "View module store and runtime", "Modules"),
    PermissionDef("modules.manage", "Manage modules", "Install and configure modules", "Modules"),
)

ALL_PERMISSION_KEYS: frozenset[str] = frozenset(p.key for p in PERMISSION_CATALOG)

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "SUPER_ADMIN": frozenset({PERMISSION_ALL}),
    "ADMIN": frozenset(
        {
            "users.read",
            "users.create",
            "users.update",
            "users.disable",
            "users.roles.manage",
            "users.sites.manage",
            "users.password.reset",
            "roles.read",
            "roles.manage",
            "sites.read",
            "sites.manage",
            "dashboard.read",
            "energy.read",
            "energy.export",
            "battery.read",
            "battery.control",
            "solar.read",
            "charging.read",
            "charging.control",
            "charging.schedule",
            "spa.read",
            "spa.control",
            "spa.schedule",
            "vehicle.read",
            "vehicle.control",
            "economy.read",
            "integration.read",
            "integration.manage",
            "heartbeat.read",
            "heartbeat.manage",
            "system.health.read",
            "system.diagnostics.read",
            "system.settings.manage",
            "audit.read",
            "modules.read",
            "modules.manage",
        }
    ),
    "OPERATOR": frozenset(
        {
            "dashboard.read",
            "energy.read",
            "battery.read",
            "battery.control",
            "solar.read",
            "charging.read",
            "charging.control",
            "charging.schedule",
            "spa.read",
            "spa.control",
            "spa.schedule",
            "vehicle.read",
            "vehicle.control",
            "economy.read",
            "integration.read",
            "heartbeat.read",
            "system.health.read",
        }
    ),
    "USER": frozenset(
        {
            "dashboard.read",
            "energy.read",
            "battery.read",
            "solar.read",
            "charging.read",
            "spa.read",
            "vehicle.read",
            "economy.read",
            "integration.read",
            "heartbeat.read",
            "system.health.read",
        }
    ),
    "VIEWER": frozenset(
        {
            "dashboard.read",
            "energy.read",
            "battery.read",
            "solar.read",
            "charging.read",
            "spa.read",
            "vehicle.read",
            "economy.read",
            "system.health.read",
        }
    ),
}


def permission_grants(required: str, held: frozenset[str]) -> bool:
    if PERMISSION_ALL in held:
        return True
    return required in held
