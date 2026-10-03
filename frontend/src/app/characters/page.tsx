"use client";

/** Character explorer — browse the cast of the indexed corpus. */

import { useEffect, useState } from "react";
import Link from "next/link";
import { getCharacters, type Character } from "@/lib/api";
import { useApp } from "@/lib/app-context";

export default function CharactersPage() {
  const { t } = useApp();
  const [rows, setRows] = useState<Character[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getCharacters()
      .then(setRows)
      .catch((e) => setError(e.message));
  }, []);

  return (
    <div className="content">
      <h1 className="page-title">{t("characters")}</h1>
      <p className="page-sub">
        Principal figures in the indexed corpus. Stances are attributed
        interpretations, never the character speaking.
      </p>
      {error && <div className="error-box">{error}</div>}
      <div className="grid">
        {rows.map((c) => (
          <Link
            href={`/characters/${c.slug}`}
            key={c.slug}
            style={{ textDecoration: "none" }}
          >
            <div className="tile">
              <h3>{c.name}</h3>
              <p>{c.description}</p>
              <span className="count">
                {c.role}
                {c.primary_themes.length > 0 &&
                  ` · ${c.primary_themes.join(", ")}`}
              </span>
            </div>
          </Link>
        ))}
      </div>
      {rows.length === 0 && !error && <p className="muted">{t("loading")}</p>}
    </div>
  );
}
