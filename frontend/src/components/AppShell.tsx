import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import clsx from "clsx";
import {
  ArrowLeftRight,
  Building2,
  ClipboardCheck,
  FileSearch,
  Fingerprint,
  Gauge,
  KeyRound,
  LogOut,
  Menu,
  ScrollText,
  ShieldCheck,
  UploadCloud,
  Users,
  X,
} from "lucide-react";
import { useAuth } from "../lib/auth";
import type { Role } from "../lib/types";
import { titleCase } from "../lib/format";
import { Logo, SimulatedBadge } from "./ui";

interface NavItem {
  to: string;
  label: string;
  icon: typeof Gauge;
  roles: Role[];
  end?: boolean;
}

const NAV: { group: string; items: NavItem[] }[] = [
  {
    group: "Workspace",
    items: [
      {
        to: "/app",
        label: "Overview",
        icon: Gauge,
        roles: ["institution_operator", "institution_admin", "central_reviewer", "sysadmin"],
        end: true,
      },
      {
        to: "/app/upload",
        label: "Upload data",
        icon: UploadCloud,
        roles: ["institution_operator", "institution_admin"],
      },
      {
        to: "/app/enrolments",
        label: "Enrolments",
        icon: Users,
        roles: ["institution_operator", "institution_admin", "central_reviewer", "sysadmin"],
      },
      {
        to: "/app/findings",
        label: "Findings",
        icon: FileSearch,
        roles: ["institution_operator", "institution_admin", "central_reviewer", "sysadmin"],
      },
      {
        to: "/app/duplicates",
        label: "Duplicates",
        icon: ArrowLeftRight,
        roles: ["institution_operator", "institution_admin", "central_reviewer", "sysadmin"],
      },
      {
        to: "/app/anomalies",
        label: "Anomaly queue",
        icon: Fingerprint,
        roles: ["central_reviewer", "sysadmin"],
      },
      {
        to: "/app/institutions",
        label: "Institutions",
        icon: Building2,
        roles: ["central_reviewer", "sysadmin"],
      },
    ],
  },
  {
    group: "Trust layer",
    items: [
      {
        to: "/app/credentials",
        label: "Certificates",
        icon: KeyRound,
        roles: ["institution_admin", "institution_operator", "central_reviewer"],
      },
      {
        to: "/app/consent",
        label: "Consent",
        icon: ClipboardCheck,
        roles: ["verifier", "student"],
      },
      {
        to: "/app/audit",
        label: "Audit trail",
        icon: ScrollText,
        roles: ["institution_admin", "central_reviewer", "sysadmin"],
      },
    ],
  },
];

const ROLE_LABEL: Record<Role, string> = {
  institution_operator: "College operator",
  institution_admin: "College administrator",
  central_reviewer: "AICTE reviewer",
  verifier: "Verifier",
  student: "Student",
  sysadmin: "Policy administrator",
};

export default function AppShell() {
  const { me, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  if (!me) return null;
  const role = me.user.role;
  const groups = NAV.map((group) => ({
    ...group,
    items: group.items.filter((item) => item.roles.includes(role)),
  })).filter((group) => group.items.length > 0);

  const nav = (
    <nav className="flex flex-1 flex-col gap-6 overflow-y-auto px-3 py-5">
      {groups.map((group) => (
        <div key={group.group}>
          <p className="px-3 pb-2 text-[9.5px] font-bold uppercase tracking-[0.22em] text-white/30">
            {group.group}
          </p>
          <div className="space-y-0.5">
            {group.items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                onClick={() => setMobileOpen(false)}
                className={({ isActive }) =>
                  clsx(
                    "group flex items-center gap-3 rounded-xl px-3 py-2.5 text-[13px] font-medium transition",
                    isActive
                      ? "bg-white/[0.11] text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]"
                      : "text-white/55 hover:bg-white/[0.06] hover:text-white/90",
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    <item.icon
                      className={clsx("h-[17px] w-[17px]", isActive ? "text-[#9CC4FF]" : "text-white/40 group-hover:text-white/70")}
                      strokeWidth={1.8}
                    />
                    {item.label}
                  </>
                )}
              </NavLink>
            ))}
          </div>
        </div>
      ))}
      <div className="mt-auto rounded-2xl border border-white/10 bg-white/[0.05] p-3.5">
        <div className="flex items-center gap-2 text-[11px] font-semibold text-white/80">
          <ShieldCheck className="h-3.5 w-3.5 text-[#9CD3B0]" />
          Humans decide
        </div>
        <p className="mt-1.5 text-[10.5px] leading-relaxed text-white/40">
          Flags prioritise review. Nothing here automatically penalises a college or a student.
        </p>
      </div>
    </nav>
  );

  const sidebarBrand = (
    <div className="flex items-center justify-between px-5 pt-6 pb-4">
      <Logo light />
      <button className="lg:hidden" onClick={() => setMobileOpen(false)} aria-label="Close menu">
        <X className="h-5 w-5 text-white/60" />
      </button>
    </div>
  );

  return (
    <div className="min-h-screen bg-paper">
      <div className="ribbon fixed inset-x-0 top-0 z-[60] flex h-6 items-center justify-center px-4">
        <p className="truncate text-[9px] font-bold uppercase tracking-[0.22em] text-white/75">
          SIMULATED — NOT OFFICIAL APAAR VERIFICATION · synthetic demo data only
        </p>
      </div>

      <aside className="fixed bottom-0 left-0 top-6 z-40 hidden w-[248px] flex-col border-r border-white/5 bg-navy-deep lg:flex">
        <div className="pointer-events-none absolute inset-0 grid-lines opacity-[0.18]" />
        <div className="relative flex h-full flex-col">
          {sidebarBrand}
          {nav}
          <div className="border-t border-white/10 px-5 py-4">
            <div className="flex items-center gap-2.5">
              <span className="grid h-8 w-8 place-items-center rounded-full bg-white/10 text-[11px] font-bold text-white">
                {me.user.name.slice(0, 1)}
              </span>
              <div className="min-w-0">
                <p className="truncate text-[11.5px] font-semibold text-white/90">{me.user.name}</p>
                <p className="truncate text-[10px] text-white/40">{ROLE_LABEL[role]}</p>
              </div>
            </div>
          </div>
        </div>
      </aside>

      {mobileOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <div className="absolute inset-0 bg-navy-deep/60 backdrop-blur-sm" onClick={() => setMobileOpen(false)} />
          <aside className="fixed bottom-0 left-0 top-6 flex w-[280px] flex-col bg-navy-deep">
            <div className="pointer-events-none absolute inset-0 grid-lines opacity-[0.18]" />
            <div className="relative flex h-full flex-col">
              {sidebarBrand}
              {nav}
            </div>
          </aside>
        </div>
      )}

      <div className="pt-6 lg:pl-[248px]">
        <header className="sticky top-6 z-30 border-b border-line/80 bg-paper/85 backdrop-blur-xl">
          <div className="flex h-14 items-center justify-between gap-3 px-4 sm:px-6 lg:px-8">
            <div className="flex min-w-0 items-center gap-3">
              <button
                className="grid h-9 w-9 place-items-center rounded-xl border border-line bg-white text-ink lg:hidden"
                onClick={() => setMobileOpen(true)}
                aria-label="Open menu"
              >
                <Menu className="h-4 w-4" />
              </button>
              <div className="hidden min-w-0 sm:block">
                <p className="truncate text-[12px] font-bold text-ink">
                  {me.user.institution ? me.user.institution.name : "All India · AICTE review"}
                </p>
                <p className="truncate text-[10.5px] text-ink-soft">
                  {me.user.institution
                    ? `${me.user.institution.code} · ${me.user.institution.state}`
                    : "Central dashboard · 12 fictional institutions"}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <SimulatedBadge subtle />
              <span className="hidden rounded-full border border-line bg-white px-3 py-1.5 text-[10.5px] font-semibold text-ink-soft sm:inline-flex">
                {titleCase(role)}
              </span>
              <button
                onClick={async () => {
                  await logout();
                  navigate("/login");
                }}
                className="btn-quiet h-9 !px-2.5 text-xs"
                title="Sign out"
              >
                <LogOut className="h-4 w-4" />
                <span className="hidden sm:inline">Sign out</span>
              </button>
            </div>
          </div>
        </header>
        <main className="mx-auto w-full max-w-[1320px] px-4 py-7 sm:px-6 lg:px-8 lg:py-9">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
