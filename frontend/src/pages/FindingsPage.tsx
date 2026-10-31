import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { ArrowUpRight, Filter, Search } from "lucide-react";
import { api } from "../lib/api";
import type { FindingSummary } from "../lib/types";
import { dateLabel, titleCase } from "../lib/format";
import {
  Badge,
  Card,
  EmptyState,
  PageHeader,
  SeverityBadge,
  Skeleton,
  StatusBadge,
  Tabs,
} from "../components/ui";

interface FindingsResponse {
  findings: FindingSummary[];
  count: number;
}

export default function FindingsPage() {
  const [params, setParams] = useSearchParams();
  const [search, setSearch] = useState("");
  const status = params.get("status") ?? "active";
  const rule = params.get("rule") ?? "";
  const severity = params.get("severity") ?? "";
  const query = useQuery({
    queryKey: ["findings"],
    queryFn: () => api<FindingsResponse>("/findings?limit=400"),
  });

  const findings = useMemo(() => {
    let rows = query.data?.findings ?? [];
    if (status === "active") rows = rows.filter((row) => ["open", "in_review", "escalated"].includes(row.status));
    else if (status !== "all") rows = rows.filter((row) => row.status === status);
    if (rule) rows = rows.filter((row) => row.rule_code === rule);
    if (severity) rows = rows.filter((row) => row.severity === severity);
    if (search) {
      const needle = search.toLowerCase();
      rows = rows.filter(
        (row) =>
          row.title.toLowerCase().includes(needle) ||
          row.ref.toLowerCase().includes(needle) ||
          (row.institution_name ?? "").toLowerCase().includes(needle) ||
          row.rule_code.toLowerCase().includes(needle),
      );
    }
    return rows;
  }, [query.data, status, rule, severity, search]);

  const rules = useMemo(
    () => Array.from(new Set((query.data?.findings ?? []).map((row) => row.rule_code))).sort(),
    [query.data],
  );

  function update(key: string, value: string) {
    const next = new URLSearchParams(params);
    if (value) next.set(key, value);
    else next.delete(key);
    setParams(next, { replace: true });
  }

  const activeCount = query.data?.findings.filter((row) => ["open", "in_review", "escalated"].includes(row.status)).length ?? 0;
  const escalated = query.data?.findings.filter((row) => row.status === "escalated").length ?? 0;
  const resolved = query.data?.findings.filter((row) => row.status === "resolved").length ?? 0;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Review workflow"
        title="Findings, with the evidence attached."
        description="A finding names the rule, what was compared, why it matters and the policy assumption used. Every transition needs a comment and writes to the audit chain."
      />

      <div className="flex flex-wrap items-center justify-between gap-3">
        <Tabs
          active={status}
          onChange={(key) => update("status", key === "active" ? "" : key)}
          tabs={[
            { key: "active", label: "Active", count: activeCount },
            { key: "escalated", label: "Escalated", count: escalated },
            { key: "resolved", label: "Resolved", count: resolved },
            { key: "all", label: "All", count: query.data?.count },
          ]}
        />
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-soft/50" />
            <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search findings" className="input !py-2 !pl-9 text-xs sm:w-52" />
          </div>
          <select value={severity} onChange={(event) => update("severity", event.target.value)} className="input !w-auto !py-2 text-xs">
            <option value="">All severities</option>
            <option value="blocker">Blocker</option>
            <option value="risk">Risk</option>
            <option value="warning">Warning</option>
            <option value="info">Info</option>
          </select>
          <select value={rule} onChange={(event) => update("rule", event.target.value)} className="input !w-auto !py-2 text-xs">
            <option value="">All rules</option>
            {rules.map((code) => <option key={code} value={code}>{titleCase(code)}</option>)}
          </select>
          {(rule || severity || search || status !== "active") && (
            <button className="btn-quiet text-[11px]" onClick={() => { setParams({}, { replace: true }); setSearch(""); }}>
              <Filter className="h-3.5 w-3.5" /> Clear
            </button>
          )}
        </div>
      </div>

      {query.isLoading ? (
        <div className="space-y-2">{Array.from({ length: 5 }).map((_, index) => <Skeleton key={index} className="h-24" />)}</div>
      ) : findings.length === 0 ? (
        <Card>
          <EmptyState
            illustration="/illustrations/Online learning-rafiki.svg"
            title="No findings match this view"
            description="Try clearing the filters, or upload a file with known data-quality problems."
            action={<Link to="/app/upload" className="btn-primary text-xs">Upload a file</Link>}
          />
        </Card>
      ) : (
        <div className="space-y-2.5">
          {findings.map((finding) => (
            <Link
              key={finding.id}
              to={`/app/findings/${finding.id}`}
              className="card group flex flex-wrap items-start gap-3 p-4 transition hover:-translate-y-0.5 hover:border-brand/25 hover:shadow-[var(--shadow-lift)] sm:p-5"
            >
              <span className="mt-0.5"><SeverityBadge severity={finding.severity} /></span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1">
                  <h3 className="text-[13.5px] font-bold text-ink">{finding.title}</h3>
                  <span className="text-[10px] font-bold uppercase tracking-[0.12em] text-ink-soft/50">{finding.ref}</span>
                  <span className="chip bg-black/[0.04] text-[10px] text-ink-soft">{titleCase(finding.rule_code)}</span>
                  {finding.policy_assumption && <Badge tone="amber">Assumption used</Badge>}
                </div>
                <p className="mt-1 line-clamp-2 max-w-4xl text-[12px] leading-relaxed text-ink-soft">{finding.explanation}</p>
                <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[10.5px] text-ink-soft/70">
                  <span>{finding.institution_name ?? "Institution"}</span>
                  <span>Raised {dateLabel(finding.created_at)}</span>
                  {finding.enrolment_id && <span>Enrolment #{finding.enrolment_id}</span>}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <StatusBadge status={finding.status} />
                <ArrowUpRight className="h-4 w-4 text-ink-soft/40 transition group-hover:text-brand" />
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
