import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Building2, MapPin, Search } from "lucide-react";
import { api } from "../lib/api";
import type { CentralDashboard, IntakeRow } from "../lib/types";
import { num, pct } from "../lib/format";
import { Badge, Card, Modal, PageHeader, ProgressBar, Skeleton, Tabs } from "../components/ui";

interface IntakeResponse {
  institution: { id: number; name: string; code: string };
  intake: IntakeRow[];
}

export default function InstitutionsPage() {
  const [search, setSearch] = useState("");
  const [state, setState] = useState("all");
  const [selected, setSelected] = useState<{ id: number; name: string } | null>(null);
  const query = useQuery({ queryKey: ["central-dashboard"], queryFn: () => api<CentralDashboard>("/dashboard/central") });
  const intake = useQuery({
    queryKey: ["intake", selected?.id],
    queryFn: () => api<IntakeResponse>(`/institutions/${selected?.id}/intake`),
    enabled: Boolean(selected),
  });

  const states = useMemo(() => ["all", ...new Set((query.data?.institutions ?? []).map((row) => row.state))], [query.data]);
  const rows = useMemo(() => {
    let list = query.data?.institutions ?? [];
    if (state !== "all") list = list.filter((row) => row.state === state);
    if (search) {
      const needle = search.toLowerCase();
      list = list.filter((row) => row.name.toLowerCase().includes(needle) || row.code.toLowerCase().includes(needle));
    }
    return list;
  }, [query.data, search, state]);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Institution register"
        title="Twelve fictional colleges, one workflow."
        description="Approved intake, readiness and open flags per institution. Open a college to inspect its programme-level intake table."
      />

      <div className="flex flex-wrap items-center gap-2">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-soft/50" />
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search name or AICTE code" className="input !py-2 !pl-9 text-xs sm:w-64" />
        </div>
        <Tabs tabs={states.map((item) => ({ key: item, label: item === "all" ? "All states" : item }))} active={state} onChange={setState} />
      </div>

      {query.isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">{Array.from({ length: 6 }).map((_, index) => <Skeleton key={index} className="h-52" />)}</div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          {rows.map((row) => (
            <Card key={row.institution_id} className="group p-5 transition hover:-translate-y-0.5 hover:border-brand/25 hover:shadow-[var(--shadow-lift)]">
              <div className="flex items-start justify-between gap-3">
                <span className="grid h-10 w-10 place-items-center rounded-2xl bg-brand-soft text-brand">
                  <Building2 className="h-5 w-5" />
                </span>
                <Badge tone={row.anomaly_flagged ? "amber" : row.risk_findings > 0 ? "blue" : "green"}>
                  {row.anomaly_flagged ? "Review" : row.risk_findings > 0 ? `${row.risk_findings} risk` : "Steady"}
                </Badge>
              </div>
              <h2 className="mt-3 text-[14px] font-bold text-ink">{row.short_name}</h2>
              <p className="mt-0.5 line-clamp-1 text-[11px] text-ink-soft">{row.name}</p>
              <p className="mt-2 inline-flex items-center gap-1 text-[10.5px] text-ink-soft"><MapPin className="h-3 w-3" /> {row.state} · {row.code}</p>
              <div className="mt-4 grid grid-cols-3 gap-2 rounded-2xl bg-paper p-3 text-center">
                <div>
                  <p className="text-[15px] font-extrabold text-ink">{num(row.enrolments)}</p>
                  <p className="text-[9px] font-semibold uppercase tracking-[0.1em] text-ink-soft">students</p>
                </div>
                <div>
                  <p className={`text-[15px] font-extrabold ${row.utilisation_pct > 100 ? "text-rose" : "text-ink"}`}>{pct(row.utilisation_pct, 0)}</p>
                  <p className="text-[9px] font-semibold uppercase tracking-[0.1em] text-ink-soft">intake</p>
                </div>
                <div>
                  <p className="text-[15px] font-extrabold text-ink">{row.open_findings}</p>
                  <p className="text-[9px] font-semibold uppercase tracking-[0.1em] text-ink-soft">flags</p>
                </div>
              </div>
              <div className="mt-3">
                <div className="mb-1 flex items-center justify-between text-[9.5px] font-semibold text-ink-soft">
                  <span>APAAR readiness</span><span>{pct(row.readiness_pct, 0)}</span>
                </div>
                <ProgressBar value={row.readiness_pct} tone={row.readiness_pct > 80 ? "green" : row.readiness_pct > 50 ? "amber" : "rose"} height="h-1.5" />
              </div>
              <button onClick={() => setSelected({ id: row.institution_id, name: row.name })} className="btn-ghost mt-4 w-full !py-2 text-[11px]">
                View intake
              </button>
            </Card>
          ))}
        </div>
      )}

      <Modal open={Boolean(selected)} onClose={() => setSelected(null)} title={selected?.name ?? "Intake"} description="Approved intake and regular-seat utilisation by programme." wide>
        {intake.isLoading ? (
          <Skeleton className="h-48" />
        ) : (
          <div className="overflow-x-auto">
            <table className="table-base min-w-[540px]">
              <thead><tr><th>Programme</th><th className="text-right">Approved</th><th className="text-right">Regular</th><th className="text-right">Special</th><th>Used</th></tr></thead>
              <tbody>
                {(intake.data?.intake ?? []).map((row) => {
                  const special = Object.values(row.seat_categories).reduce((sum, value) => sum + value, 0);
                  return (
                    <tr key={`${row.programme_id}-${row.academic_year}`}>
                      <td><p className="text-[12px] font-semibold text-ink">{row.programme_code}</p><p className="max-w-[200px] truncate text-[10px] text-ink-soft">{row.programme_name}</p></td>
                      <td className="text-right tabular-nums">{row.approved_intake}</td>
                      <td className="text-right tabular-nums font-semibold">{row.regular_admitted}</td>
                      <td className="text-right tabular-nums">{special}</td>
                      <td className="w-[120px]">
                        <ProgressBar value={row.utilisation_pct} tone={row.utilisation_pct > 100 ? "rose" : row.utilisation_pct > 90 ? "amber" : "green"} height="h-1.5" />
                        <p className="mt-1 text-[10px] text-ink-soft">{pct(row.utilisation_pct, 0)}</p>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Modal>
    </div>
  );
}
