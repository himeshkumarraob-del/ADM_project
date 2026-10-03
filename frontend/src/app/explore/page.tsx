"use client";

/** Explore: the theme taxonomy — a browseable map of what the corpus covers. */

import { useEffect, useState } from "react";
import Link from "next/link";
import { getThemes, type Theme } from "@/lib/api";
import { useApp } from "@/lib/app-context";

export default function ExplorePage() {
  const { t } = useApp();
  const [themes, setThemes] = useState<Theme[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getThemes()
      .then(setThemes)
      .catch((e) => setError(e.message));
  }, []);

  const groups = themes.reduce<Record<string, Theme[]>>((acc, th) => {
    (acc[th.kind] ??= []).push(th);
    return acc;
  }, {});

  return (
    <div className="content">
      <h1 className="page-title">{t("explore")}</h1>
      <p className="page-sub">
        Themes recorded across the indexed passages — the vocabulary the
        retriever actually matches on.
      </p>
      {error && <div className="error-box">{error}</div>}

      <p className="muted">
        <Link href="/characters">{t("characters")} →</Link>{" "}
        <Link href="/sources">{t("sources")} →</Link>
      </p>

      {Object.entries(groups).map(([kind, list]) => (
        <section key={kind}>
          <div className="card-title">{kind}</div>
          <div className="grid">
            {list.map((th) => (
              <div className="tile" key={th.slug}>
                <h3>{th.name}</h3>
                <p>{th.description}</p>
                <span className="count">
                  {th.passage_count} passage{th.passage_count === 1 ? "" : "s"}
                </span>
              </div>
            ))}
          </div>
        </section>
      ))}
      {themes.length === 0 && !error && <p className="muted">{t("loading")}</p>}
    </div>
  );
}
