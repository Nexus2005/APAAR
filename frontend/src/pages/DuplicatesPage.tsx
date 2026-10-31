import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeftRight, MapPin, ShieldCheck } from "lucide-react";
import { api } from "../lib/api";
import type { DuplicateLink } from "../lib/types";
import { dateLabel } from "../lib/format";
import { Badge, Card, EmptyState, PageHeader, SectionCard, Skeleton, Tabs } from "../components/ui";

interface DuplicatesResponse {
  duplicates: DuplicateLink[];
  count: number;
  whitelisted: number;
}

function Side({ side, tone }: { side: DuplicateLink["a"]; tone: "blue" | "green" }) {
  return (
    <div className={`rounded-2xl border p-4 ${tone === "blue" ? "border-brand/15 bg-brand-soft/30" : "border-mint/20 bg-mint-soft/30"}`}>
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-[12px] font-bold text-ink">{side.institution}</p>
          <p className="text-[10px] text-ink-soft">{side.institution_code} · {side.programme}</p>
        </div>
        <Badge tone={tone === "blue" ? "blue" : "green"}>{side.seat_category}</Badge>
      </div>
      <dl className="mt-3 space-y-1.5 text-[11px]">
        <div className="flex justify-between gap-3"><dt className="text-ink-soft">Student</dt><dd className="font-semibold text-ink">{side.student}</dd></div>
        <div className="flex justify-between gap-3"><dt className="text-ink-soft">Date of birth</dt><dd className="text-ink">{dateLabel(side.dob)}</dd></div>
        <div className="flex justify-between gap-3"><dt className="text-ink-soft">APAAR</dt><dd className="font-mono text-[10px] text-ink-soft">{side.apaar_masked}</dd></div>
        <div className="flex justify-between gap-3"><dt className="text-ink-soft">Admitted</dt><dd className="text-ink">{dateLabel(side.admission_date)}</dd></div>
        <div className="flex justify-between gap-3"><dt className="text-ink-soft">Enrolment</dt><dd className="font-mono text-[10px] text-ink-soft">{side.enrolment_ref}</dd></div>
      </dl>
      <p className="mt-3 line-clamp-2 text-[10.5px] leading-relaxed text-ink-soft/70">{side.programme_name}</p>
    </div>
  );
}

export default function DuplicatesPage() {
  const [tab, setTab] = useState("active");
  const query = useQuery({
    queryKey: ["duplicates"],
    queryFn: () => api<DuplicatesResponse>("/duplicates"),
  });

  const rows = useMemo(() => {
    const list = query.data?.duplicates ?? [];
    if (tab === "whitelisted") return list.filter((row) => row.whitelisted_reason);
    if (tab === "active") return list.filter((row) => !row.whitelisted_reason);
    return list;
  }, [query.data, tab]);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Cross-college duplicates"
        title="One student, two colleges — shown side by side."
        description="Exact matches compare a keyed identifier fingerprint across overlapping years. Fuzzy matches use date of birth and blocked name similarity. A legitimate dual degree can be whitelisted; nothing is auto-rejected."
      />

      <div className="grid gap-4 sm:grid-cols-3">
        <Card className="p-4">
          <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-ink-soft">Awaiting review</p>
          <p className="mt-2 text-[26px] font-extrabold text-ink">{query.data?.count ? query.data.count - query.data.whitelisted : "—"}</p>
        </Card>
        <Card className="p-4">
          <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-ink-soft">Whitelisted</p>
          <p className="mt-2 text-[26px] font-extrabold text-mint">{query.data?.whitelisted ?? "—"}</p>
        </Card>
        <Card className="p-4">
          <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-ink-soft">Match policy</p>
          <p className="mt-2 text-[12px] leading-relaxed text-ink-soft">Name ≥ 90 + matching DOB · overlap-aware · approved dual degrees exempt</p>
        </Card>
      </div>

      <Tabs
        active={tab}
        onChange={setTab}
        tabs={[
          { key: "active", label: "Awaiting review" },
          { key: "whitelisted", label: "Whitelisted" },
          { key: "all", label: "All links" },
        ]}
      />

      {query.isLoading ? (
        <div className="space-y-3">{Array.from({ length: 3 }).map((_, index) => <Skeleton key={index} className="h-64" />)}</div>
      ) : rows.length === 0 ? (
        <Card><EmptyState illustration="/illustrations/Online learning-rafiki.svg" title="No duplicate links in this view" description="Upload files with overlapping students to see detection in action." /></Card>
      ) : (
        <div className="space-y-4">
          {rows.map((link) => (
            <SectionCard
              key={link.id}
              title={`${link.a.student} · ${link.match_type === "exact_apaar" ? "Exact identifier match" : "Fuzzy match"}`}
              description={`Admissions in ${link.a.academic_year}. Match score ${link.score.toFixed(0)}/100.`}
              action={
                <div className="flex items-center gap-2">
                  {link.whitelisted_reason ? <Badge tone="green"><ShieldCheck className="h-3 w-3" /> {link.whitelisted_reason.replace(/_/g, " ")}</Badge> : <Badge tone="amber">Needs human review</Badge>}
                  <span className="text-[10px] text-ink-soft">Link #{link.id}</span>
                </div>
              }
            >
              <div className="grid gap-3 px-5 pb-5 lg:grid-cols-[1fr_auto_1fr] lg:items-center">
                <Side side={link.a} tone="blue" />
                <div className="flex items-center justify-center">
                  <span className="grid h-9 w-9 place-items-center rounded-full border border-line bg-white text-ink-soft shadow-sm">
                    <ArrowLeftRight className="h-4 w-4" />
                  </span>
                </div>
                <Side side={link.b} tone="green" />
              </div>
              <div className="flex flex-wrap items-center gap-x-5 gap-y-1 border-t border-line px-5 py-3 text-[10.5px] text-ink-soft">
                <span className="inline-flex items-center gap-1.5"><MapPin className="h-3 w-3" /> Both enrolments are active in the same academic year.</span>
                <span>Evidence is masked and review-only.</span>
              </div>
            </SectionCard>
          ))}
        </div>
      )}
    </div>
  );
}
