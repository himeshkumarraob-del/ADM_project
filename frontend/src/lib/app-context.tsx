"use client";

/**
 * Locale + chat session context shared by every page.
 * The language toggle lives in the sidebar and flips UI strings and API
 * `language` together.
 */

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { Locale } from "./i18n";
import { t as translate } from "./i18n";

interface AppState {
  locale: Locale;
  setLocale: (l: Locale) => void;
  t: (key: string) => string;
  activeConversationId: string | null;
  setActiveConversationId: (id: string | null) => void;
  /** bumped whenever a conversation should be re-fetched */
  historyVersion: number;
  bumpHistory: () => void;
}

const AppContext = createContext<AppState | null>(null);

export function AppProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("en");
  const [activeConversationId, setActiveConversationId] = useState<string | null>(
    null,
  );
  const [historyVersion, setHistoryVersion] = useState(0);

  useEffect(() => {
    // Reading a persisted preference is the classic "sync with an external
    // store" case; the value can only be known on the client.
    const saved = window.localStorage.getItem("mw_locale");
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (saved === "en" || saved === "hi") setLocaleState(saved);
  }, []);

  const setLocale = useCallback((l: Locale) => {
    setLocaleState(l);
    window.localStorage.setItem("mw_locale", l);
  }, []);

  const t = useCallback((key: string) => translate(locale, key), [locale]);
  const bumpHistory = useCallback(() => setHistoryVersion((v) => v + 1), []);

  const value = useMemo(
    () => ({
      locale,
      setLocale,
      t,
      activeConversationId,
      setActiveConversationId,
      historyVersion,
      bumpHistory,
    }),
    [locale, setLocale, t, activeConversationId, historyVersion, bumpHistory],
  );

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>;
}

export function useApp(): AppState {
  const ctx = useContext(AppContext);
  if (!ctx) throw new Error("useApp must be used inside AppProvider");
  return ctx;
}
