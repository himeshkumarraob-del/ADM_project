"use client";

/** Daily Reflection — one verified passage to sit with today. */

import { useEffect, useState } from "react";
import type { GuidanceResponse } from "@/lib/api";
import { getDailyReflection } from "@/lib/api";
import { useApp } from "@/lib/app-context";
import ResponseCard from "@/components/ResponseCard";

export default function ReflectionPage() {
  const { locale, t } = useApp();
  const [reply, setReply] = useState<GuidanceResponse | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // locale is the trigger for this fetch; the loading flag flips with it
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);
    getDailyReflection(locale)
      .then((res) => {
        if (res.available) setReply(res.reply);
        else setMessage(res.message ?? null);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [locale]);

  return (
    <div className="content">
      <h1 className="page-title">{t("daily_reflection")}</h1>
      <p className="page-sub">
        A verified passage, selected deterministically for today.
      </p>
      {error && <div className="error-box">{error}</div>}
      {loading && <p className="muted">{t("loading")}</p>}
      {message && <div className="notice">{message}</div>}
      {reply && (
        <div className="bubble assistant" style={{ width: "100%" }}>
          <ResponseCard reply={reply} />
        </div>
      )}
    </div>
  );
}
