import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  CircleDot,
  History,
  Info,
  Loader2,
  MessageSquare,
} from "lucide-react";
import { api, ApiError } from "../lib/api";
import type { FindingSummary } from "../lib/types";
import { dateTimeLabel, titleCase } from "../lib/format";
import {
  Alert,
  Badge,
  Card,
  PageHeader,
  SeverityBadge,
  Skeleton,
  StatusBadge,
} from "../components/ui";

const ACTION_LABELS: Record<string, string> = {
  start_review: "Start review",
  resolve: "Resolve",
  dismiss: "Dismiss",
  escalate: "Escalate to AICTE",
  reopen: "Reopen",
};

function EvidenceValue({ value }: { value: unknown }) {
  if (value === null || value === undefined) return <span className="text-ink-soft/50">—</span>;
  if (typeof value === "boolean") return <span>{value ? "Yes" : "No"}</span>;
  if (typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>);
    return (
      <div className="space-y-1">
        {entries.map(([key, nested]) => (
          <div key={key} className="flex gap-2 text-[11px]">
            <span className="min-w-[110px] text-ink-soft/70">{titleCase(key)}</span>
            <span className="break-all font-medium text-ink"><EvidenceValue value={nested} /></span>
          </div>
        ))}
      </div>
    );
  }
  return <span className="break-words">{String(value)}</span>;
}

export default function FindingDetail() {
  const { findingId } = useParams();
  const queryClient = useQueryClient();
  const [action, setAction] = useState("start_review");
  const [comment, setComment] = useState("");
  const [feedback, setFeedback] = useState<string | null>(null);

  const query = useQuery({
    queryKey: ["finding", findingId],
    queryFn: () => api<FindingSummary>(`/findings/${findingId}`),
    enabled: Boolean(findingId),
  });

  const mutation = useMutation({
    mutationFn: () =>
      api<{ finding: FindingSummary }>(`/findings/${findingId}/actions`, {
        method: "POST",
        body: JSON.stringify({ action, comment }),
      }),
    onSuccess: () => {
      setComment("");
      setFeedback("Action recorded. The finding history and audit chain were updated.");
      queryClient.invalidateQueries({ queryKey: ["finding", findingId] });
      queryClient.invalidateQueries({ queryKey: ["findings"] });
      queryClient.invalidateQueries({ queryKey: ["institution-dashboard"] });
    },
    onError: (error) => setFeedback(error instanceof ApiError ? error.message : "Could not record the action."),
  });

  if (query.isLoading) return <div className="space-y-4"><Skeleton className="h-24" /><Skeleton className="h-96" /></div>;
  if (query.isError || !query.data) return <Alert tone="rose" title="Finding not found">It may have been removed or belongs to another institution.</Alert>;

  const finding = query.data;
  const allowed = finding.allowed_actions ?? [];
  const evidence = Object.entries(finding.evidence ?? {});

  return (
    <div className="space-y-5">
      <Link to="/app/findings" className="btn-quiet !px-2 text-xs">
        <ArrowLeft className="h-3.5 w-3.5" /> All findings
      </Link>

      <PageHeader
        eyebrow={`${finding.ref} · ${titleCase(finding.rule_code)}`}
        title={finding.title}
        description={`${finding.institution_name ?? "Institution"} · raised ${dateTimeLabel(finding.created_at)}`}
        actions={
          <>
            <SeverityBadge severity={finding.severity} />
            <StatusBadge status={finding.status} />
          </>
        }
      />

      <div className="grid gap-5 xl:grid-cols-[1.4fr_0.8fr]">
        <div className="space-y-5">
          <Card className="p-5 sm:p-6">
            <div className="flex items-start gap-3">
              <span className="grid h-9 w-9 shrink-0 place-items-center rounded-2xl bg-brand-soft text-brand">
                <Info className="h-4 w-4" />
              </span>
              <div>
                <h2 className="text-[14px] font-bold text-ink">What happened</h2>
                <p className="mt-1.5 text-[12.5px] leading-relaxed text-ink-soft">{finding.explanation}</p>
              </div>
            </div>
            <div className="mt-5 grid gap-4 sm:grid-cols-2">
              <div className="rounded-2xl bg-paper p-4">
                <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-ink-soft">What the rule checks</p>
                <p className="mt-1.5 text-[12px] leading-relaxed text-ink">{finding.what_checks}</p>
              </div>
              <div className="rounded-2xl bg-paper p-4">
                <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-ink-soft">Why it matters</p>
                <p className="mt-1.5 text-[12px] leading-relaxed text-ink">{finding.why_matters}</p>
              </div>
            </div>
            <div className="mt-4 flex items-start gap-3 rounded-2xl border border-brand/15 bg-brand-soft/50 p-4">
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-brand" />
              <div>
                <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-brand-dark">Recommended human action</p>
                <p className="mt-1 text-[12px] leading-relaxed text-ink">{finding.recommended_action}</p>
              </div>
            </div>
            {finding.policy_assumption && (
              <div className="mt-4 flex items-start gap-3 rounded-2xl border border-amber/25 bg-amber-soft/70 p-4">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber" />
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-amber">Policy assumption used</p>
                  <p className="mt-1 text-[12px] leading-relaxed text-ink">{finding.policy_assumption}</p>
                </div>
              </div>
            )}
          </Card>

          <Card className="overflow-hidden">
            <div className="flex items-center justify-between border-b border-line px-5 py-4">
              <div>
                <h2 className="text-[14px] font-bold text-ink">Evidence compared</h2>
                <p className="mt-0.5 text-[11px] text-ink-soft">Identifiers are masked. This is the exact stored evidence.</p>
              </div>
              <Badge tone="slate">{evidence.length} fields</Badge>
            </div>
            <dl className="divide-y divide-line">
              {evidence.map(([key, value]) => (
                <div key={key} className="grid gap-1 px-5 py-3 sm:grid-cols-[180px_1fr]">
                  <dt className="text-[10.5px] font-bold uppercase tracking-[0.1em] text-ink-soft">{titleCase(key)}</dt>
                  <dd className="text-[12px] text-ink"><EvidenceValue value={value} /></dd>
                </div>
              ))}
            </dl>
          </Card>
        </div>

        <div className="space-y-5">
          <Card className="p-5">
            <div className="flex items-center gap-2">
              <CircleDot className="h-4 w-4 text-brand" />
              <h2 className="text-[14px] font-bold text-ink">Record a decision</h2>
            </div>
            <p className="mt-1 text-[11px] leading-relaxed text-ink-soft">
              Every action needs a comment. Nothing is auto-rejected; a person owns the outcome.
            </p>
            {allowed.length === 0 ? (
              <div className="mt-4 rounded-2xl bg-paper px-4 py-3 text-[11.5px] text-ink-soft">
                This finding is <strong>{finding.status.replace("_", " ")}</strong>. An administrator or central reviewer can reopen it if needed.
              </div>
            ) : (
              <div className="mt-4 space-y-3">
                <div>
                  <label className="label" htmlFor="action">Action</label>
                  <select id="action" className="input text-xs" value={action} onChange={(event) => setAction(event.target.value)}>
                    {allowed.map((name) => <option key={name} value={name}>{ACTION_LABELS[name] ?? titleCase(name)}</option>)}
                  </select>
                </div>
                <div>
                  <label className="label" htmlFor="comment">Comment (required)</label>
                  <textarea
                    id="comment"
                    rows={3}
                    value={comment}
                    onChange={(event) => setComment(event.target.value)}
                    placeholder="Explain what you checked and why this decision is right."
                    className="input resize-y text-xs"
                  />
                </div>
                <button
                  onClick={() => mutation.mutate()}
                  disabled={mutation.isPending || comment.trim().length < 3}
                  className="btn-primary w-full text-xs"
                >
                  {mutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <MessageSquare className="h-4 w-4" />}
                  {mutation.isPending ? "Recording…" : "Record action"}
                </button>
              </div>
            )}
            {feedback && (
              <p className={`mt-3 rounded-xl px-3 py-2 text-[11px] ${mutation.isError ? "bg-rose-soft text-rose" : "bg-mint-soft text-mint"}`}>{feedback}</p>
            )}
          </Card>

          <Card className="overflow-hidden">
            <div className="flex items-center gap-2 border-b border-line px-5 py-4">
              <History className="h-4 w-4 text-ink-soft" />
              <h2 className="text-[14px] font-bold text-ink">History</h2>
            </div>
            <ol className="px-5 py-4">
              {(finding.history ?? []).length === 0 ? (
                <li className="text-[11.5px] text-ink-soft">No events yet.</li>
              ) : (
                (finding.history ?? []).map((event, index) => (
                  <li key={`${event.at}-${index}`} className="relative pb-5 pl-6 last:pb-1">
                    {index < (finding.history?.length ?? 0) - 1 && <span className="absolute left-[5px] top-3 h-full w-px bg-line" />}
                    <span className="absolute left-0 top-1.5 h-2.5 w-2.5 rounded-full border-2 border-white bg-brand shadow-[0_0_0_2px_rgba(47,111,237,0.2)]" />
                    <p className="text-[11.5px] font-bold text-ink">{event.label}</p>
                    <p className="mt-0.5 text-[11px] leading-relaxed text-ink-soft">{event.comment}</p>
                    <p className="mt-1 text-[9.5px] uppercase tracking-[0.08em] text-ink-soft/60">{event.actor} · {dateTimeLabel(event.at)}</p>
                  </li>
                ))
              )}
            </ol>
          </Card>
        </div>
      </div>
    </div>
  );
}
