import { UserStatusKind, userStatusLabel } from "@/lib/userAdminUtils";

const toneMap: Record<UserStatusKind, string> = {
  active: "success",
  disabled: "neutral",
  locked: "warning",
};

export function StatusBadge({ status }: { status: UserStatusKind }) {
  return (
    <span className={`admin-status-badge admin-status-${toneMap[status]}`} role="status">
      {userStatusLabel(status)}
    </span>
  );
}
