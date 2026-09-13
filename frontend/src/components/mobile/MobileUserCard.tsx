"use client";

import Link from "next/link";
import { StatusBadge, UserAvatar } from "@/components/admin-ui";
import type { UserItem } from "@/lib/adminUsersApi";
import { formatDateTime, isAdminRole, userDisplayLabel, userStatus } from "@/lib/userAdminUtils";

export function MobileUserCard({ user }: { user: UserItem }) {
  const status = userStatus(user);
  const admin = user.roles.some((r) => isAdminRole(r.name));

  return (
    <article className="mobile-user-card">
      <div className="mobile-user-card-head">
        <UserAvatar name={userDisplayLabel(user)} size="md" />
        <div>
          <strong>{userDisplayLabel(user)}</strong>
          <p className="muted">{user.email || user.username}</p>
        </div>
        <StatusBadge status={status} />
      </div>
      <div className="mobile-user-card-meta">
        <div>
          <span>Roles</span>
          <strong>{user.roles.map((r) => r.name).join(", ") || "—"}</strong>
        </div>
        <div>
          <span>Sites</span>
          <strong>{user.sites.length ? user.sites.join(", ") : "All"}</strong>
        </div>
        <div>
          <span>Last login</span>
          <strong>{user.lastLoginAt ? formatDateTime(user.lastLoginAt) : "—"}</strong>
        </div>
      </div>
      {admin ? <p className="mobile-user-card-tag">Admin</p> : null}
      <Link href={`/admin/users/${user.id}`} className="mobile-site-card-btn">
        Edit user →
      </Link>
    </article>
  );
}
