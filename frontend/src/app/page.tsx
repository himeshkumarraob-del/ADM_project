"use client";

/**
 * The main chat surface: pick a mode, ask a question, get the seven-section
 * grounded response. The active conversation id is kept in app context so the
 * history page and this page stay in sync.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import ResponseCard from "@/components/ResponseCard";
import {
  getModes,
  sendChat,
  sendFeedback,
  type ChatResponse,
  type ModeInfo,
} from "@/lib/api";
import { useApp } from "@/lib/app-context";

interface ThreadEntry {
  id: string;
  role: "user" | "assistant";
  content: string;
  chat?: ChatResponse;
}

const SUGGESTED_PROMPTS = [
  {
    category: "Duty vs Desire",
    icon: "⚖️",
    prompt: "I am struggling to choose between my duty and my personal desires.",
  },
  {
    category: "Handling Betrayal",
    icon: "💔",
    prompt: "How should I handle betrayal by someone I trusted?",
  },
  {
    category: "Peer Pressure & Ethics",
    icon: "🛡️",
    prompt: "I am under pressure to do something I believe is wrong.",
  },
  {
    category: "Workplace Conflict",
    icon: "⚔️",
    prompt: "How should I deal with conflict at work?",
  },
  {
    category: "Overcoming Failure",
    icon: "🌱",
    prompt: "I failed at something important. How should I respond?",
  },
];

export default function ChatPage() {
  const { locale, t, activeConversationId, setActiveConversationId, bumpHistory } =
    useApp();
  const [modes, setModes] = useState<ModeInfo[]>([]);
  const [mode, setMode] = useState("situation_advice");
  const [responseDetail, setResponseDetail] = useState<"concise" | "detailed">("detailed");
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [thread, setThread] = useState<ThreadEntry[]>([]);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    getModes()
      .then((m) => setModes(m))
      .catch(() => setModes([]));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [thread, busy]);

  const current = modes.find((m) => m.id === mode);

  const submit = useCallback(
    async (text?: string) => {
      const message = (text ?? input).trim();
      if (!message || busy) return;
      setError(null);
      setBusy(true);
      setInput("");
      const userEntry: ThreadEntry = {
        id: `u-${Date.now()}`,
        role: "user",
        content: message,
      };
      setThread((prev) => [...prev, userEntry]);
      try {
        const chat = await sendChat({
          message,
          mode,
          language: locale,
          conversation_id: activeConversationId,
        });
        setActiveConversationId(chat.conversation_id);
        bumpHistory();
        setThread((prev) => [
          ...prev,
          {
            id: chat.message_id,
            role: "assistant",
            content: "",
            chat,
          },
        ]);
      } catch (err) {
        setError(err instanceof Error ? err.message : String(err));
      } finally {
        setBusy(false);
      }
    },
    [
      input,
      busy,
      mode,
      locale,
      activeConversationId,
      setActiveConversationId,
      bumpHistory,
    ],
  );

  const newChat = () => {
    setActiveConversationId(null);
    setThread([]);
    setError(null);
  };

  const feedback = async (messageId: string, rating: 1 | -1) => {
    try {
      await sendFeedback({ message_id: messageId, rating });
    } catch {
      // feedback is best-effort; the UI already shows the local state
    }
  };

  return (
    <div className="content">
      <h1 className="page-title">{t("app_name")}</h1>
      <p className="page-sub">{t("tagline")}</p>

      <div className="mode-bar">
        {modes.map((m) => (
          <button
            key={m.id}
            className={`chip${mode === m.id ? " active" : ""}`}
            onClick={() => setMode(m.id)}
            title={m.tagline}
          >
            {m.emoji} {m.label}
          </button>
        ))}
        <button className="chip" onClick={newChat}>
          ＋ {t("new_chat")}
        </button>
      </div>

      {current && <p className="muted">{current.tagline}</p>}
      {error && <div className="error-box">{error}</div>}

      <div className="thread">
        {thread.length === 0 && !busy && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <div className="bubble assistant" style={{ width: "100%" }}>
              <p style={{ margin: "0 0 8px 0" }}>
                {t("saarathi_meaning")}
              </p>
              <div className="notice" style={{ margin: 0, fontSize: "12.5px" }}>
                ⚖️ {t("grounded_banner")}
              </div>
            </div>

            <div style={{ marginTop: 8 }}>
              <div className="card-title" style={{ marginTop: 0 }}>
                {t("example_prompts_title")}
              </div>
              <div className="grid">
                {SUGGESTED_PROMPTS.map((sp) => (
                  <div
                    key={sp.prompt}
                    className="tile"
                    onClick={() => void submit(sp.prompt)}
                    style={{ cursor: "pointer" }}
                  >
                    <h3>
                      {sp.icon} {sp.category}
                    </h3>
                    <p style={{ fontStyle: "italic", marginTop: 4 }}>
                      &quot;{sp.prompt}&quot;
                    </p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {thread.map((entry) =>
          entry.role === "user" ? (
            <div className="bubble user" key={entry.id}>
              {entry.content}
            </div>
          ) : (
            <div className="bubble assistant" key={entry.id}>
              {entry.chat && (
                <ResponseCard
                  reply={entry.chat.reply}
                  citations={entry.chat.citations}
                  detail={responseDetail}
                  onFeedback={(rating) => void feedback(entry.chat!.message_id, rating)}
                />
              )}
            </div>
          ),
        )}

        {busy && (
          <div className="bubble assistant muted">{t("thinking")}</div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="composer">
        <textarea
          value={input}
          placeholder={current?.placeholder ?? t("ask")}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              void submit();
            }
          }}
        />
        <select
          aria-label="Response detail"
          value={responseDetail}
          onChange={(e) => setResponseDetail(e.target.value as "concise" | "detailed")}
        >
          <option value="concise">Concise</option>
          <option value="detailed">Detailed</option>
        </select>
        <button className="btn" disabled={busy || !input.trim()} onClick={() => void submit()}>
          {t("send")}
        </button>
      </div>
    </div>
  );
}
