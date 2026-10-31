import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { AlertTriangle, ArrowLeft, CheckCircle2, ShieldOff, ShieldX } from "lucide-react";
import { api } from "../lib/api";
import type { VerifyResult } from "../lib/types";
import { dateTimeLabel } from "../lib/format";
import { Badge, Logo, SimulatedBadge } from "../components/ui";

const CONFIG = {
  VALID: {
    tone: "mint",
    title: "Signature valid",
    subtitle: "This enrolment record was signed by the issuing institution and has not been revoked.",
    icon: CheckCircle2,
    bg: "from-[#0f3d2a] via-[#14523a] to-[#1b6b4a]",
    badge: "bg-[#9CD3B0] text-[#0b2f21]",
  },
  REVOKED: {
    tone: "rose",
    title: "Credential revoked",
    subtitle: "The issuer revoked this record. It must no longer be accepted as evidence of enrolment.",
    icon: ShieldOff,
    bg: "from-[#5e1b16] via-[#7c241d] to-[#9c2f25]",
    badge: "bg-[#FFC9A3] text-[#4a1410]",
  },
  TAMPERED: {
    tone: "amber",
    title: "Tampered record",
    subtitle: "The stored contents no longer match the issuer's signature. Do not trust this record.",
    icon: ShieldX,
    bg: "from-[#5c3809] via-[#7a4d0f] to-[#9a6116]",
    badge: "bg-[#FFE0B2] text-[#4a2c06]",
  },
  NOT_FOUND: {
    tone: "slate",
    title: "No such credential",
    subtitle: "Nothing exists for this reference in the demo register.",
    icon: AlertTriangle,
    bg: "from-[#16233d] via-[#1d2d4c] to-[#274063]",
    badge: "bg-white/90 text-navy",
  },
} as const;

export default function VerifyPage() {
  const { credentialId } = useParams();
  const query = useQuery({
    queryKey: ["verify", credentialId],
    queryFn: () => api<VerifyResult>(`/verify/${credentialId}`),
    enabled: Boolean(credentialId),
    retry: false,
  });

  const result = query.data;
  const config = CONFIG[(result?.status ?? "NOT_FOUND") as keyof typeof CONFIG];
  const Icon = config.icon;

  return (
    <div className="min-h-screen bg-paper">
      <div className="ribbon flex h-6 items-center justify-center px-4">
        <p className="truncate text-[9px] font-bold uppercase tracking-[0.24em] text-white/75">
          SIMULATED — NOT OFFICIAL APAAR VERIFICATION
        </p>
      </div>
      <header className="border-b border-line bg-white">
        <div className="mx-auto flex h-[68px] max-w-4xl items-center justify-between px-5">
          <Link to="/"><Logo /></Link>
          <SimulatedBadge subtle />
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-5 py-10 sm:py-14">
        <Link to="/" className="btn-quiet !px-2 text-xs"><ArrowLeft className="h-3.5 w-3.5" /> Back to APAAR-Setu</Link>

        {query.isLoading || !result ? (
          <div className="mt-6 flex min-h-[300px] items-center justify-center rounded-[2rem] border border-line bg-white">
            {query.isError ? (
              <div className="p-8 text-center">
                <p className="text-sm font-bold text-rose">Could not verify this reference</p>
                <p className="mt-1 text-xs text-ink-soft">Check the backend is running and try again.</p>
              </div>
            ) : (
              <div className="h-9 w-9 animate-spin rounded-full border-2 border-brand/20 border-t-brand" />
            )}
          </div>
        ) : (
          <>
            <div className={`relative mt-6 overflow-hidden rounded-[2rem] bg-gradient-to-br ${config.bg} p-7 text-white shadow-[var(--shadow-lift)] sm:p-9`}>
              <div className="pointer-events-none absolute inset-0 grid-lines opacity-[0.12]" />
              <div className="relative flex flex-wrap items-start justify-between gap-4">
                <div>
                  <span className={`chip ${config.badge}`}>{result.status.replace("_", " ")}</span>
                  <h1 className="serif mt-4 text-[38px] leading-none sm:text-[46px]">{config.title}</h1>
                  <p className="mt-3 max-w-md text-[12.5px] leading-relaxed text-white/65">{config.subtitle}</p>
                </div>
                <span className="grid h-16 w-16 place-items-center rounded-3xl bg-white/10 backdrop-blur">
                  <Icon className="h-8 w-8" strokeWidth={1.6} />
                </span>
              </div>
              <div className="relative mt-7 grid gap-3 border-t border-white/15 pt-5 sm:grid-cols-3">
                <div>
                  <p className="text-[9px] font-bold uppercase tracking-[0.16em] text-white/40">Credential</p>
                  <p className="mt-1 break-all font-mono text-[11px] text-white/90">{result.credential_id}</p>
                </div>
                <div>
                  <p className="text-[9px] font-bold uppercase tracking-[0.16em] text-white/40">Issuer</p>
                  <p className="mt-1 text-[11.5px] text-white/90">{result.issuer_name ?? result.credential?.issuer?.name ?? "Unknown"}</p>
                </div>
                <div>
                  <p className="text-[9px] font-bold uppercase tracking-[0.16em] text-white/40">Issued</p>
                  <p className="mt-1 text-[11.5px] text-white/90">{dateTimeLabel(result.issued_at ?? result.credential?.issuedAt ?? null)}</p>
                </div>
              </div>
            </div>

            <div className="mt-5 grid gap-4 sm:grid-cols-2">
              <div className="card p-5">
                <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-ink-soft">Enrolment claims</p>
                <dl className="mt-3 space-y-2 text-[12px]">
                  {Object.entries(result.credential?.claims ?? {}).map(([key, value]) => (
                    <div key={key} className="flex justify-between gap-3">
                      <dt className="text-ink-soft">{key.replace(/_/g, " ")}</dt>
                      <dd className="text-right font-semibold text-ink">{value}</dd>
                    </div>
                  ))}
                  <div className="flex justify-between gap-3 border-t border-line pt-2">
                    <dt className="text-ink-soft">subject</dt>
                    <dd className="font-mono text-[10.5px] text-ink">{result.credential?.subject?.enrolment_ref ?? "—"}</dd>
                  </div>
                </dl>
              </div>
              <div className="card p-5">
                <p className="text-[10px] font-bold uppercase tracking-[0.14em] text-ink-soft">What this proves</p>
                <ul className="mt-3 space-y-2 text-[11.5px] leading-relaxed text-ink-soft">
                  <li className="flex gap-2"><span className="mt-[6px] h-1.5 w-1.5 shrink-0 rounded-full bg-mint" /> The claims match the issuer's Ed25519 signature.</li>
                  <li className="flex gap-2"><span className="mt-[6px] h-1.5 w-1.5 shrink-0 rounded-full bg-mint" /> The record is not revoked at the time of checking.</li>
                  <li className="flex gap-2"><span className="mt-[6px] h-1.5 w-1.5 shrink-0 rounded-full bg-amber" /> It does <strong>not</strong> prove APAAR authenticity or government endorsement.</li>
                  <li className="flex gap-2"><span className="mt-[6px] h-1.5 w-1.5 shrink-0 rounded-full bg-amber" /> No name, DOB or APAAR is disclosed by this page.</li>
                </ul>
                <div className="mt-4 flex items-center gap-2">
                  <Badge tone={result.signature_valid ? "green" : "rose"}>{result.signature_valid ? "Signature verified" : "Signature failed"}</Badge>
                  {result.revoked_at && <Badge tone="rose">Revoked {dateTimeLabel(result.revoked_at)}</Badge>}
                </div>
                {result.revoke_reason && <p className="mt-2 text-[10.5px] text-ink-soft">Reason: {result.revoke_reason}</p>}
              </div>
            </div>

            <p className="mt-5 text-center text-[10px] leading-relaxed text-ink-soft/60">
              {result.credential?.disclaimer ?? result.credential?.disclaimers ?? "VC-style signed record for a prototype. Not an official certificate."}
            </p>
          </>
        )}
      </main>
    </div>
  );
}
