"use client";

/** Conversation history: reopen or delete past threads. */

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  deleteConversation,
  getConversation,
  getConversations,
  type Conversation,
} from "@/lib/api";
import { useApp } from "@/lib/app-context";

export default function HistoryPage() {
  const { t, setActiveConversationId, historyVersion, bumpHistory } = useApp();
  const router = useRouter();
  const [rows, setRows] = useState<Conversation[]>([]);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(() => {
    getConversations()
      .then(setRows)
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh, historyVersion]);

  const open = async (id: string) => {
    try {
      await getConversation(id); // validates it still exists
      setActiveConversationId(id);
      bumpHistory();
      router.push("/");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const remove = async (id: string) => {
    try {
      await deleteConversation(id);
      refresh();
      bumpHistory();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  return (
    <div className="content">
      <h1 className="page-title">{t("history")}</h1>
      <p className="page-sub">Reopen a past conversation or clear it away.</p>
      {error && <div className="error-box">{error}</div>}

      {rows.length === 0 && <p className="muted">{t("no_conversations")}</p>}

      {rows.map((c) => (
        <div className="list-row" key={c.id}>
          <div>
            <div className="title">{c.title}</div>
            <div className="sub">
              {c.mode} · {c.language} · {c.message_count} message
              {c.message_count === 1 ? "" : "s"} ·{" "}
              {new Date(c.updated_at).toLocaleString()}
            </div>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            <button className="btn secondary" onClick={() => void open(c.id)}>
              {t("ask")}
            </button>
            <button className="btn danger" onClick={() => void remove(c.id)}>
              ✕
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
