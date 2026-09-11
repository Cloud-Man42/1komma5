import { redirect } from "next/navigation";

export default function MarketplaceSecurityRedirect() {
  redirect("/config/modules-devices/store/security");
}
