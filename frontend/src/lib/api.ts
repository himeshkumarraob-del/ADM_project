/**
 * Typed client for the Mahabharata Wisdom AI backend.
 *
 * Every call talks to NEXT_PUBLIC_API_URL (defaults to http://localhost:8000)
 * and surfaces backend errors as `ApiError` so the UI can render them.
 */

export const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Language = "en" | "hi";

export type SupportLevel =
  | "strong_textual_support"
  | "interpretive"
  | "modern_application"
  | "insufficient_evidence";

export interface ModeInfo {
  id: string;
  label: string;
  emoji: string;
  tagline: string;
  placeholder: string;
}

export interface SafetyNotice {
  kind: "crisis" | "medical" | "legal" | "financial" | "general";
  message: string;
}

export interface SituationAnalysis {
  situation_type: string;
  emotions: string[];
  entities: string[];
  themes: string[];
  conflict: string | null;
  intent: string;
  language: string;
}

export interface EvidencePassage {
  id: string;
  parva: string;
  section: string;
  chapter: string | null;
  reference: string;
  source_reference: string;
  speaker: string;
  listener: string;
  characters: string[];
  themes: string[];
  quote: string;
  summary: string;
  original_text: string;
  text_type: string;
  source_title: string;
  verification_status: string;
  is_primary_text: boolean;
  relevance: number;
  semantic_score: number;
  keyword_score: number;
  source: string;
}

export interface Perspective {
  character: string;
  character_slug: string;
  stance: string;
  basis: string;
  passage_ids: string[];
  support_level: SupportLevel;
}

export interface GuidanceResponse {
  situation_summary: string;
  analysis: SituationAnalysis;
  episode: string;
  episode_reference: string;
  episode_characters: string[];
  primary_text: EvidencePassage[];
  interpretation: string;
  application: string;
  perspectives: Perspective[];
  reflection_questions: string[];
  support_level: SupportLevel;
  evidence_note: string;
  sources: string[];
  safety_notices: SafetyNotice[];
  generator: string;
  language: Language;
  retrieval_debug: Record<string, unknown>;
}

export interface Citation {
  id: string;
  passage_id: string;
  reference: string;
  support_level: string;
  relevance: number;
  verified: boolean;
}

export interface ChatResponse {
  message_id: string;
  conversation_id: string;
  reply: GuidanceResponse;
  citations: Citation[];
}

export interface Conversation {
  id: string;
  title: string;
  mode: string;
  language: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface Message {
  id: string;
  role: string;
  mode: string;
  content: string;
  reply: GuidanceResponse | null;
  created_at: string;
}

export interface Character {
  slug: string;
  name: string;
  aliases: string[];
  role: string;
  description: string;
  primary_themes: string[];
  theme_counts?: Record<string, number>;
}

export interface CharacterDetail {
  character: Character;
  passages: Passage[];
  passage_count: number;
  perspective_hint: string;
}

export interface Theme {
  slug: string;
  name: string;
  kind: string;
  description: string;
  passage_count: number;
}

export interface Passage {
  id: string;
  parva: string;
  section: string;
  chapter: string | null;
  reference: string;
  speaker: string;
  listener: string;
  characters: string[];
  themes: string[];
  keywords: string[];
  events: string[];
  original_text: string;
  translation: string;
  summary: string;
  text_type: string;
  source_title: string;
  verification_status: string;
  verification_note?: string;
  is_primary_text: boolean;
  embedding_status: string;
  relevance: number | null;
}

export interface EvalMetrics {
  questions: number;
  retrieval_coverage: number;
  theme_relevance_rate: number;
  reference_relevance_rate?: number;
  refusal_accuracy: number | null;
  incorrect_refusals: number;
  hallucination_rate: number;
  citation_accuracy: number;
  text_interpretation_distinction_rate: number;
  no_absolute_commands_rate: number;
  safety_notice_rate: number;
  answer_faithfulness_proxy: number | null;
  [key: string]: unknown;
}

export interface EvalRunSummary {
  id: string;
  dataset: string;
  generator: string;
  created_at: string;
  metrics: EvalMetrics;
}

export interface EvalResult {
  run_id?: string;
  metrics: EvalMetrics;
  disclaimer: string;
  results: Array<Record<string, unknown>>;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
      cache: "no-store",
    });
  } catch {
    throw new ApiError(
      0,
      "Cannot reach the API. Is the backend running on port 8000?",
    );
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
      else if (Array.isArray(body?.detail))
        detail = body.detail
          .map((d: { msg?: string }) => d.msg ?? "")
          .filter(Boolean)
          .join("; ");
    } catch {
      // non-JSON error body: keep the status text
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

// --------------------------------------------------------------------------- //
// Chat
// --------------------------------------------------------------------------- //
export function sendChat(body: {
  message: string;
  mode: string;
  language: Language;
  conversation_id?: string | null;
  character?: string | null;
  include_perspectives?: boolean | null;
}): Promise<ChatResponse> {
  return request<ChatResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export const getModes = () => request<ModeInfo[]>("/api/modes");

export const getConversations = () =>
  request<Conversation[]>("/api/conversations");

export const getConversation = (id: string) =>
  request<{ conversation: Conversation; messages: Message[] }>(
    `/api/conversations/${id}`,
  );

export const deleteConversation = (id: string) =>
  request<{ ok: boolean }>(`/api/conversations/${id}`, { method: "DELETE" });

export function sendFeedback(body: {
  message_id: string;
  rating: number;
  categories?: string[];
  comment?: string;
}): Promise<{ ok: boolean }> {
  return request("/api/feedback", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// --------------------------------------------------------------------------- //
// Exploration
// --------------------------------------------------------------------------- //
export const getCharacters = () => request<Character[]>("/api/characters");

export const getCharacter = (slug: string) =>
  request<CharacterDetail>(`/api/characters/${slug}`);

export const getThemes = () => request<Theme[]>("/api/themes");

export function searchPassages(body: {
  q?: string;
  parva?: string;
  character?: string;
  theme?: string;
  speaker?: string;
  text_type?: "verse" | "prose" | "summary";
  verified_only?: boolean;
  limit?: number;
}): Promise<{ count: number; results: EvidencePassage[] }> {
  return request("/api/search", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export const getDailyReflection = (language: Language) =>
  request<{ available: boolean; message?: string; reply: GuidanceResponse }>(
    `/api/reflection/daily?language=${language}`,
  );

export const getPassage = (id: string) =>
  request<Passage>(`/api/passages/${id}`);

// --------------------------------------------------------------------------- //
// Admin
// --------------------------------------------------------------------------- //
export interface AdminStats {
  passages: number;
  sources: number;
  characters: number;
  themes: number;
  embeddings: number;
  messages: number;
  citations: number;
  feedback: number;
  indexed: number;
  pending: number;
  corpus_dir: string;
  by_verification: Record<string, number>;
  by_parva: Record<string, number>;
}

export const getAdminStats = () => request<AdminStats>("/api/admin/stats");

export const adminListPassages = (params: {
  status?: string;
  q?: string;
  limit?: number;
  offset?: number;
}) => {
  const qs = new URLSearchParams();
  if (params.status) qs.set("status", params.status);
  if (params.q) qs.set("q", params.q);
  if (params.limit) qs.set("limit", String(params.limit));
  if (params.offset) qs.set("offset", String(params.offset));
  return request<{ total: number; items: Passage[] }>(
    `/api/admin/passages?${qs.toString()}`,
  );
};

export function verifyPassage(
  id: string,
  body: { status: string; note?: string },
): Promise<{ ok: boolean }> {
  return request(`/api/admin/passages/${id}/verify`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updatePassage(
  id: string,
  body: Record<string, unknown>,
): Promise<Passage> {
  return request(`/api/admin/passages/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export const getFeedback = () =>
  request<Array<Record<string, unknown>>>("/api/admin/feedback");

export const getRetrievalQuality = () =>
  request<Record<string, unknown>>("/api/admin/retrieval-quality");

// --------------------------------------------------------------------------- //
// Evaluation
// --------------------------------------------------------------------------- //
export const runEvaluation = () =>
  request<EvalResult>("/api/eval/run", { method: "POST" });

export const listEvalRuns = () => request<EvalRunSummary[]>("/api/eval/runs");

export const getEvalRun = (id: string) =>
  request<{ id: string; created_at: string; results: EvalResult }>(
    `/api/eval/runs/${id}`,
  );

// --------------------------------------------------------------------------- //
// Auth (optional; AUTH_REQUIRED=false by default)
// --------------------------------------------------------------------------- //
export const login = (body: { email: string; password: string }) =>
  request<{ access_token: string; token_type: string }>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify(body),
  });
