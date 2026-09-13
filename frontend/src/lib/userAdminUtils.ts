import type { UserItem } from "@/lib/adminUsersApi";

export function userInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length >= 2) return `${parts[0][0] ?? ""}${parts[1][0] ?? ""}`.toUpperCase();
  return name.slice(0, 2).toUpperCase();
}

export function userDisplayLabel(user: Pick<UserItem, "displayName" | "username" | "email">): string {
  return user.displayName?.trim() || user.username || user.email;
}

export type UserStatusKind = "active" | "disabled" | "locked";

export function userStatus(user: Pick<UserItem, "isActive" | "isLocked">): UserStatusKind {
  if (user.isLocked) return "locked";
  if (!user.isActive) return "disabled";
  return "active";
}

export function userStatusLabel(status: UserStatusKind): string {
  if (status === "locked") return "Låst";
  if (status === "disabled") return "Inaktiv";
  return "Aktiv";
}

export function formatDateTime(iso: string | null): string {
  if (!iso) return "—";
  try {
    return new Intl.DateTimeFormat("sv-SE", {
      dateStyle: "short",
      timeStyle: "short",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

export type UserSortKey = "name" | "lastLogin" | "status";

export function sortUsers(users: UserItem[], key: UserSortKey, asc: boolean): UserItem[] {
  const dir = asc ? 1 : -1;
  return [...users].sort((a, b) => {
    if (key === "name") {
      return userDisplayLabel(a).localeCompare(userDisplayLabel(b), "sv") * dir;
    }
    if (key === "lastLogin") {
      const ta = a.lastLoginAt ? Date.parse(a.lastLoginAt) : 0;
      const tb = b.lastLoginAt ? Date.parse(b.lastLoginAt) : 0;
      return (ta - tb) * dir;
    }
    return userStatus(a).localeCompare(userStatus(b), "sv") * dir;
  });
}

export function isAdminRole(roleName: string): boolean {
  return roleName === "SUPER_ADMIN" || roleName === "ADMIN";
}
