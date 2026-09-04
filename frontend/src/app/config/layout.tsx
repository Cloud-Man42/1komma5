import { ConfigShell } from "@/components/config/ConfigShell";

export default function ConfigLayout({ children }: { children: React.ReactNode }) {
  return <ConfigShell>{children}</ConfigShell>;
}
