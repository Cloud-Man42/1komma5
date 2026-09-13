"use client";

import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

function isStandaloneDisplay(): boolean {
  if (typeof window === "undefined") return false;
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    (window.navigator as Navigator & { standalone?: boolean }).standalone === true
  );
}

export function useMobileShell(): boolean {
  const pathname = usePathname();
  const [mobile, setMobile] = useState(false);

  useEffect(() => {
    if (pathname.startsWith("/display") || pathname.startsWith("/login")) {
      setMobile(false);
      return;
    }
    const query = window.matchMedia("(max-width: 768px)");
    const update = () => setMobile(query.matches || isStandaloneDisplay());
    update();
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, [pathname]);

  return mobile;
}

export function useIsStandalonePwa(): boolean {
  const [standalone, setStandalone] = useState(false);
  useEffect(() => {
    setStandalone(isStandaloneDisplay());
  }, []);
  return standalone;
}
