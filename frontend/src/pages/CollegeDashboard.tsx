import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  AlertTriangle,
  ArrowRight,
  ArrowUpRight,
  Download,
  FileWarning,
  Fingerprint,
  IdCard,
  UploadCloud,
  Users,
} from "lucide-react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, apiBlob, downloadBlob } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { InstitutionDashboard } from "../lib/types";
import { dateTimeLabel, num, pct, titleCase } from "../lib/format";
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

function greeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

function monthLabel(month: string) {
  const parsed = new Date(`${month}-01T00:00:00`);
  return parsed.toLocaleDateString("en-IN", { month: "short" });
}

export default function CollegeDashboard() {
  const { me } = useAuth();
  const query = useQuery({
    queryKey: ["institution-dashboard"],
    queryFn: () => api<InstitutionDashboard>("/dashboard/institution"),
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
    return (
      <Alert tone="rose" title="Dashboard unavailable">
        The dashboard could not load. Refresh the page, or check that you are signed in to the right college.
      </Alert>
    );
  }

  const data = query.data;
  const { kpis, institution } = data;
  const over = data.intake.filter((row) => row.status === "red");
  const readinessTone = kpis.apaar_readiness_pct >= 85 ? "green" : kpis.apaar_readiness_pct >= 60 ? "amber" : "rose";
  const seatTone = kpis.seats_left < 0 ? "rose" : kpis.seats_left <= 10 ? "amber" : "green";

  async function download() {
    const blob = await apiBlob("/reports/enrolment.csv");
    downloadBlob(blob, "enrolment-report.csv");
  }

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="College console"
        title={`${greeting()}, ${me?.user.name.split(" ")[0] ?? "there"}.`}
        description={`${institution.name} · ${institution.city}, ${institution.state}. Here is where your admission data stands today.`}
        actions={
          <>
            {me?.user.role === "institution_admin" && (
              <button onClick={download} className="btn-ghost !py-2.5 text-xs">
                <Download className="h-4 w-4" /> Enrolment CSV
              </button>
            )}
            <Link to="/app/upload" className="btn-primary !py-2.5 text-xs">
              <UploadCloud className="h-4 w-4" /> Upload admissions
            </Link>
          </>
        }
      />

      {over.length > 0 && (
        <Alert
          tone="rose"
          title={`${over.length} programme${over.length === 1 ? "" : "s"} above approved intake`}
          action={
            <Link to="/app/findings?rule=INTAKE_EXCEEDED" className="btn bg-rose text-white hover:bg-rose/90 !px-3 !py-1.5 text-[11px]">
              Read the evidence <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          }
        >
          Regular admissions exceed the approved number. This is flagged for human review — no record was rejected automatically.
        </Alert>
      )}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Students admitted"
          value={num(kpis.total_admitted)}
          sub={<span>{num(kpis.regular_admitted)} regular · {pct(kpis.utilisation_pct)} of approved intake</span>}
          icon={<Users className="h-4 w-4" />}
          tone="navy"
        />
        <StatCard
          label="Open findings"
          value={num(kpis.open_findings)}
          sub={
            <span className="inline-flex flex-wrap gap-1.5">
              <Badge tone="red">{kpis.severity_counts.blocker ?? 0} blocker</Badge>
              <Badge tone="amber">{kpis.severity_counts.risk ?? 0} risk</Badge>
              <Badge tone="blue">{kpis.severity_counts.warning ?? 0} warning</Badge>
            </span>
          }
          icon={<FileWarning className="h-4 w-4" />}
          tone="amber"
        />
        <StatCard
          label="APAAR readiness"
          value={pct(kpis.apaar_readiness_pct)}
          sub={<ProgressBar value={kpis.apaar_readiness_pct} tone={readinessTone} className="mt-1" />}
          icon={<IdCard className="h-4 w-4" />}
          tone={readinessTone === "green" ? "green" : "blue"}
        />
        <StatCard
          label="Seats left"
          value={num(kpis.seats_left)}
          sub={<span>{num(kpis.approved_intake)} approved across programmes</span>}
          icon={<Fingerprint className="h-4 w-4" />}
          tone={seatTone === "rose" ? "rose" : seatTone === "amber" ? "amber" : "green"}
        />
      </div>

      <div className="grid gap-5 xl:grid-cols-3">
        <SectionCard
          className="xl:col-span-2"
          title="Approved intake by programme"
          description="Regular seats are counted against approved intake. Special categories are counted separately."
          action={<Badge tone="slate">Policy v{data.assumptions.policy_version}</Badge>}
          bodyClassName="overflow-x-auto"
        >
          <table className="table-base min-w-[680px]">
            <thead>
              <tr>
                <th>Programme</th>
                <th className="text-right">Approved</th>
                <th className="text-right">Regular</th>
                <th className="text-right">Special seats</th>
                <th>Headroom</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {data.intake.map((row) => {
                const special = Object.values(row.seat_categories).reduce((sum, value) => sum + value, 0);
                const tone = row.status === "red" ? "rose" : row.status === "amber" ? "amber" : row.status === "unconfigured" ? "slate" : "green";
                return (
                  <tr key={`${row.programme_id}-${row.academic_year}`}>
                    <td>
                      <p className="font-semibold text-ink">{row.programme_code}</p>
                      <p className="mt-0.5 max-w-[220px] truncate text-[11px] text-ink-soft">{row.programme_name}</p>
                    </td>
                    <td className="text-right tabular-nums">{row.approved_intake || "—"}</td>
                    <td className="text-right font-semibold tabular-nums">{row.regular_admitted}</td>
                    <td className="text-right tabular-nums">{special}</td>
                    <td className="w-[170px]">
                      <div className="flex items-center gap-2">
                        <ProgressBar
                          value={row.approved_intake ? (row.regular_admitted / row.approved_intake) * 100 : 0}
                          tone={tone === "slate" ? "navy" : tone}
                          height="h-1.5"
                          className="w-20"
                        />
                        <span className="text-[11px] font-semibold tabular-nums text-ink-soft">
                          {row.headroom >= 0 ? `${row.headroom} left` : `${Math.abs(row.headroom)} over`}
                        </span>
                      </div>
                    </td>
                    <td className="text-right">
                      <Badge tone={tone}>
                        {row.status === "red" ? "Over" : row.status === "amber" ? "Near cap" : row.status === "unconfigured" ? "No intake" : "Within"}
                      </Badge>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <div className="flex flex-wrap items-center gap-2 border-t border-line px-5 py-3 text-[10.5px] text-ink-soft">
            <span className="font-semibold">Seat caps:</span>
            {Object.entries(data.assumptions.seat_caps)
              .filter(([key]) => key !== "regular")
              .map(([key, meta]) => (
                <span key={key} className="chip bg-black/[0.04] text-ink-soft">
                  {titleCase(key)} {meta.cap_pct_of_approved === null ? "not configured" : `${meta.cap_pct_of_approved}%`}
                  {meta.status === "assumption" && <span className="text-amber">· assumption</span>}
                </span>
              ))}
          </div>
        </SectionCard>

        <Card className="p-5">
          <div className="flex items-start justify-between">
            <div>
              <h2 className="text-[15px] font-bold text-ink">APAAR readiness</h2>
              <p className="mt-1 text-xs text-ink-soft">How many admitted students have a usable identifier.</p>
            </div>
            <Badge tone={readinessTone}>{readinessTone === "green" ? "Healthy" : readinessTone === "amber" ? "Watch" : "Low"}</Badge>
          </div>
          <div className="mt-6 flex items-center gap-5">
            <div
              className="relative grid h-28 w-28 shrink-0 place-items-center rounded-full"
              style={{
                background: `conic-gradient(${
                  readinessTone === "green" ? "#2E8B57" : readinessTone === "amber" ? "#D9822B" : "#C0392B"
                } ${kpis.apaar_readiness_pct}%, #eef0f5 0)`,
              }}
            >
              <div className="grid h-[86px] w-[86px] place-items-center rounded-full bg-white">
                <div className="text-center">
                  <p className="text-[22px] font-extrabold leading-none text-ink">{Math.round(kpis.apaar_readiness_pct)}%</p>
                  <p className="mt-1 text-[9px] font-bold uppercase tracking-[0.12em] text-ink-soft">linked</p>
                </div>
              </div>
            </div>
            <div className="flex-1 space-y-3">
              {[
                ["Linked", kpis.apaar_linked, "bg-mint"],
                ["Pending / declined", kpis.apaar_pending_declined, "bg-amber"],
                ["Missing", kpis.apaar_missing, "bg-rose"],
              ].map(([label, value, color]) => (
                <div key={String(label)} className="flex items-center justify-between gap-2 text-[12px]">
                  <span className="inline-flex items-center gap-2 text-ink-soft">
                    <span className={`h-2 w-2 rounded-full ${color}`} />
                    {label}
                  </span>
                  <span className="font-bold tabular-nums text-ink">{num(Number(value))}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="mt-6 rounded-2xl bg-paper px-4 py-3 text-[11px] leading-relaxed text-ink-soft">
            Pending and declined records still count toward intake. They are shown as a lane, never as an error.
          </div>
          <Link to="/app/enrolments" className="btn-ghost mt-4 w-full !py-2 text-[11.5px]">
            Open enrolment register <ArrowUpRight className="h-3.5 w-3.5" />
          </Link>
        </Card>
      </div>

      <div className="grid gap-5 xl:grid-cols-3">
        <SectionCard
          className="xl:col-span-2"
          title="Admissions across the window"
          description="Dated admissions from the seeded uploads. Spikes are one input into the anomaly scorer."
          bodyClassName="px-2 pb-2"
        >
          <div className="h-[240px] w-full">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={data.trend} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="admissions" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#2F6FED" stopOpacity={0.28} />
                    <stop offset="100%" stopColor="#2F6FED" stopOpacity={0.02} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 6" stroke="#E5E8EF" vertical={false} />
                <XAxis dataKey="month" tickFormatter={monthLabel} tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: "#7b8496" }} />
                <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: "#7b8496" }} width={38} />
                <Tooltip
                  cursor={{ stroke: "#2F6FED", strokeDasharray: "4 4" }}
                  contentStyle={{ borderRadius: 14, border: "1px solid #E5E8EF", fontSize: 12, boxShadow: "0 10px 30px -12px rgba(13,24,48,.25)" }}
                  labelFormatter={(label) => monthLabel(String(label))}
                />
                <Area type="monotone" dataKey="admitted" stroke="#2F6FED" strokeWidth={2.4} fill="url(#admissions)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </SectionCard>

        <SectionCard
          title="Latest uploads"
          description="Re-uploading the same file is idempotent."
          action={<Link to="/app/upload" className="text-[11px] font-semibold text-brand">New upload</Link>}
        >
          {data.uploads.length === 0 ? (
            <EmptyState compact illustration="/illustrations/Taking notes-amico.svg" title="No uploads yet" />
          ) : (
            <div className="divide-y divide-line">
              {data.uploads.map((upload) => (
                <div key={upload.id} className="px-5 py-3">
                  <div className="flex items-center justify-between gap-2">
                    <p className="truncate text-[12px] font-semibold text-ink">{upload.filename}</p>
                    <StatusBadge status={upload.status} />
                  </div>
                  <p className="mt-1 text-[10.5px] text-ink-soft">
                    {dateTimeLabel(upload.uploaded_at)} · {upload.accepted_rows} accepted · {upload.rejected_rows} rejected
                  </p>
                  {upload.pending_lane_rows > 0 && (
                    <p className="mt-1 text-[10px] font-medium text-amber">{upload.pending_lane_rows} on the pending/declined lane</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </SectionCard>
      </div>

      <SectionCard
        title="Findings needing your attention"
        description="Each finding carries the rule, the evidence and the policy assumption used."
        action={<Link to="/app/findings" className="text-[11px] font-semibold text-brand">All findings</Link>}
      >
        {data.findings.length === 0 ? (
          <EmptyState illustration="/illustrations/Online learning-rafiki.svg" title="No open findings" description="Every deterministic check currently passes for this college." />
        ) : (
          <div className="divide-y divide-line">
            {data.findings.map((finding) => (
              <Link
                key={finding.id}
                to={`/app/findings/${finding.id}`}
                className="flex flex-wrap items-start gap-3 px-5 py-4 transition hover:bg-brand-soft/20"
              >
                <span className="mt-0.5">
                  <SeverityBadge severity={finding.severity} />
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-[13px] font-bold text-ink">{finding.title}</p>
                    <span className="text-[10px] font-semibold uppercase tracking-[0.1em] text-ink-soft/60">{finding.ref}</span>
                  </div>
                  <p className="mt-1 line-clamp-2 text-[11.5px] leading-relaxed text-ink-soft">{finding.explanation}</p>
                </div>
                <StatusBadge status={finding.status} />
                <ArrowUpRight className="mt-1 h-4 w-4 shrink-0 text-ink-soft/40" />
              </Link>
            ))}
          </div>
        )}
      </SectionCard>

      <div className="flex items-start gap-2 px-1 text-[10.5px] leading-relaxed text-ink-soft/70">
        <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber" />
        Seat caps and the admission window are prototype assumptions from <code className="rounded bg-black/5 px-1">config/rules.yaml</code>.
        A human must confirm them against the AICTE Approval Process Handbook.
      </div>
    </div>
  );
}
