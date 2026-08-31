"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

export function PiBackButton() {
  const router = useRouter();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    setVisible(window.history.length > 1);
  }, []);

  if (!visible) return null;

  return (
    <button type="button" className="pi-back-btn" onClick={() => router.back()}>
      ‹ Tillbaka
    </button>
  );
}
