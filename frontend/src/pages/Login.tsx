import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { ArrowLeft, ArrowRight, Eye, EyeOff, Loader2, Lock, Search, ShieldCheck } from "lucide-react";
import { useAuth } from "../lib/auth";
import { ApiError } from "../lib/api";
import { Logo, SimulatedBadge } from "../components/ui";

const DEMO = [
  { email: "admin.syn-mh-001@demo.apaar-setu.invalid", label: "College admin", detail: "Sahyadri Institute of Technology", tone: "School" },
  { email: "operator.syn-mh-002@demo.apaar-setu.invalid", label: "College operator", detail: "Deccan College of Engineering", tone: "Operator" },
  { email: "reviewer@aicte.demo.apaar-setu.invalid", label: "AICTE reviewer", detail: "Central dashboard and review queue", tone: "Central" },
  { email: "verifier@bank.demo.apaar-setu.invalid", label: "Verifier", detail: "Request consent-bound facts", tone: "Verifier" },
  { email: "student@demo.apaar-setu.invalid", label: "Student", detail: "Approve or deny consent requests", tone: "Student" },
  { email: "sysadmin@demo.apaar-setu.invalid", label: "Policy admin", detail: "Rule versions and audit chain", tone: "Policy" },
];

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login } = useAuth();
  const [email, setEmail] = useState(DEMO[0].email);
  const [password, setPassword] = useState("demo1234");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState("");

  const next = (location.state as { from?: string } | null)?.from || "/app";

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await login(email.trim(), password);
      navigate(next, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not sign in. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }

  const filtered = DEMO.filter(
    (account) =>
      account.label.toLowerCase().includes(filter.toLowerCase()) ||
      account.detail.toLowerCase().includes(filter.toLowerCase()),
  );

  return (
    <div className="min-h-screen bg-paper lg:grid lg:grid-cols-[1.05fr_0.95fr]">
      <div className="ribbon flex h-6 items-center justify-center px-4">
        <p className="truncate text-[9px] font-bold uppercase tracking-[0.24em] text-white/75">
          SIMULATED — NOT OFFICIAL APAAR VERIFICATION
        </p>
      </div>

      <aside className="relative hidden overflow-hidden bg-navy-deep lg:col-start-1 lg:row-span-2 lg:row-start-1 lg:flex lg:flex-col lg:justify-between">
        <div className="pointer-events-none absolute inset-0 grid-lines opacity-[0.15]" />
        <div className="pointer-events-none absolute -right-20 top-10 h-80 w-80 rounded-full bg-brand/25 blur-[90px]" />
        <div className="pointer-events-none absolute -left-16 bottom-0 h-72 w-72 rounded-full bg-mint/15 blur-[90px]" />
        <div className="relative p-10">
          <Link to="/">
            <Logo light />
          </Link>
          <div className="mt-16 max-w-md">
            <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-[#9CC4FF]">Colleges · AICTE · Verifiers · Students</p>
            <h1 className="serif mt-3 text-[42px] leading-[1.02] text-white">
              One workspace for
              <br />
              the evidence behind
              <br />
              <span className="italic text-[#9CD3B0]">every enrolment.</span>
            </h1>
            <p className="mt-5 max-w-sm text-[13px] leading-relaxed text-white/50">
              The demo database is already seeded with 12 fictional institutions, 32 programmes and
              1,652 messy admission rows. Pick a role and look around.
            </p>
          </div>
          <div className="relative mt-10 max-w-md rounded-3xl border border-white/10 bg-white/[0.05] p-4 backdrop-blur">
            <img
              src="/illustrations/college admission-rafiki.svg"
              alt="Illustration of an admission review"
              className="h-56 w-full object-contain"
            />
          </div>
        </div>
        <div className="relative border-t border-white/10 px-10 py-6">
          <div className="flex flex-wrap items-center gap-x-6 gap-y-2 text-[10.5px] font-medium text-white/40">
            <span className="inline-flex items-center gap-1.5"><ShieldCheck className="h-3.5 w-3.5 text-mint" /> Humans decide</span>
            <span className="inline-flex items-center gap-1.5"><Lock className="h-3.5 w-3.5 text-mint" /> Privacy by construction</span>
            <span className="inline-flex items-center gap-1.5"><Search className="h-3.5 w-3.5 text-mint" /> Every action audited</span>
          </div>
        </div>
      </aside>

      <main className="flex min-h-[calc(100vh-24px)] flex-col justify-center px-5 py-10 sm:px-10 lg:col-start-2 lg:row-span-2 lg:row-start-1">
        <div className="mx-auto w-full max-w-[420px]">
          <div className="mb-8 flex items-center justify-between lg:hidden">
            <Link to="/"><Logo /></Link>
            <SimulatedBadge subtle />
          </div>
          <Link to="/" className="btn-quiet mb-6 !px-2 text-xs">
            <ArrowLeft className="h-3.5 w-3.5" /> Back to overview
          </Link>
          <p className="text-[10.5px] font-bold uppercase tracking-[0.18em] text-brand">Demo sign-in</p>
          <h2 className="serif mt-2 text-[36px] leading-none text-ink">Welcome back</h2>
          <p className="mt-3 text-[13px] text-ink-soft">
            Choose a demo role below. The password for every demo account is <code className="rounded bg-black/5 px-1.5 py-0.5 text-[11px] font-semibold">demo1234</code>.
          </p>

          <form onSubmit={submit} className="mt-7 space-y-4">
            <div>
              <label className="label" htmlFor="email">Email</label>
              <input
                id="email"
                type="email"
                required
                className="input"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                autoComplete="username"
              />
            </div>
            <div>
              <label className="label" htmlFor="password">Password</label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? "text" : "password"}
                  required
                  className="input pr-12"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((value) => !value)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-soft hover:text-ink"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>
            {error && (
              <div className="rounded-2xl border border-rose/20 bg-rose-soft px-4 py-3 text-xs text-rose">
                {error}
              </div>
            )}
            <button type="submit" disabled={loading} className="btn-primary w-full !py-3">
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Lock className="h-4 w-4" />}
              {loading ? "Signing in…" : "Open workspace"}
              {!loading && <ArrowRight className="ml-auto h-4 w-4" />}
            </button>
          </form>

          <div className="mt-8">
            <div className="mb-3 flex items-center justify-between gap-3">
              <p className="text-[10.5px] font-bold uppercase tracking-[0.16em] text-ink-soft">Or jump in as</p>
              <input
                value={filter}
                onChange={(event) => setFilter(event.target.value)}
                placeholder="Filter roles"
                className="w-28 rounded-full border border-line bg-white px-3 py-1 text-[11px] outline-none focus:border-brand"
              />
            </div>
            <div className="grid gap-1.5">
              {filtered.map((account) => (
                <button
                  key={account.email}
                  type="button"
                  onClick={() => {
                    setEmail(account.email);
                    setPassword("demo1234");
                    setError(null);
                  }}
                  className={`flex items-center gap-3 rounded-2xl border px-3.5 py-2.5 text-left transition ${
                    email === account.email
                      ? "border-brand/40 bg-brand-soft/60"
                      : "border-line bg-white hover:border-brand/25 hover:bg-brand-soft/20"
                  }`}
                >
                  <span className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-navy text-[10px] font-bold text-white">
                    {account.label.slice(0, 1)}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-[12px] font-bold text-ink">{account.label}</span>
                    <span className="block truncate text-[10.5px] text-ink-soft">{account.detail}</span>
                  </span>
                  <ArrowRight className="h-3.5 w-3.5 shrink-0 text-ink-soft/50" />
                </button>
              ))}
            </div>
          </div>
          <p className="mt-6 text-center text-[10px] leading-relaxed text-ink-soft/70">
            Fictional data only. No real APAAR, AICTE, DigiLocker, NAD or ABC connection exists.
          </p>
        </div>
      </main>
    </div>
  );
}
