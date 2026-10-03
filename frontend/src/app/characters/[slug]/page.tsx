"use client";

/**
 * A single character: description, attributed perspective hint, and the
 * passages they appear in.
 */

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { getCharacter, type CharacterDetail } from "@/lib/api";
import { useApp } from "@/lib/app-context";

export default function CharacterDetailPage() {
  const { t } = useApp();
  const params = useParams<{ slug: string }>();
  const [data, setData] = useState<CharacterDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!params.slug) return;
    getCharacter(params.slug)
      .then(setData)
      .catch((e) => setError(e.message));
  }, [params.slug]);

  return (
    <div className="content">
      <p>
        <Link href="/characters">← {t("back")}</Link>
      </p>
      {error && <div className="error-box">{error}</div>}
      {!data && !error && <p className="muted">{t("loading")}</p>}
      {data && (
        <>
          <h1 className="page-title">{data.character.name}</h1>
          <p className="page-sub">{data.character.role}</p>
          <p>{data.character.description}</p>

          <div className="notice">{data.perspective_hint}</div>

          <div className="card-title">
            {t("sources")} ({data.passage_count})
          </div>
          {data.passages.map((p) => (
            <div className="source-card" key={p.id}>
              <div className="ref">{p.reference}</div>
              <div className="meta">
                {p.parva}
                {p.section ? ` · ${p.section}` : ""} · {p.verification_status}
                {p.speaker ? ` · speaker: ${p.speaker}` : ""}
              </div>
              {p.translation && <div className="quote">{p.translation}</div>}
              {p.summary && <div className="muted">{p.summary}</div>}
              <p>
                {p.themes.map((th) => (
                  <span className="pill gold" key={th}>
                    {th}
                  </span>
                ))}
              </p>
            </div>
          ))}
        </>
      )}
    </div>
  );
}
