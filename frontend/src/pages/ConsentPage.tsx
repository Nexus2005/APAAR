import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, ClipboardCheck, Copy, Lock, Send, ShieldCheck, X } from "lucide-react";
import { api, ApiError } from "../lib/api";
import { useAuth } from "../lib/auth";
import type { ConsentRequest } from "../lib/types";
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

interface RequestsResponse {
  requests: ConsentRequest[];
  role: "student" | "verifier";
}

interface FieldsResponse {
  fields: { key: string; label: string }[];
  never_shared: string[];
}

interface ShareResponse {
  consent_request_id: number;
  purpose: string;
  fields: Record<string, string | boolean | null>;
  shared_at: string;
  expires_at: string;
  note: string;
}

export default function ConsentPage() {
  const { me } = useAuth();
  const queryClient = useQueryClient();
  const role = me?.user.role;
  const [enrolmentRef, setEnrolmentRef] = useState("");
  const [purpose, setPurpose] = useState("");
  const [selectedFields, setSelectedFields] = useState<string[]>(["enrolled", "programme"]);
  const [token, setToken] = useState("");
  const [share, setShare] = useState<ShareResponse | null>(null);
  const [tokenModal, setTokenModal] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  const requests = useQuery({
    queryKey: ["consent-requests"],
    queryFn: () => api<RequestsResponse>("/consent/requests/mine"),
    enabled: role === "student" || role === "verifier",
  });
  const fields = useQuery({
    queryKey: ["consent-fields"],
    queryFn: () => api<FieldsResponse>("/consent/fields"),
    enabled: role === "verifier",
  });

  const createRequest = useMutation({
    mutationFn: () =>
      api<{ request: ConsentRequest }>("/consent/requests", {
        method: "POST",
        body: JSON.stringify({ enrolment_ref: enrolmentRef.trim(), fields: selectedFields, purpose }),
      }),
    onSuccess: () => {
      setFeedback("Consent request sent. The student decides what happens next.");
      setPurpose("");
      queryClient.invalidateQueries({ queryKey: ["consent-requests"] });
    },
    onError: (error) => setFeedback(error instanceof ApiError ? error.message : "Could not create the request."),
  });

  const decide = useMutation({
    mutationFn: ({ id, approve }: { id: number; approve: boolean }) =>
      api<{ share_token: string | null }>(`/consent/requests/${id}/decision`, {
        method: "POST",
        body: JSON.stringify({ approve }),
      }),
    onSuccess: (data) => {
      setFeedback(data.share_token ? "Approved. Share the one-time token with the verifier." : "Denied. No data will be shared.");
      if (data.share_token) setTokenModal(data.share_token);
      queryClient.invalidateQueries({ queryKey: ["consent-requests"] });
    },
    onError: (error) => setFeedback(error instanceof ApiError ? error.message : "Could not record your decision."),
  });

  const readShare = useMutation({
    mutationFn: () => api<ShareResponse>(`/consent/share/${token.trim()}`),
    onSuccess: (data) => {
      setShare(data);
      setFeedback("Consented facts retrieved. This access was logged.");
    },
    onError: (error) => {
      setShare(null);
      setFeedback(error instanceof ApiError ? error.message : "Could not read the share link.");
    },
  });

  if (role !== "student" && role !== "verifier") {
    return <Alert tone="amber" title="Consent inbox">Sign in as a student or verifier to use the consent flow.</Alert>;
  }

  const isStudent = role === "student";

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Consent-gated verification"
        title={isStudent ? "You decide who sees what." : "Ask first. Then read only what was approved."}
        description={
          isStudent
            ? "Each request names the verifier, the purpose and the exact fields. Approving creates a single-use, expiring token. APAAR, name and DOB are never shareable."
            : "Request specific facts for a stated purpose. The student approves or denies. The verifier receives only allow-listed fields, and every access is logged."
        }
        actions={<Badge tone="green"><Lock className="h-3 w-3" /> APAAR never shared</Badge>}
      />

      {feedback && (
        <Alert tone={createRequest.isError || decide.isError || readShare.isError ? "rose" : "green"} action={<button onClick={() => setFeedback(null)} className="text-[11px] underline">Dismiss</button>}>
          {feedback}
        </Alert>
      )}

      <div className={`grid gap-5 ${isStudent ? "" : "xl:grid-cols-[0.9fr_1.1fr]"}`}>
        {!isStudent && (
          <div className="space-y-4">
            <SectionCard title="New consent request" description="The student sees your name, purpose and the requested fields.">
              <div className="space-y-3 px-5 pb-5">
                <div>
                  <label className="label" htmlFor="enrolment">Enrolment reference</label>
                  <input id="enrolment" value={enrolmentRef} onChange={(event) => setEnrolmentRef(event.target.value)} placeholder="ENR-2026-00010002" className="input font-mono text-xs" />
                  <p className="mt-1 text-[10px] text-ink-soft">Copy one from the college console or a credential.</p>
                </div>
                <div>
                  <label className="label" htmlFor="purpose">Purpose</label>
                  <input id="purpose" value={purpose} onChange={(event) => setPurpose(event.target.value)} placeholder="e.g. education-loan eligibility check" className="input text-xs" />
                </div>
                <div>
                  <p className="label">Requested fields</p>
                  <div className="grid grid-cols-2 gap-1.5">
                    {(fields.data?.fields ?? []).map((field) => {
                      const active = selectedFields.includes(field.key);
                      return (
                        <button
                          key={field.key}
                          type="button"
                          onClick={() => setSelectedFields((current) => active ? current.filter((item) => item !== field.key) : [...current, field.key])}
                          className={`rounded-xl border px-3 py-2 text-left text-[10.5px] transition ${active ? "border-brand/40 bg-brand-soft text-brand-dark" : "border-line bg-white text-ink-soft hover:border-brand/25"}`}
                        >
                          {field.label}
                        </button>
                      );
                    })}
                  </div>
                </div>
                <button
                  onClick={() => createRequest.mutate()}
                  disabled={createRequest.isPending || !enrolmentRef.trim() || purpose.trim().length < 3 || selectedFields.length === 0}
                  className="btn-primary w-full text-xs"
                >
                  <Send className="h-4 w-4" /> {createRequest.isPending ? "Sending…" : "Send request"}
                </button>
              </div>
            </SectionCard>

            <SectionCard title="Redeem a share token" description="The student shares a one-time token after approving.">
              <div className="space-y-3 px-5 pb-5">
                <input value={token} onChange={(event) => setToken(event.target.value)} placeholder="Paste one-time token" className="input font-mono text-xs" />
                <button onClick={() => readShare.mutate()} disabled={readShare.isPending || !token.trim()} className="btn-dark w-full text-xs">
                  <ShieldCheck className="h-4 w-4" /> {readShare.isPending ? "Checking…" : "Read consented facts"}
                </button>
                {share && (
                  <div className="rounded-2xl border border-mint/25 bg-mint-soft/40 p-4">
                    <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-mint">Consented facts</p>
                    <dl className="mt-2 space-y-1.5 text-[12px]">
                      {Object.entries(share.fields).map(([key, value]) => (
                        <div key={key} className="flex justify-between gap-3">
                          <dt className="text-ink-soft">{titleCase(key)}</dt>
                          <dd className="font-semibold text-ink">{String(value)}</dd>
                        </div>
                      ))}
                    </dl>
                    <p className="mt-2 text-[10px] leading-relaxed text-ink-soft">Expires {dateTimeLabel(share.expires_at)} · this access was written to the log.</p>
                  </div>
                )}
              </div>
            </SectionCard>
          </div>
        )}

        <SectionCard title={isStudent ? "Requests for you" : "Your requests"} description={isStudent ? "Approving issues one token, valid until the request expires." : "Only approved requests can be read, and only with the token the student shares."}>
          {requests.isLoading ? (
            <div className="px-5 pb-5"><Skeleton className="h-40" /></div>
          ) : (requests.data?.requests.length ?? 0) === 0 ? (
            <EmptyState illustration="/illustrations/Book lover-pana.svg" title="Nothing waiting" description={isStudent ? "No verifier has asked you for anything yet." : "Create a request to begin the consent flow."} />
          ) : (
            <div className="divide-y divide-line">
              {requests.data?.requests.map((request) => (
                <div key={request.id} className="px-5 py-4">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <p className="text-[12.5px] font-bold text-ink">{request.purpose}</p>
                      <p className="mt-0.5 text-[10.5px] text-ink-soft">
                        {isStudent ? `From ${request.verifier_name}` : `To ${request.student_display ?? "student"}`} · created {dateTimeLabel(request.created_at)}
                      </p>
                    </div>
                    <StatusBadge status={request.status} />
                  </div>
                  <div className="mt-2 flex flex-wrap gap-1.5">
                    {request.fields.map((field) => <span key={field} className="chip bg-black/[0.04] text-[10px] text-ink-soft">{titleCase(field)}</span>)}
                    <span className="chip bg-brand-soft text-[10px] text-brand-dark">expires {dateTimeLabel(request.expires_at)}</span>
                  </div>
                  {isStudent && request.status === "pending" && (
                    <div className="mt-3 flex gap-2">
                      <button onClick={() => decide.mutate({ id: request.id, approve: true })} disabled={decide.isPending} className="btn bg-mint text-white hover:bg-mint/90 flex-1 !py-2 text-[11px]">
                        <Check className="h-3.5 w-3.5" /> Approve
                      </button>
                      <button onClick={() => decide.mutate({ id: request.id, approve: false })} disabled={decide.isPending} className="btn-ghost flex-1 !py-2 text-[11px]">
                        <X className="h-3.5 w-3.5" /> Deny
                      </button>
                    </div>
                  )}
                  {!isStudent && request.status === "pending" && (
                    <p className="mt-2 text-[10.5px] text-amber">Waiting for the student's decision. You cannot read anything yet.</p>
                  )}
                </div>
              ))}
            </div>
          )}
        </SectionCard>
      </div>

      <div className="grid gap-3 rounded-3xl border border-line bg-white p-5 sm:grid-cols-3">
        {[
          ["Purpose-bound", "Every request states why the data is needed."],
          ["Allow-listed", "Only enrolled, programme, year, institution and status can ever be shared."],
          ["Audited", "Approvals, denials and reads land in the access log and audit chain."],
        ].map(([title, body]) => (
          <div key={title} className="flex gap-3">
            <ClipboardCheck className="mt-0.5 h-4 w-4 shrink-0 text-mint" />
            <div>
              <p className="text-[11.5px] font-bold text-ink">{title}</p>
              <p className="mt-0.5 text-[10.5px] leading-relaxed text-ink-soft">{body}</p>
            </div>
          </div>
        ))}
      </div>

      <Modal open={Boolean(tokenModal)} onClose={() => setTokenModal(null)} title="One-time share token" description="Give this to the verifier. It expires with the request.">
        <div className="space-y-3">
          <div className="rounded-2xl border border-line bg-paper p-4">
            <p className="break-all font-mono text-[12px] text-ink">{tokenModal}</p>
          </div>
          <button
            onClick={() => tokenModal && navigator.clipboard?.writeText(tokenModal)}
            className="btn-primary w-full text-xs"
          >
            <Copy className="h-4 w-4" /> Copy token
          </button>
          <p className="text-[10.5px] leading-relaxed text-ink-soft">
            The token is shown once. It grants read access only to the fields you approved, for the stated purpose, until it expires.
          </p>
        </div>
      </Modal>
    </div>
  );
}
