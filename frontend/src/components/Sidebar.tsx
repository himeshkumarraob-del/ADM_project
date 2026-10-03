"use client";

/** Left-hand navigation: sections of the app + the en/hi language toggle. */

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useApp } from "@/lib/app-context";
import type { Locale } from "@/lib/i18n";

const PRIMARY = [
  { href: "/", key: "ask" },
  { href: "/explore", key: "explore" },
  { href: "/characters", key: "characters" },
  { href: "/sources", key: "sources" },
  { href: "/reflection", key: "daily_reflection" },
  { href: "/history", key: "history" },
];

const SECONDARY = [
  { href: "/evaluation", key: "evaluation" },
  { href: "/admin", key: "admin" },
];

export default function Sidebar() {
  const { t, locale, setLocale } = useApp();
  const pathname = usePathname();

  const link = (href: string, key: string) => (
    <Link
      key={href}
      href={href}
      className={`nav-link${pathname === href ? " active" : ""}`}
    >
      {t(key)}
    </Link>
  );

  return (
    <aside className="sidebar">
      <div className="brand">
        {t("app_name")}
        <small>{t("tagline")}</small>
      </div>

      {PRIMARY.map((item) => link(item.href, item.key))}

      <div className="nav-section">{t("evaluation")}</div>
      {SECONDARY.map((item) => link(item.href, item.key))}

      <div className="lang-toggle">
        {(["en", "hi"] as Locale[]).map((l) => (
          <button
            key={l}
            className={`chip${locale === l ? " active" : ""}`}
            onClick={() => setLocale(l)}
            aria-pressed={locale === l}
          >
            {l === "en" ? "English" : "हिन्दी"}
          </button>
        ))}
      </div>
    </aside>
  );
}
