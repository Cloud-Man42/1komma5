import { userInitials } from "@/lib/userAdminUtils";

export function UserAvatar({ name, size = "md" }: { name: string; size?: "sm" | "md" | "lg" }) {
  return (
    <span className={`admin-avatar admin-avatar-${size}`} aria-hidden="true">
      {userInitials(name)}
    </span>
  );
}
