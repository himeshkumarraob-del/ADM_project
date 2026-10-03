"use client";

/**
 * Evaluation dashboard: run the suite, inspect metrics and the per-question
 * breakdown (including canaries that must be refused).
 */

import { useCallback, useEffect, useState } from "react";
import {
  listEvalRuns,
  runEvaluation,
  type EvalResult,
  type EvalRunSummary,
} from "@/lib/api";
import { useApp } from "@/lib/app-context";

const METRIC_LABELS: Array<[string, string]> = [
  ["hallucination_rate", "Hallucination rate"],
  ["citation_accuracy", "Citation accuracy"],
  ["refusal_accuracy", "Refusal accuracy"],
  ["incorrect_refusals", "Incorrect refusals"],
  ["text_interpretation_distinction_rate", "Text/interpretation distinction"],
  ["no_absolute_commands_rate", "No absolute commands"],
  ["safety_notice_rate", "Safety notices"],
  ["retrieval_coverage", "Retrieval coverage"],
  ["theme_relevance_rate", "Theme relevance"],
  ["answer_faithfulness_proxy", "Faithfulness (proxy)"],
];

function metricClass(key: string, value: number | null): string {
  if (value === null) return "pill";
  const lowerIsBetter = key === "hallucination_rate" || key === "incorrect_refusals";
  const good = lowerIsBetter ? value === 0 : value >= 0.9;
  return `pill ${good ? "ok" : "bad"}`;
}

export default function EvaluationPage() {
  const { t } = useApp();
  const [latest, setLatest] = useState<EvalResult | null>(null);
  const [runs, setRuns] = useState<EvalRunSummary[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshRuns = useCallback(() => {
    listEvalRuns()
      .then(setRuns)
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    refreshRuns();
  }, [refreshRuns]);

  const run = async () => {
    setBusy(true);
    setError(null);
    try {
      setLatest(await runEvaluation());
      refreshRuns();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="content">
      <h1 className="page-title">{t("evaluation")}</h1>
      <p className="page-sub">
        Offline suite: retrieval relevance, citation accuracy, hallucination
        rate and refusal behaviour across 15 questions including canaries.
      </p>

      <button className="btn" onClick={() => void run()} disabled={busy}>
        {busy ? t("loading") : t("run_eval")}
      </button>
      {error && <div className="error-box">{error}</div>}

      {latest && (
        <>
          <div className="card-title">Metrics</div>
          <div className="grid">
            {METRIC_LABELS.map(([key, label]) => {
              const raw = latest.metrics[key];
              const value = typeof raw === "number" ? raw : null;
              return (
                <div className="tile" key={key}>
                  <h3>{label}</h3>
                  <span className={metricClass(key, value)}>
                    {value === null ? "n/a" : value.toFixed(3)}
                  </span>
                </div>
              );
            })}
          </div>
          <p className="muted">{latest.disclaimer}</p>

          <div className="card-title">{t("question")}s</div>
          <table className="data">
            <thead>
              <tr>
                <th>id</th>
                <th>{t("question")}</th>
                <th>{t("expected")}</th>
                <th>{t("got")}</th>
                <th>ok</th>
              </tr>
            </thead>
            <tbody>
              {latest.results.map((r) => {
                const row = r as unknown as {
                  id: string;
                  question: string;
                  expected: string;
                  support_level: string;
                  refusal_ok: boolean;
                };
                const canary = row.expected === "insufficient";
                return (
                  <tr key={row.id}>
                    <td>
                      {row.id}
                      {canary && (
                        <>
                          {" "}
                          <span className="pill bad">{t("canary")}</span>
                        </>
                      )}
                    </td>
                    <td>{row.question}</td>
                    <td>{row.expected}</td>
                    <td>{row.support_level}</td>
                    <td>{row.refusal_ok ? "✓" : "✗"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </>
      )}

      <div className="card-title">Previous runs</div>
      <table className="data">
        <thead>
          <tr>
            <th>dataset</th>
            <th>generator</th>
            <th>when</th>
            <th>hallucination</th>
            <th>citations</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((r) => (
            <tr key={r.id}>
              <td>{r.dataset}</td>
              <td>{r.generator}</td>
              <td>{new Date(r.created_at).toLocaleString()}</td>
              <td>{r.metrics.hallucination_rate?.toFixed(3)}</td>
              <td>{r.metrics.citation_accuracy?.toFixed(3)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {runs.length === 0 && <p className="muted">No runs yet.</p>}
    </div>
  );
}
