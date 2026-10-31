import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Copy, ExternalLink, QrCode, ShieldCheck, ShieldOff } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { CredentialRow } from "../lib/types";
import { dateTimeLabel, titleCase } from "../lib/format";
import {
  Alert,
  Badge,
  EmptyState,
  Modal,
  PageHeader,
  SectionCard,
  Skeleton,
  StatusBadge,
} from "../components/ui";

interface CredentialsResponse {
  credentials: CredentialRow[];
}

interface IssuableResponse {
  enrolments: {
    id: number;
    enrolment_ref: string;
    student: string;
    programme: string;
    academic_year: string;
    status: string;
    has_credential: boolean;
  }[];
}

export default function CredentialsPage() {
  const { me } = useAuth();
  const queryClient = useQueryClient();
  const isAdmin = me?.user.role === "institution_admin";
  const [qr, setQr] = useState<CredentialRow | null>(null);
  const [revoking, setRevoking] = useState<CredentialRow | null>(null);
  const [reason, setReason] = useState("");
  const [feedback, setFeedback] = useState<string | null>(null);

  const credentials = useQuery({ queryKey: ["credentials"], queryFn: () => api<CredentialsResponse>("/credentials") });
  const issuable = useQuery({
    queryKey: ["issuable"],
    queryFn: () => api<IssuableResponse>("/credentials/issuable"),
    enabled: isAdmin,
  });

  const issue = useMutation({
    mutationFn: (enrolmentId: number) =>
      api<{ credential: CredentialRow }>("/credentials/issue", {
        method: "POST",
        body: JSON.stringify({ enrolment_id: enrolmentId }),
      }),
    onSuccess: (data) => {
      setQr(data.credential);
      setFeedback("Credential issued and the enrolment marked verified.");
      queryClient.invalidateQueries({ queryKey: ["credentials"] });
      queryClient.invalidateQueries({ queryKey: ["issuable"] });
    },
    onError: (error) => setFeedback(error instanceof ApiError ? error.message : "Could not issue the credential."),
  });

  const revoke = useMutation({
    mutationFn: ({ id, note }: { id: string; note: string }) =>
      api<{ credential: CredentialRow }>(`/credentials/${id}/revoke`, {
        method: "POST",
        body: JSON.stringify({ reason: note }),
      }),
    onSuccess: () => {
      setRevoking(null);
      setReason("");
      setFeedback("Credential revoked. The public verify page now returns REVOKED.");
      queryClient.invalidateQueries({ queryKey: ["credentials"] });
    },
    onError: (error) => setFeedback(error instanceof ApiError ? error.message : "Could not revoke."),
  });

  const rows = credentials.data?.credentials ?? [];
  const candidates = (issuable.data?.enrolments ?? []).filter((row) => !row.has_credential);

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Trust layer"
        title="Signed enrolment records."
        description="VC-style records signed with each institution's Ed25519 key. The QR contains only the verify URL — no name, date of birth or APAAR."
        actions={<Badge tone="green"><ShieldCheck className="h-3 w-3" /> {rows.filter((row) => row.status === "valid").length} active</Badge>}
      />

      {feedback && (
        <Alert tone={revoke.isError || issue.isError ? "rose" : "green"} action={<button onClick={() => setFeedback(null)} className="text-[11px] underline">Dismiss</button>}>
          {feedback}
        </Alert>
      )}

      <div className="grid gap-5 xl:grid-cols-[1.2fr_0.8fr]">
        <SectionCard title="Issued credentials" description="Revocation takes effect immediately on the public verify page.">
          {credentials.isLoading ? (
            <div className="px-5 pb-5"><Skeleton className="h-40" /></div>
          ) : rows.length === 0 ? (
            <EmptyState illustration="/illustrations/Certification-amico.svg" title="No credentials issued" description="An administrator can issue a credential for any admitted enrolment." />
          ) : (
            <div className="divide-y divide-line">
              {rows.map((row) => (
                <div key={row.credential_id} className="flex flex-wrap items-center gap-3 px-5 py-3.5">
                  <span className={`grid h-9 w-9 place-items-center rounded-2xl ${row.status === "valid" ? "bg-mint-soft text-mint" : "bg-rose-soft text-rose"}`}>
                    {row.status === "valid" ? <ShieldCheck className="h-4 w-4" /> : <ShieldOff className="h-4 w-4" />}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-[12px] font-bold text-ink">{row.student ?? "Student record"}</p>
                    <p className="truncate font-mono text-[10px] text-ink-soft">{row.credential_id} · {row.enrolment_ref}</p>
                  </div>
                  <div className="text-right">
                    <StatusBadge status={row.status} />
                    <p className="mt-1 text-[9.5px] text-ink-soft">{dateTimeLabel(row.issued_at)}</p>
                  </div>
                  <div className="flex gap-1">
                    <button onClick={() => setQr(row)} className="btn-quiet !px-2" title="Show QR"><QrCode className="h-4 w-4" /></button>
                    <a href={row.verify_path} target="_blank" rel="noreferrer" className="btn-quiet !px-2" title="Open verify page"><ExternalLink className="h-4 w-4" /></a>
                    {isAdmin && row.status === "valid" && (
                      <button onClick={() => setRevoking(row)} className="btn-quiet !px-2 text-rose" title="Revoke"><ShieldOff className="h-4 w-4" /></button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </SectionCard>

        <SectionCard
          title="Issue a credential"
          description={isAdmin ? "Verified enrolment records only. The credential contains programme and year — never personal identifiers." : "Only an institution administrator can issue credentials."}
        >
          {!isAdmin ? (
            <EmptyState compact illustration="/illustrations/Graduation-rafiki.svg" title="View-only access" description="Ask your institution administrator to issue a credential." />
          ) : candidates.length === 0 ? (
            <EmptyState compact title="Nothing left to issue" description="Every admitted enrolment already has a valid credential." />
          ) : (
            <div className="max-h-[420px] divide-y divide-line overflow-auto">
              {candidates.slice(0, 50).map((row) => (
                <div key={row.id} className="flex items-center gap-3 px-5 py-3">
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-[11.5px] font-semibold text-ink">{row.student}</p>
                    <p className="truncate text-[10px] text-ink-soft">{row.programme}</p>
                    <p className="font-mono text-[9.5px] text-ink-soft/60">{row.enrolment_ref}</p>
                  </div>
                  <button
                    onClick={() => issue.mutate(row.id)}
                    disabled={issue.isPending}
                    className="btn-primary !px-3 !py-1.5 text-[10.5px]"
                  >
                    Issue
                  </button>
                </div>
              ))}
            </div>
          )}
        </SectionCard>
      </div>

      <Alert tone="blue" title="Not an official certificate">
        These are VC-style signed records for a prototype. They are not W3C-conformant verifiable credentials and are not connected to APAAR, DigiLocker, NAD or ABC.
      </Alert>

      <Modal open={Boolean(qr)} onClose={() => setQr(null)} title="Credential QR" description={qr?.credential_id}>
        {qr && (
          <div className="space-y-4">
            <div className="mx-auto w-fit rounded-3xl border border-line bg-white p-4 shadow-sm">
              <img src={`/api/v1/credentials/${qr.credential_id}/qr.png`} alt="QR code that opens the public verification page" className="h-52 w-52" />
            </div>
            <div className="rounded-2xl bg-paper p-3">
              <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-ink-soft">Public verify link</p>
              <p className="mt-1 break-all font-mono text-[10.5px] text-ink">{window.location.origin}{qr.verify_path}</p>
              <button
                onClick={() => navigator.clipboard?.writeText(`${window.location.origin}${qr.verify_path}`)}
                className="btn-ghost mt-2 !py-1.5 text-[10.5px]"
              >
                <Copy className="h-3.5 w-3.5" /> Copy link
              </button>
            </div>
            <div className="grid grid-cols-2 gap-2 text-[11px]">
              <div className="rounded-xl bg-paper p-3"><span className="text-ink-soft">Student</span><p className="font-semibold text-ink">{qr.student ?? "—"}</p></div>
              <div className="rounded-xl bg-paper p-3"><span className="text-ink-soft">Status</span><p className="font-semibold text-ink">{titleCase(qr.status)}</p></div>
            </div>
            <p className="text-[10.5px] leading-relaxed text-ink-soft">
              The QR encodes only the verification URL. Scanning it reveals no personal data without the credential payload, which itself contains no name, DOB or APAAR.
            </p>
          </div>
        )}
      </Modal>

      <Modal open={Boolean(revoking)} onClose={() => setRevoking(null)} title="Revoke credential" description="This is recorded in the audit chain and cannot be undone through the UI.">
        <div className="space-y-3">
          <label className="label" htmlFor="reason">Reason (required)</label>
          <textarea id="reason" rows={3} value={reason} onChange={(event) => setReason(event.target.value)} className="input text-xs" placeholder="e.g. admission withdrawn after verification" />
          <button
            onClick={() => revoking && revoke.mutate({ id: revoking.credential_id, note: reason })}
            disabled={revoke.isPending || reason.trim().length < 3}
            className="btn w-full bg-rose text-white hover:bg-rose/90"
          >
            {revoke.isPending ? "Revoking…" : "Revoke now"}
          </button>
        </div>
      </Modal>
    </div>
  );
}
