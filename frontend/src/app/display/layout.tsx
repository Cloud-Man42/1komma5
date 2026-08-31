import "@/styles/pi-dashboard.css";

export default function DisplayLayout({ children }: { children: React.ReactNode }) {
  return <div data-theme="dark">{children}</div>;
}
