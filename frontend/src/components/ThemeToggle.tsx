"use client";

import { useTheme } from "@/components/ThemeProvider";

export function ThemeToggle() {
  const { theme, toggleTheme } = useTheme();

  return (
    <button
      type="button"
      className="theme-toggle"
      onClick={toggleTheme}
      aria-label={theme === "dark" ? "Byt till ljust läge" : "Byt till mörkt läge"}
      title={theme === "dark" ? "Ljust läge" : "Mörkt läge"}
    >
      {theme === "dark" ? "☀" : "☾"}
    </button>
  );
}
