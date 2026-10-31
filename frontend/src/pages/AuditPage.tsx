import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, RefreshCw, ShieldAlert } from "lucide-react";
import { api } from "../lib/api";
import type { AuditEntry } from "../lib/types";
import { dateTimeLabel, titleCase } from "../lib/format";
import { Alert, Badge, Card, PageHeader, Skeleton } from "../components/ui";

interface AuditResponse {
  entries: AuditEntry[];
}

interface VerifyResponse {
  valid: boolean;
  entries: number;
  broken_seq: number | null;
  message: string;
}

export default function AuditPage() {
  const audit = useQuery({ queryKey: ["audit"], queryFn: () => api<AuditResponse>("/audit?limit=200") });
  const verify = useQuery({ queryKey: ["audit-verify"], queryFn: () => api<VerifyResponse>("/audit/verify") });

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Audit trail"
        title="Every action, chained."
        description="Each entry stores the previous hash and its own SHA-256 over the canonical entry. Verification recomputes the chain and reports the first broken sequence."
        actions={
          <button className="btn-ghost text-xs" onClick={() => { verify.refetch(); audit.refetch(); }}>
            <RefreshCw className="h-4 w-4" /> Re-verify chain
          </button>
        }
      />

      {verify.isLoading ? (
        <Skeleton className="h-24" />
      ) : verify.data ? (
        <Card className={`overflow-hidden ${verify.data.valid ? "border-mint/25" : "border-rose/30"}`}>
          <div className={`flex flex-wrap items-center justify-between gap-4 px-5 py-5 ${verify.data.valid ? "bg-mint-soft/50" : "bg-rose-soft/50"}`}>
            <div className="flex items-center gap-3">
              <span className={`grid h-11 w-11 place-items-center rounded-2xl ${verify.data.valid ? "bg-mint text-white" : "bg-rose text-white"}`}>
                {verify.data.valid ? <CheckCircle2 className="h-5 w-5" /> : <ShieldAlert className="h-5 w-5" />}
              </span>
              <div>
                <p className="text-[15px] font-bold text-ink">{verify.data.valid ? "Chain intact" : `Chain broken at #${verify.data.broken_seq}`}</p>
                <p className="text-[11.5px] text-ink-soft">{verify.data.message}</p>
              </div>
            </div>
            <Badge tone={verify.data.valid ? "green" : "rose"}>{verify.data.entries} entries checked</Badge>
          </div>
        </Card>
      ) : (
        <Alert tone="rose" title="Verification unavailable">Could not recompute the chain.</Alert>
      )}

      <div className="flex items-start gap-2 text-[10.5px] leading-relaxed text-ink-soft/70">
        <ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber" />
        There is no blockchain here. The chain is a local, tamper-evident log. Run <code className="rounded bg-black/5 px-1">python scripts/tamper_demo.py</code> to edit one entry and watch verification name the broken sequence.
      </div>

      {audit.isLoading ? (
        <Skeleton className="h-96" />
      ) : (
        <Card className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="table-base min-w-[960px]">
              <thead>
                <tr>
                  <th>Seq</th>
                  <th>Action</th>
                  <th>Actor</th>
                  <th>Resource</th>
                  <th>When</th>
                  <th>Hash</th>
                </tr>
              </thead>
              <tbody>
                {(audit.data?.entries ?? []).map((entry) => (
                  <tr key={entry.seq}>
                    <td className="font-mono text-[11px] text-ink-soft">#{entry.seq}</td>
                    <td>
                      <p className="text-[11.5px] font-semibold text-ink">{titleCase(entry.action.replace(/\./g, " / "))}</p>
                    </td>
                    <td className="text-[11px] text-ink-soft">{entry.actor}</td>
                    <td className="font-mono text-[10px] text-ink-soft">{entry.resource}</td>
                    <td className="text-[10.5px] text-ink-soft">{dateTimeLabel(entry.at)}</td>
                    <td>
                      <p className="font-mono text-[9.5px] text-ink-soft/80" title={entry.hash}>{entry.hash.slice(0, 16)}…</p>
                      <p className="font-mono text-[9px] text-ink-soft/40" title={entry.prev_hash}>prev {entry.prev_hash.slice(0, 10)}…</p>
                    </td>
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
