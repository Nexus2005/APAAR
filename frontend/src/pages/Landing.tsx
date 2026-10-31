import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  ArrowRight,
  ArrowUpRight,
  BadgeCheck,
  Building2,
  FileSpreadsheet,
  Fingerprint,
  Layers,
  Lock,
  QrCode,
  ScanSearch,
  ShieldCheck,
  Sparkles,
  Users,
} from "lucide-react";
import { Logo, SimulatedBadge } from "../components/ui";

const WORKFLOW = [
  {
    step: "01",
    title: "Bring the messy file",
    body: "CSV, XLSX or an ERP feed. Column mapping is suggested, then confirmed by a human — never guessed silently.",
    icon: FileSpreadsheet,
  },
  {
    step: "02",
    title: "Every row gets an answer",
    body: "Required fields, APAAR format and a simulated identity lookup. Rejected rows come with codes and a downloadable error file.",
    icon: ScanSearch,
  },
  {
    step: "03",
    title: "Rules flag, humans decide",
    body: "Approved intake, seat categories, duplicates and anomalies become evidence-backed findings with a review history.",
    icon: ShieldCheck,
  },
];

const FEATURES = [
  {
    icon: Layers,
    title: "Separate seat counters",
    body: "Regular, supernumerary, NRI, OCI and FN seats are counted independently. Policy numbers live in versioned config.",
  },
  {
    icon: Fingerprint,
    title: "Cross-college duplicates",
    body: "Keyed identifier matching plus blocked fuzzy matching finds the same student in two institutions, with both records side by side.",
  },
  {
    icon: Sparkles,
    title: "Explainable prioritisation",
    body: "An anomaly score ranks colleges for review using plain-language reasons. Never a fraud verdict, never a penalty.",
  },
  {
    icon: QrCode,
    title: "Signed QR records",
    body: "Ed25519-signed enrolment records verify as VALID, REVOKED or TAMPERED — with no name, DOB or APAAR inside the QR.",
  },
  {
    icon: Lock,
    title: "Consent-gated sharing",
    body: "A verifier asks. The student approves. Only allow-listed fields are shared, once, with an expiry and an access log.",
  },
  {
    icon: BadgeCheck,
    title: "Tamper-evident audit",
    body: "Every action joins a SHA-256 hash chain. Verification recomputes the chain and names the first broken entry.",
  },
];

const AUDIENCES = [
  {
    tag: "For colleges",
    title: "Upload, fix, respond",
    body: "See exactly which rows failed and why. Track headroom per programme before a breach, not after.",
    icon: Building2,
  },
  {
    tag: "For AICTE",
    title: "One review queue",
    body: "Intake utilisation, readiness and prioritised institutions across states — with the evidence behind each flag.",
    icon: Users,
  },
  {
    tag: "For verifiers",
    title: "Ask, don't browse",
    body: "Request a single fact with a stated purpose. The student decides; the access log records the outcome.",
    icon: BadgeCheck,
  },
];

export default function Landing() {
  const navigate = useNavigate();
  const [credential, setCredential] = useState("");

  function verify(event: FormEvent) {
    event.preventDefault();
    const trimmed = credential.trim();
    if (trimmed) navigate(`/verify/${encodeURIComponent(trimmed)}`);
  }

  return (
    <div className="min-h-screen bg-paper">
      <div className="ribbon flex h-6 items-center justify-center px-4">
        <p className="truncate text-[9px] font-bold uppercase tracking-[0.24em] text-white/75">
          SIMULATED — NOT OFFICIAL APAAR VERIFICATION · synthetic demo data only
        </p>
      </div>

      <header className="sticky top-0 z-40 border-b border-line/60 bg-paper/80 backdrop-blur-xl">
        <div className="mx-auto flex h-[72px] max-w-[1240px] items-center justify-between px-5 lg:px-8">
          <Link to="/" aria-label="APAAR-Setu home">
            <Logo />
          </Link>
          <nav className="hidden items-center gap-7 text-[13px] font-semibold text-ink-soft md:flex">
            <a className="transition hover:text-ink" href="#workflow">How it works</a>
            <a className="transition hover:text-ink" href="#platform">Platform</a>
            <a className="transition hover:text-ink" href="#trust">Trust layer</a>
            <a className="transition hover:text-ink" href="#verify">Verify</a>
          </nav>
          <div className="flex items-center gap-2">
            <Link to="/login" className="btn-quiet hidden text-[13px] sm:inline-flex">
              Sign in
            </Link>
            <Link to="/login" className="btn-primary !px-4 text-[13px]">
              Open console
              <ArrowUpRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </header>

      <main>
        <section className="relative overflow-hidden">
          <div className="mesh pointer-events-none absolute inset-0" />
          <div className="grid-lines pointer-events-none absolute inset-0 opacity-40 [mask-image:radial-gradient(ellipse_at_center,black,transparent_75%)]" />
          <div className="relative mx-auto grid max-w-[1240px] items-center gap-12 px-5 pb-16 pt-14 lg:grid-cols-[1.05fr_0.95fr] lg:gap-8 lg:px-8 lg:pb-24 lg:pt-20">
            <div className="animate-fade-up">
              <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-line bg-white/80 px-3 py-1.5 text-[10.5px] font-bold uppercase tracking-[0.16em] text-ink-soft backdrop-blur">
                <span className="h-1.5 w-1.5 rounded-full bg-mint" />
                Institutional Intake & Verification Platform
              </div>
              <h1 className="serif text-[46px] leading-[0.98] tracking-[-0.03em] text-ink sm:text-[62px] lg:text-[68px]">
                Enrolment integrity,
                <br />
                <span className="italic text-brand">with humans</span> in the loop.
              </h1>
              <p className="mt-6 max-w-[520px] text-[15px] leading-relaxed text-ink-soft">
                APAAR-Setu maps college admission files, validates every row, checks approved intake
                and seat categories, and surfaces duplicates and anomalies as evidence — for people
                to review, never for software to punish.
              </p>
              <div className="mt-8 flex flex-wrap items-center gap-3">
                <Link to="/login" className="btn-primary !px-6 !py-3">
                  Explore the prototype
                  <ArrowRight className="h-4 w-4" />
                </Link>
                <a href="#verify" className="btn-ghost !px-5 !py-3">
                  <QrCode className="h-4 w-4 text-brand" />
                  Verify a certificate
                </a>
              </div>
              <div className="mt-8 flex flex-wrap items-center gap-x-5 gap-y-2 text-[11.5px] font-medium text-ink-soft">
                <span className="inline-flex items-center gap-1.5"><ShieldCheck className="h-3.5 w-3.5 text-mint" /> Humans decide</span>
                <span className="inline-flex items-center gap-1.5"><Lock className="h-3.5 w-3.5 text-mint" /> Privacy by construction</span>
                <span className="inline-flex items-center gap-1.5"><Layers className="h-3.5 w-3.5 text-mint" /> Works offline</span>
              </div>
            </div>

            <div className="relative animate-fade-up delay-2">
              <div className="absolute -inset-4 rounded-[2.5rem] bg-gradient-to-tr from-brand/10 via-transparent to-mint/10 blur-2xl" />
              <div className="relative overflow-hidden rounded-[2.2rem] border border-white/70 bg-white/70 p-3 shadow-[var(--shadow-lift)] backdrop-blur-xl">
                <div className="relative overflow-hidden rounded-[1.6rem] bg-gradient-to-br from-[#eef3ff] via-white to-[#eef7f1]">
                  <img
                    src="/illustrations/college admission-bro.svg"
                    alt="Illustration of students reviewing college admission records"
                    className="h-[330px] w-full object-contain p-4 sm:h-[390px]"
                  />
                  <div className="pointer-events-none absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-white/70 to-transparent" />
                </div>
                <div className="absolute left-5 top-6 rounded-2xl border border-white/80 bg-white/90 px-3.5 py-2.5 shadow-[var(--shadow-soft)] backdrop-blur animate-float">
                  <p className="text-[9px] font-bold uppercase tracking-[0.16em] text-ink-soft">Rules engine</p>
                  <p className="mt-1 text-[13px] font-extrabold text-ink">14 deterministic checks</p>
                </div>
                <div className="absolute right-5 top-24 rounded-2xl border border-white/80 bg-white/90 px-3.5 py-2.5 shadow-[var(--shadow-soft)] backdrop-blur animate-float [animation-delay:1.6s]">
                  <div className="flex items-center gap-2">
                    <span className="grid h-7 w-7 place-items-center rounded-full bg-mint-soft text-mint">
                      <ShieldCheck className="h-3.5 w-3.5" />
                    </span>
                    <div>
                      <p className="text-[9px] font-bold uppercase tracking-[0.14em] text-ink-soft">Certificate</p>
                      <p className="text-[12px] font-extrabold text-mint">SIGNATURE VALID</p>
                    </div>
                  </div>
                </div>
                <div className="absolute bottom-5 right-5 rounded-2xl border border-white/80 bg-white/90 px-3.5 py-2.5 shadow-[var(--shadow-soft)] backdrop-blur">
                  <p className="text-[9px] font-bold uppercase tracking-[0.16em] text-ink-soft">APAAR lane</p>
                  <p className="mt-1 text-[12px] font-extrabold text-ink">pending · declined · linked</p>
                </div>
              </div>
              <div className="mt-4 flex items-center justify-center gap-2">
                <SimulatedBadge subtle />
                <span className="text-[10.5px] text-ink-soft">Illustrative interface. No real student data.</span>
              </div>
            </div>
          </div>
        </section>

        <section className="border-y border-line bg-white/60">
          <div className="mx-auto grid max-w-[1240px] grid-cols-2 divide-line px-5 py-7 sm:grid-cols-4 lg:px-8">
            {[
              ["12", "fictional institutions"],
              ["4", "states in the demo"],
              ["1,652", "synthetic admission rows"],
              ["0", "automatic penalties"],
            ].map(([value, label]) => (
              <div key={label} className="px-2 py-2 text-center">
                <p className="serif text-[26px] text-ink">{value}</p>
                <p className="mt-1 text-[10.5px] font-semibold uppercase tracking-[0.12em] text-ink-soft">{label}</p>
              </div>
            ))}
          </div>
        </section>

        <section id="workflow" className="mx-auto max-w-[1240px] px-5 py-20 lg:px-8">
          <div className="mx-auto max-w-2xl text-center">
            <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-brand">The workflow</p>
            <h2 className="serif mt-3 text-[36px] leading-tight text-ink sm:text-[44px]">
              From a spreadsheet to a reviewable finding
            </h2>
            <p className="mt-4 text-sm leading-relaxed text-ink-soft">
              No black boxes. Every flag shows what was compared, why it matters, which policy
              assumption applied, and what a person can do next.
            </p>
          </div>
          <div className="mt-12 grid gap-4 md:grid-cols-3">
            {WORKFLOW.map((item) => (
              <article key={item.step} className="card group relative overflow-hidden p-6 transition hover:-translate-y-1 hover:shadow-[var(--shadow-lift)]">
                <span className="serif absolute right-5 top-4 text-[54px] leading-none text-brand/[0.08]">{item.step}</span>
                <span className="grid h-11 w-11 place-items-center rounded-2xl bg-brand-soft text-brand-dark">
                  <item.icon className="h-5 w-5" strokeWidth={1.7} />
                </span>
                <h3 className="mt-5 text-[16px] font-bold text-ink">{item.title}</h3>
                <p className="mt-2 text-[12.5px] leading-relaxed text-ink-soft">{item.body}</p>
              </article>
            ))}
          </div>
        </section>

        <section id="platform" className="relative overflow-hidden bg-navy-deep py-20">
          <div className="pointer-events-none absolute inset-0 grid-lines opacity-[0.12]" />
          <div className="pointer-events-none absolute -left-32 top-0 h-96 w-96 rounded-full bg-brand/20 blur-[100px]" />
          <div className="pointer-events-none absolute -right-24 bottom-0 h-80 w-80 rounded-full bg-mint/15 blur-[100px]" />
          <div className="relative mx-auto max-w-[1240px] px-5 lg:px-8">
            <div className="flex flex-wrap items-end justify-between gap-6">
              <div className="max-w-xl">
                <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-[#9CC4FF]">Platform</p>
                <h2 className="serif mt-3 text-[36px] leading-tight text-white sm:text-[44px]">
                  Built for the questions after the upload
                </h2>
              </div>
              <p className="max-w-sm text-[12.5px] leading-relaxed text-white/50">
                Six capabilities that make the difference between a data-entry tool and an
                auditable integrity workflow.
              </p>
            </div>
            <div className="mt-10 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {FEATURES.map((feature) => (
                <article key={feature.title} className="group rounded-3xl border border-white/10 bg-white/[0.04] p-5 transition hover:border-white/20 hover:bg-white/[0.07]">
                  <span className="grid h-9 w-9 place-items-center rounded-xl bg-white/10 text-[#9CC4FF]">
                    <feature.icon className="h-[18px] w-[18px]" strokeWidth={1.7} />
                  </span>
                  <h3 className="mt-4 text-[14px] font-bold text-white">{feature.title}</h3>
                  <p className="mt-2 text-[12px] leading-relaxed text-white/50">{feature.body}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="trust" className="mx-auto grid max-w-[1240px] items-center gap-12 px-5 py-20 lg:grid-cols-2 lg:px-8">
          <div className="relative order-2 lg:order-1">
            <div className="card overflow-hidden bg-gradient-to-br from-white via-white to-brand-soft/40 p-4">
              <img
                src="/illustrations/Certification-bro.svg"
                alt="Illustration of a signed certificate being verified"
                className="h-[320px] w-full object-contain"
                loading="lazy"
              />
            </div>
            <div className="absolute -bottom-4 left-6 right-6 rounded-2xl border border-line bg-white/95 px-4 py-3 shadow-[var(--shadow-soft)] backdrop-blur">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2 text-[11px] font-semibold text-ink-soft">
                  <Lock className="h-3.5 w-3.5 text-mint" /> No name, DOB or APAAR in the QR
                </div>
                <span className="chip bg-mint-soft text-mint">Ed25519</span>
              </div>
            </div>
          </div>
          <div className="order-1 lg:order-2">
            <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-brand">Trust layer</p>
            <h2 className="serif mt-3 text-[36px] leading-tight text-ink sm:text-[44px]">
              A certificate that fails loudly when it should
            </h2>
            <p className="mt-4 text-sm leading-relaxed text-ink-soft">
              Issue a signed record for a verified enrolment. Revoke it and the public verify page
              flips to REVOKED immediately. Change one claim in storage and it reads TAMPERED.
            </p>
            <div className="mt-7 space-y-3">
              {[
                ["Public verification", "Anyone with the ID can check signature and revocation — with no personal data revealed."],
                ["Consent before disclosure", "Verifiers cannot browse students. A purpose-bound request must be approved and it expires."],
                ["Hash-chained audit", "Login, upload, finding action, consent and revocation all append to a verifiable chain."],
              ].map(([title, body], index) => (
                <div key={title} className="flex gap-3 rounded-2xl border border-line bg-white p-4">
                  <span className="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full bg-navy text-[10px] font-bold text-white">
                    {index + 1}
                  </span>
                  <div>
                    <p className="text-[13px] font-bold text-ink">{title}</p>
                    <p className="mt-1 text-[12px] leading-relaxed text-ink-soft">{body}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="border-y border-line bg-white">
          <div className="mx-auto max-w-[1240px] px-5 py-16 lg:px-8">
            <div className="grid gap-5 md:grid-cols-3">
              {AUDIENCES.map((audience) => (
                <article key={audience.tag} className="group rounded-3xl border border-line bg-paper p-6 transition hover:border-brand/25 hover:bg-white">
                  <div className="flex items-center justify-between">
                    <span className="chip bg-white text-ink-soft shadow-sm">{audience.tag}</span>
                    <audience.icon className="h-5 w-5 text-brand/50" strokeWidth={1.6} />
                  </div>
                  <h3 className="mt-5 text-[17px] font-bold text-ink">{audience.title}</h3>
                  <p className="mt-2 text-[12.5px] leading-relaxed text-ink-soft">{audience.body}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="verify" className="mx-auto max-w-[1240px] px-5 py-20 lg:px-8">
          <div className="relative overflow-hidden rounded-[2.5rem] border border-line bg-gradient-to-br from-navy via-navy to-[#143a63] p-8 sm:p-12">
            <div className="pointer-events-none absolute inset-0 grid-lines opacity-10" />
            <div className="pointer-events-none absolute -right-10 -top-10 h-60 w-60 rounded-full bg-brand/25 blur-3xl" />
            <div className="relative grid items-center gap-8 lg:grid-cols-[1.1fr_0.9fr]">
              <div>
                <SimulatedBadge />
                <h2 className="serif mt-4 text-[32px] leading-tight text-white sm:text-[40px]">
                  Check a signed enrolment record
                </h2>
                <p className="mt-3 max-w-md text-[13px] leading-relaxed text-white/55">
                  Paste the credential reference from a QR code. The verifier checks the signature
                  and revocation status locally against the demo database.
                </p>
              </div>
              <form onSubmit={verify} className="rounded-3xl border border-white/15 bg-white/[0.06] p-4 backdrop-blur">
                <label className="mb-2 block text-[10px] font-bold uppercase tracking-[0.16em] text-white/45">
                  Credential reference
                </label>
                <div className="flex flex-col gap-2 sm:flex-row">
                  <input
                    value={credential}
                    onChange={(event) => setCredential(event.target.value)}
                    placeholder="cred_xxxxxxxxxxxxxxxx"
                    className="w-full rounded-2xl border border-white/15 bg-white/10 px-4 py-3 text-sm text-white outline-none placeholder:text-white/30 focus:border-[#9CC4FF]"
                  />
                  <button className="btn bg-white text-navy hover:bg-white/90" type="submit">
                    Verify
                    <ArrowRight className="h-4 w-4" />
                  </button>
                </div>
                <p className="mt-3 text-[10.5px] leading-relaxed text-white/35">
                  Credentials are VC-style signed records. This is not a W3C-conformance claim and
                  not an official APAAR certificate.
                </p>
              </form>
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-line bg-white">
        <div className="mx-auto grid max-w-[1240px] gap-8 px-5 py-12 lg:grid-cols-[1.2fr_1fr_1fr_1fr] lg:px-8">
          <div>
            <Logo />
            <p className="mt-4 max-w-xs text-[12px] leading-relaxed text-ink-soft">
              A prototype built on synthetic data. No connection to real APAAR, AICTE, DigiLocker,
              NAD or ABC systems. Every identity check is a labelled mock.
            </p>
          </div>
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-ink">Platform</p>
            <ul className="mt-3 space-y-2 text-[12px] text-ink-soft">
              <li><a className="hover:text-ink" href="#workflow">Workflow</a></li>
              <li><a className="hover:text-ink" href="#platform">Capabilities</a></li>
              <li><Link className="hover:text-ink" to="/login">College console</Link></li>
              <li><Link className="hover:text-ink" to="/login">AICTE console</Link></li>
            </ul>
          </div>
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-ink">Trust</p>
            <ul className="mt-3 space-y-2 text-[12px] text-ink-soft">
              <li><a className="hover:text-ink" href="#trust">Signed certificates</a></li>
              <li><a className="hover:text-ink" href="#trust">Consent flow</a></li>
              <li><a className="hover:text-ink" href="#trust">Audit chain</a></li>
              <li><Link className="hover:text-ink" to="/login">Sign in</Link></li>
            </ul>
          </div>
          <div>
            <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-ink">Disclaimer</p>
            <p className="mt-3 text-[11.5px] leading-relaxed text-ink-soft">
              Not affiliated with AICTE or the Government of India. All institutions, students and
              identifiers are fictional.
            </p>
          </div>
        </div>
        <div className="border-t border-line">
          <div className="mx-auto flex max-w-[1240px] flex-wrap items-center justify-between gap-3 px-5 py-5 text-[10.5px] text-ink-soft lg:px-8">
            <span>APAAR-Setu · Institutional Integrity Platform</span>
            <span className="inline-flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-amber" />
              SIMULATED — NOT OFFICIAL APAAR VERIFICATION
            </span>
          </div>
        </div>
      </footer>
    </div>
  );
}
