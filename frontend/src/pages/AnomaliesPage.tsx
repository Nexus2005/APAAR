import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { AlertTriangle, ArrowUpRight, Info, Sparkles } from "lucide-react";
import { api } from "../lib/api";
import type { Anomaly } from "../lib/types";
import { pct } from "../lib/format";
import { Alert, Badge, Card, EmptyState, PageHeader, ProgressBar, Skeleton } from "../components/ui";

interface AnomaliesResponse {
  anomalies: Anomaly[];
}

const FEATURE_LABELS: Record<string, string> = {
  total_admissions: "Admissions",
  last_week_share_pct: "Final-week share",
  intake_utilisation_pct: "Intake utilisation",
  special_category_share_pct: "Special-category share",
  shared_phone_students: "Students sharing a phone",
  shared_phone_groups: "Shared phone groups",
  missing_apaar_share_pct: "Missing APAAR share",
  approved_intake: "Approved intake",
  regular_admitted: "Regular admitted",
};

export default function AnomaliesPage() {
  const query = useQuery({ queryKey: ["anomalies"], queryFn: () => api<AnomaliesResponse>("/anomalies") });
  if (query.isLoading) return <div className="space-y-4"><Skeleton className="h-24" /><Skeleton className="h-96" /></div>;
  if (query.isError) return <Alert tone="rose" title="Anomaly queue unavailable">Sign in as an AICTE reviewer and refresh.</Alert>;

  const anomalies = query.data?.anomalies ?? [];
  const flagged = anomalies.filter((item) => item.flagged);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Anomaly queue"
        title="Prioritised for a human, never convicted by a model."
        description="An IsolationForest ranks institutions by unusual patterns. Every card explains the biggest deviations from the peer median in plain language."
        actions={<Badge tone="amber">{flagged.length} flagged</Badge>}
      />

      <Alert tone="blue" title="How to read this">
        A high score means “look here first”, not “this college is fraudulent”. The model only ranks. Reasons are computed from the stored feature values; no language model writes a number.
      </Alert>

      {anomalies.length === 0 ? (
        <Card><EmptyState title="No anomaly scores yet" description="Seed the demo data or upload admissions for all institutions." /></Card>
      ) : (
        <div className="space-y-4">
          {anomalies.map((anomaly) => (
            <Card key={anomaly.institution_id} className="overflow-hidden">
              <div className="flex flex-wrap items-start justify-between gap-4 border-b border-line px-5 py-4">
                <div className="flex items-start gap-3">
                  <span className={`grid h-11 w-11 place-items-center rounded-2xl text-[13px] font-extrabold ${anomaly.flagged ? "bg-amber-soft text-amber" : "bg-black/[0.04] text-ink-soft"}`}>
                    #{anomaly.rank}
                  </span>
                  <div>
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="text-[14px] font-bold text-ink">{anomaly.institution_name}</h2>
                      {anomaly.flagged ? <Badge tone="amber">Review requested</Badge> : <Badge tone="slate">Watching</Badge>}
                    </div>
                    <p className="mt-0.5 text-[10.5px] text-ink-soft">{anomaly.institution_code} · {anomaly.state} · {anomaly.method.replace(/_/g, " ")}</p>
                  </div>
                </div>
                <div className="min-w-[170px]">
                  <div className="flex items-center justify-between text-[10px] font-semibold text-ink-soft">
                    <span>Priority score</span>
                    <span>{anomaly.score.toFixed(1)}</span>
                  </div>
                  <ProgressBar value={anomaly.score} tone={anomaly.flagged ? "amber" : "blue"} className="mt-1.5" height="h-1.5" />
                </div>
              </div>

              <div className="grid gap-5 px-5 py-4 lg:grid-cols-[1.1fr_0.9fr]">
                <div>
                  <p className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-[0.14em] text-ink-soft">
                    <Sparkles className="h-3 w-3 text-amber" /> Plain-language reasons
                  </p>
                  <ul className="mt-2.5 space-y-2">
                    {anomaly.reasons.map((reason) => (
                      <li key={reason} className="flex gap-2 text-[12px] leading-relaxed text-ink">
                        <span className="mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full bg-amber" />
                        {reason}
                      </li>
                    ))}
                  </ul>
                </div>
                <div className="rounded-2xl bg-paper p-4">
                  <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-ink-soft">Feature vs peer median</p>
                  <div className="mt-2.5 space-y-2">
                    {["last_week_share_pct", "intake_utilisation_pct", "special_category_share_pct", "shared_phone_students", "missing_apaar_share_pct"].map((key) => {
                      const value = anomaly.features[key] ?? 0;
                      const median = anomaly.peer_medians[key] ?? 0;
                      const isPct = key.endsWith("_pct");
                      return (
                        <div key={key} className="flex items-center justify-between gap-3 text-[11px]">
                          <span className="text-ink-soft">{FEATURE_LABELS[key] ?? key}</span>
                          <span className="flex items-center gap-2 tabular-nums">
                            <span className="font-bold text-ink">{isPct ? pct(value, 1) : value}</span>
                            <span className="text-ink-soft/50">vs {isPct ? pct(median, 1) : median}</span>
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>

              <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line px-5 py-3 text-[10.5px] text-ink-soft">
                <span className="inline-flex items-center gap-1.5"><Info className="h-3 w-3" /> Scores are recomputed after each upload across all institutions.</span>
                <Link to="/app/findings?rule=ANOMALY_INSTITUTION" className="inline-flex items-center gap-1 font-semibold text-brand">
                  Open finding <ArrowUpRight className="h-3 w-3" />
                </Link>
              </div>
            </Card>
          ))}
        </div>
      )}

      <div className="flex items-start gap-2 px-1 text-[10.5px] leading-relaxed text-ink-soft/70">
        <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber" />
        Contamination and feature definitions are prototype assumptions in <code className="rounded bg-black/5 px-1">config/rules.yaml</code>. With fewer than eight institutions the engine falls back to a robust z-score.
      </div>
    </div>
  );
}
