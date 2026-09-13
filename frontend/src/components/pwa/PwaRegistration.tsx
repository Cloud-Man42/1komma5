"use client";



import { useEffect } from "react";



declare global {

  interface WindowEventMap {

    "emic:pwa-install-available": CustomEvent<{ prompt: () => Promise<void> }>;

  }

}



export function PwaRegistration() {

  useEffect(() => {

    if (typeof window === "undefined" || !("serviceWorker" in navigator)) return;

    const SW_MIGRATION_KEY = "emic-sw-v4-migrated";
    const register = () => {
      void navigator.serviceWorker
        .register("/sw.js", { scope: "/", updateViaCache: "none" })
        .then((registration) => {
          void registration.update();
        })
        .catch(() => {
          /* registration optional */
        });
    };

    if (!localStorage.getItem(SW_MIGRATION_KEY)) {
      void navigator.serviceWorker
        .getRegistrations()
        .then((regs) => Promise.all(regs.map((reg) => reg.unregister())))
        .finally(() => {
          localStorage.setItem(SW_MIGRATION_KEY, "1");
          register();
        });
      return;
    }

    register();



    const onBeforeInstall = (event: Event) => {

      event.preventDefault();

      const installEvent = event as BeforeInstallPromptEvent;

      window.dispatchEvent(

        new CustomEvent("emic:pwa-install-available", {

          detail: {

            prompt: async () => {

              await installEvent.prompt();

              await installEvent.userChoice;

            },

          },

        }),

      );

    };



    window.addEventListener("beforeinstallprompt", onBeforeInstall);

    return () => window.removeEventListener("beforeinstallprompt", onBeforeInstall);

  }, []);

  return null;

}



interface BeforeInstallPromptEvent extends Event {

  prompt: () => Promise<void>;

  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;

}


