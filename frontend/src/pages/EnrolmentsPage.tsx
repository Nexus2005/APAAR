import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Download, Search } from "lucide-react";
import { api, apiBlob, downloadBlob } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { EnrolmentRow } from "../lib/types";
import { dateLabel, num, titleCase } from "../lib/format";
import { Badge, Card, EmptyState, PageHeader, Skeleton, StatusBadge } from "../components/ui";

interface EnrolmentsResponse {
  enrolments: EnrolmentRow[];
  count: number;
}

export default function EnrolmentsPage() {
  const { me } = useAuth();
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const query = useQuery({
    queryKey: ["enrolments"],
    queryFn: () => api<EnrolmentsResponse>("/enrolments?limit=400"),
  });

  const rows = useMemo(() => {
    let list = query.data?.enrolments ?? [];
    if (category) list = list.filter((row) => row.seat_category === category);
    if (search) {
      const needle = search.toLowerCase();
      list = list.filter(
        (row) =>
          row.student.toLowerCase().includes(needle) ||
          row.enrolment_ref.toLowerCase().includes(needle) ||
          row.programme_code.toLowerCase().includes(needle) ||
          row.institution_code.toLowerCase().includes(needle),
      );
    }
    return list;
  }, [query.data, search, category]);

  async function download() {
    const blob = await apiBlob("/reports/enrolment.csv");
    downloadBlob(blob, "enrolment-report.csv");
  }

  const canExport = me?.user.role === "institution_admin" || me?.user.role === "central_reviewer" || me?.user.role === "sysadmin";

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Enrolment register"
        title="Every admitted record, privacy-safe by default."
        description="APAAR values are shown masked. Pending and declined records keep a temporary reference and still count toward intake."
        actions={canExport ? <button onClick={download} className="btn-ghost text-xs"><Download className="h-4 w-4" /> Export CSV</button> : undefined}
      />

      <div className="flex flex-wrap items-center gap-2">
        <div className="relative">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-soft/50" />
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search student, ref, programme" className="input !py-2 !pl-9 text-xs sm:w-72" />
        </div>
        <select value={category} onChange={(event) => setCategory(event.target.value)} className="input !w-auto !py-2 text-xs">
          <option value="">All seat categories</option>
          {["regular", "supernumerary", "nri", "oci", "fn", "tfw"].map((item) => <option key={item} value={item}>{titleCase(item)}</option>)}
        </select>
        <span className="ml-auto text-[11px] font-semibold text-ink-soft">{num(rows.length)} records</span>
      </div>

      {query.isLoading ? (
        <Skeleton className="h-96" />
      ) : rows.length === 0 ? (
        <Card><EmptyState title="No enrolments match" description="Adjust the search, or upload an admission file." /></Card>
      ) : (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="table-base min-w-[980px]">
              <thead>
                <tr>
                  <th>Student</th>
                  <th>Enrolment</th>
                  <th>Programme</th>
                  <th>Institution</th>
                  <th>Category</th>
                  <th>APAAR</th>
                  <th>Admitted</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id}>
                    <td>
                      <p className="text-[12px] font-semibold text-ink">{row.student}</p>
                      <p className="text-[10px] text-ink-soft">{row.academic_year}</p>
                    </td>
                    <td className="font-mono text-[10.5px] text-ink-soft">{row.enrolment_ref}</td>
                    <td>
                      <p className="text-[11.5px] font-medium text-ink">{row.programme_code}</p>
                      <p className="max-w-[200px] truncate text-[10px] text-ink-soft">{row.programme}</p>
                    </td>
                    <td className="text-[11px] text-ink-soft">{row.institution}</td>
                    <td><Badge tone={row.seat_category === "regular" ? "slate" : "violet"}>{titleCase(row.seat_category)}</Badge></td>
                    <td>
                      <p className="font-mono text-[10.5px] text-ink-soft">{row.apaar_masked}</p>
                      {row.apaar_status !== "provided" && <Badge tone="amber">{titleCase(row.apaar_status)}</Badge>}
                    </td>
                    <td className="text-[11px] text-ink-soft">{dateLabel(row.admission_date)}</td>
                    <td><StatusBadge status={row.status} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
