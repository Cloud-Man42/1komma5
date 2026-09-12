import { ReactNode } from "react";

export function StickyFormFooter({ children }: { children: ReactNode }) {
  return <footer className="admin-form-footer">{children}</footer>;
}
