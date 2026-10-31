import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  ArrowUpRight,
  Building2,
  ClipboardList,
  Download,
  Fingerprint,
  Search,
  Send,
  ShieldAlert,
  Sparkles,
  Users,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, apiBlob, downloadBlob } from "../lib/api";
import type { CentralDashboard as CentralData } from "../lib/types";
import { num, pct } from "../lib/format";
import {
  Alert,
  Badge,
  Card,
  EmptyState,
  PageHeader,
  ProgressBar,
  SectionCard,
  SeverityBadge,
  Skeleton,
  StatCard,
  StatusBadge,
} from "../components/ui";

interface CopilotResponse {
  answer: string;
  tool: string | null;
  rows: Record<string, unknown>[];
  citations: string[];
  llm_used: boolean;
}

const QUICK_QUESTIONS = [
  "Which colleges are above intake in Maharashtra?",
  "Show the top anomalies",
  "Summarise duplicates across colleges",
  "Data quality by state",
];

export default function CentralDashboard() {
  const [question, setQuestion] = useState("");
  const query = useQuery({
    queryKey: ["central-dashboard"],
    queryFn: () => api<CentralData>("/dashboard/central"),
  });
  const copilot = useMutation({
    mutationFn: (q: string) =>
      api<CopilotResponse>("/copilot/query", { method: "POST", body: JSON.stringify({ question: q }) }),
  });

  if (query.isLoading) {
    return (
      <div className="space-y-5">
        <Skeleton className="h-20 w-2/3" />
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {Array.from({ length: 4 }).map((_, index) => <Skeleton key={index} className="h-32" />)}
        </div>
        <Skeleton className="h-80" />
      </div>
    );
  }
  if (query.isError || !query.data) {
    return <Alert tone="rose" title="Central dashboard unavailable">Refresh the page or sign in again as an AICTE reviewer.</Alert>;
  }

  const data = query.data;

  async function download() {
    const blob = await apiBlob("/reports/data-quality.csv");
    downloadBlob(blob, "data-quality-report.csv");
  }

  function ask(value?: string) {
    const text = (value ?? question).trim();
    if (!text) return;
    setQuestion(text);
    copilot.mutate(text);
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="AICTE central console"
        title="The national picture, without the noise."
        description="Intake utilisation, readiness and a prioritised review queue. Every score is an invitation to look, not a verdict."
        actions={
          <button onClick={download} className="btn-ghost !py-2.5 text-xs">
            <Download className="h-4 w-4" /> Data-quality CSV
          </button>
        }
      />

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Institutions" value={num(data.kpis.institutions)} sub="across 4 states · synthetic" icon={<Building2 className="h-4 w-4" />} tone="navy" />
        <StatCard label="Admitted students" value={num(data.kpis.enrolments)} sub={<span>rejected rows are excluded from intake</span>} icon={<Users className="h-4 w-4" />} tone="blue" />
        <StatCard label="Programmes over intake" value={num(data.kpis.programmes_over_intake)} sub={<span>{num(data.kpis.open_risk_findings)} open risk / blocker findings</span>} icon={<ShieldAlert className="h-4 w-4" />} tone="amber" />
        <StatCard label="Ranked for review" value={num(data.kpis.anomalies_flagged)} sub={<span>prioritisation only · {data.kpis.escalated} escalated</span>} icon={<Fingerprint className="h-4 w-4" />} tone="rose" />
      </div>

      <div className="grid gap-5 xl:grid-cols-3">
        <SectionCard
          className="xl:col-span-2"
          title="Intake utilisation by state"
          description="Regular admissions as a share of approved intake, aggregated from the versioned approvals."
          action={<Badge tone="slate">Policy v{data.policy.version}</Badge>}
          bodyClassName="px-2 pb-3"
        >
          <div className="h-[260px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={data.states} margin={{ top: 8, right: 18, left: 0, bottom: 6 }}>
                <CartesianGrid strokeDasharray="3 6" stroke="#E5E8EF" vertical={false} />
                <XAxis dataKey="state" tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: "#7b8496" }} />
                <YAxis unit="%" tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: "#7b8496" }} width={42} />
                <Tooltip
                  cursor={{ fill: "rgba(47,111,237,.05)" }}
                  contentStyle={{ borderRadius: 14, border: "1px solid #E5E8EF", fontSize: 12 }}
                  formatter={(value) => [`${value}%`, "Utilisation"]}
                />
                <Bar dataKey="utilisation_pct" radius={[10, 10, 4, 4]} maxBarSize={54}>
                  {data.states.map((state) => (
                    <Cell key={state.state} fill={state.utilisation_pct > 100 ? "#C0392B" : state.utilisation_pct > 90 ? "#D9822B" : "#2F6FED"} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </SectionCard>

        <SectionCard title="Review queue" description="Highest-signal institutions first." action={<Link className="text-[11px] font-semibold text-brand" to="/app/anomalies">Open queue</Link>}>
          <div className="divide-y divide-line">
            {data.anomalies.slice(0, 4).map((anomaly) => (
              <Link key={anomaly.institution_id} to="/app/anomalies" className="block px-5 py-3.5 transition hover:bg-brand-soft/20">
                <div className="flex items-center justify-between gap-2">
                  <p className="text-[12px] font-semibold text-ink">{anomaly.institution_name}</p>
                  <Badge tone={anomaly.flagged ? "amber" : "slate"}>#{anomaly.rank}</Badge>
                </div>
                <p className="mt-1 line-clamp-2 text-[10.5px] leading-relaxed text-ink-soft">{anomaly.reasons[0]}</p>
              </Link>
            ))}
          </div>
        </SectionCard>
      </div>

      <SectionCard
        title="Institutions"
        description="Click a row to open its dashboard. Flags are review signals, not penalties."
        bodyClassName="overflow-x-auto"
      >
        <table className="table-base min-w-[980px]">
          <thead>
            <tr>
              <th>Institution</th>
              <th>State</th>
              <th className="text-right">Students</th>
              <th className="text-right">Intake used</th>
              <th>Readiness</th>
              <th className="text-right">Open flags</th>
              <th>Anomaly rank</th>
            </tr>
          </thead>
          <tbody>
            {data.institutions.map((row) => (
              <tr key={row.institution_id}>
                <td>
                  <Link to="/app/institutions" className="block">
                    <p className="font-semibold text-ink">{row.short_name}</p>
                    <p className="mt-0.5 text-[10.5px] text-ink-soft">{row.code}</p>
                  </Link>
                </td>
                <td className="text-[12px] text-ink-soft">{row.state}</td>
                <td className="text-right tabular-nums">{num(row.enrolments)}</td>
                <td className="text-right">
                  <span className={row.utilisation_pct > 100 ? "font-bold text-rose" : "tabular-nums text-ink"}>
                    {pct(row.utilisation_pct, 1)}
                  </span>
                </td>
                <td className="w-[130px]">
                  <ProgressBar value={row.readiness_pct} tone={row.readiness_pct > 80 ? "green" : row.readiness_pct > 50 ? "amber" : "rose"} height="h-1.5" />
                  <p className="mt-1 text-[10px] text-ink-soft">{pct(row.readiness_pct)}</p>
                </td>
                <td className="text-right tabular-nums">
                  <span className={row.risk_findings > 0 ? "font-bold text-amber" : "text-ink-soft"}>{row.open_findings}</span>
                </td>
                <td>
                  {row.anomaly_rank ? (
                    <Badge tone={row.anomaly_flagged ? "amber" : "slate"}>
                      #{row.anomaly_rank} {row.anomaly_flagged ? "· review" : ""}
                    </Badge>
                  ) : (
                    <span className="text-[11px] text-ink-soft">—</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </SectionCard>

      <div className="grid gap-5 xl:grid-cols-3">
        <SectionCard
          className="xl:col-span-2"
          title="Prioritised for review"
          description="IsolationForest ranks institutions; the reasons are computed from peer medians, not generated text."
          action={<Link to="/app/anomalies" className="text-[11px] font-semibold text-brand">Full queue</Link>}
        >
          <div className="space-y-3 px-5 pb-5">
            {data.anomalies.slice(0, 3).map((anomaly) => (
              <div key={anomaly.institution_id} className="rounded-2xl border border-line bg-paper/60 p-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <p className="text-[13px] font-bold text-ink">{anomaly.institution_name}</p>
                    <p className="text-[10.5px] text-ink-soft">{anomaly.institution_code} · {anomaly.state}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge tone={anomaly.flagged ? "amber" : "slate"}>{anomaly.flagged ? "Flagged" : "Watching"}</Badge>
                    <span className="text-[10px] font-semibold text-ink-soft">Priority #{anomaly.rank}</span>
                  </div>
                </div>
                <ul className="mt-2.5 space-y-1">
                  {anomaly.reasons.slice(0, 3).map((reason) => (
                    <li key={reason} className="flex gap-2 text-[11.5px] leading-relaxed text-ink-soft">
                      <span className="mt-[7px] h-1 w-1 shrink-0 rounded-full bg-amber" />
                      {reason}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </SectionCard>

        <Card className="flex flex-col overflow-hidden">
          <div className="border-b border-line bg-gradient-to-br from-navy to-[#1b3b66] px-5 py-4 text-white">
            <div className="flex items-center gap-2 text-[11px] font-bold uppercase tracking-[0.14em] text-white/60">
              <Sparkles className="h-3.5 w-3.5 text-[#9CD3B0]" /> Copilot
            </div>
            <p className="mt-1.5 text-[13px] font-semibold">Ask the review data a question</p>
            <p className="mt-1 text-[10.5px] leading-relaxed text-white/50">
              Fixed, parameterised tools only. No free-form SQL. No model-written statistics.
            </p>
          </div>
          <div className="flex-1 space-y-3 px-4 py-4">
            <div className="flex flex-wrap gap-1.5">
              {QUICK_QUESTIONS.map((q) => (
                <button key={q} onClick={() => ask(q)} className="rounded-full border border-line bg-white px-2.5 py-1 text-[10px] font-medium text-ink-soft transition hover:border-brand/40 hover:text-brand">
                  {q}
                </button>
              ))}
            </div>
            <div className="flex gap-2">
              <input
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") ask();
                }}
                placeholder="e.g. duplicates in Maharashtra"
                className="input !py-2 text-xs"
              />
              <button onClick={() => ask()} disabled={copilot.isPending} className="btn-primary !px-3" aria-label="Ask">
                {copilot.isPending ? <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" /> : <Send className="h-4 w-4" />}
              </button>
            </div>
            {copilot.isError && <p className="text-[11px] text-rose">The copilot could not answer that request.</p>}
            {copilot.data && (
              <div className="rounded-2xl border border-line bg-paper p-3.5">
                <p className="text-[12px] leading-relaxed text-ink">{copilot.data.answer}</p>
                {copilot.data.rows.length > 0 && (
                  <div className="mt-2.5 space-y-1">
                    {copilot.data.rows.slice(0, 4).map((row, index) => (
                      <p key={index} className="truncate text-[10.5px] text-ink-soft">
                        {String(row.institution_code ?? row.state ?? row.link_id ?? "")} ·{" "}
                        {String(row.excess ? `${row.excess} over intake` : row.reasons ? "ranked for review" : row.match_type ?? "")}
                      </p>
                    ))}
                  </div>
                )}
                <p className="mt-2 text-[9.5px] uppercase tracking-[0.12em] text-ink-soft/60">
                  tool: {copilot.data.tool ?? "none"} · llm: {copilot.data.llm_used ? "used" : "not used"}
                </p>
              </div>
            )}
          </div>
        </Card>
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <SectionCard title="Programmes over approved intake" description="Regular seats only; special categories are counted separately.">
          {data.over_intake.length === 0 ? (
            <EmptyState compact title="No programme is over intake" />
          ) : (
            <div className="divide-y divide-line">
              {data.over_intake.map((row) => (
                <Link key={`${row.institution_code}-${row.programme_code}`} to="/app/findings?rule=INTAKE_EXCEEDED" className="flex items-center justify-between gap-3 px-5 py-3 transition hover:bg-brand-soft/20">
                  <div>
                    <p className="text-[12px] font-semibold text-ink">{row.institution_name}</p>
                    <p className="text-[10.5px] text-ink-soft">{row.programme_code} · {row.state}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-[12px] font-bold text-rose">+{row.regular_admitted - row.approved_intake}</p>
                    <p className="text-[10px] text-ink-soft">{row.regular_admitted} / {row.approved_intake}</p>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </SectionCard>

        <SectionCard title="Escalated to AICTE" description="Findings a college has escalated for central review." action={<Link to="/app/findings?status=escalated" className="text-[11px] font-semibold text-brand">See all</Link>}>
          {data.escalations.length === 0 ? (
            <EmptyState compact illustration="/illustrations/Seminar-amico.svg" title="Nothing escalated yet" description="Colleges can escalate any open finding with a comment." />
          ) : (
            <div className="divide-y divide-line">
              {data.escalations.map((finding) => (
                <Link key={finding.id} to={`/app/findings/${finding.id}`} className="flex items-start gap-3 px-5 py-3.5 transition hover:bg-brand-soft/20">
                  <SeverityBadge severity={finding.severity} />
                  <div className="min-w-0 flex-1">
                    <p className="text-[12px] font-semibold text-ink">{finding.title}</p>
                    <p className="mt-0.5 truncate text-[10.5px] text-ink-soft">{finding.institution_name}</p>
                  </div>
                  <StatusBadge status={finding.status} />
                </Link>
              ))}
            </div>
          )}
        </SectionCard>
      </div>

      <div className="flex items-start gap-2 px-1 text-[10.5px] leading-relaxed text-ink-soft/70">
        <ClipboardList className="mt-0.5 h-3.5 w-3.5 shrink-0 text-brand" />
        Every number here comes from the seeded database. Anomaly scores only prioritise human review — the UI never calls an institution fraudulent.
        <Link to="/app/audit" className="ml-auto inline-flex items-center gap-1 font-semibold text-brand">
          <Search className="h-3 w-3" /> Audit trail <ArrowUpRight className="h-3 w-3" />
        </Link>
      </div>
    </div>
  );
}
