"use client";

import Image from "next/image";

export function LoginHero() {
  return (
    <aside className="login-hero">
      <div className="login-hero-glow" aria-hidden="true" />
      <div className="login-hero-logo-wrap">
        <Image
          src="/icons/emic-logo.png"
          alt="EMIC — Energy Monitor In A Cloud"
          width={640}
          height={640}
          priority
          className="login-hero-logo"
        />
      </div>
    </aside>
  );
}
