import { Suspense } from "react";
import { LoginForm } from "./LoginForm";

export default function LoginPage() {
  return (
    <Suspense fallback={<p className="muted login-panel">Laddar inloggning…</p>}>
      <LoginForm />
    </Suspense>
  );
}
