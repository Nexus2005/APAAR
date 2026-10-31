import { useEffect, type ReactNode } from "react";
import clsx from "clsx";
import { ArrowUpRight, X } from "lucide-react";

export function Logo({ light = false, compact = false }: { light?: boolean; compact?: boolean }) {
  return (
    <div className="flex items-center gap-2.5">
      <span className="relative grid h-9 w-9 place-items-center rounded-[13px] bg-gradient-to-br from-brand to-navy-deep shadow-[0_8px_20px_-8px_rgba(47,111,237,0.9)]">
        <svg viewBox="0 0 32 32" className="h-5 w-5" aria-hidden="true">
          <path
            d="M6 21V12l10-5 10 5v9"
            fill="none"
            stroke="white"
            strokeWidth="2.4"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          <path
            d="M12 21v-6h8v6"
            fill="none"
            stroke="#9CD3B0"
            strokeWidth="2.4"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </span>
      {!compact && (
        <span className="leading-none">
          <span className={clsx("block text-[17px] font-extrabold tracking-tight", light ? "text-white" : "text-ink")}>
            APAAR<span className="text-brand">·</span>Setu
          </span>
          <span className={clsx("mt-1 block text-[9px] font-semibold uppercase tracking-[0.24em]", light ? "text-white/50" : "text-ink-soft/70")}>
            Enrolment integrity
          </span>
        </span>
      )}
    </div>
  );
}

export function SimulatedBadge({ subtle = false }: { subtle?: boolean }) {
  return (
    <span
      className={clsx(
        "chip border",
        subtle
          ? "border-amber/25 bg-amber-soft text-amber"
          : "border-white/15 bg-white/10 text-white/80 backdrop-blur",
      )}
      title="This prototype uses synthetic data and mock government adapters only."
    >
      <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-amber">
        <span className="pulse-dot absolute inset-0 rounded-full bg-amber" />
      </span>
      SIMULATED
    </span>
  );
}

const badgeStyles: Record<string, string> = {
  green: "bg-mint-soft text-mint",
  mint: "bg-mint-soft text-mint",
  amber: "bg-amber-soft text-amber",
  red: "bg-rose-soft text-rose",
  rose: "bg-rose-soft text-rose",
  blue: "bg-brand-soft text-brand-dark",
  slate: "bg-black/5 text-ink-soft",
  navy: "bg-navy/10 text-navy",
  violet: "bg-violet-50 text-violet-700",
};

export function Badge({
  children,
  tone = "slate",
  className,
}: {
  children: ReactNode;
  tone?: keyof typeof badgeStyles | string;
  className?: string;
}) {
  return (
    <span className={clsx("chip", badgeStyles[tone] ?? badgeStyles.slate, className)}>{children}</span>
  );
}

export function SeverityBadge({ severity }: { severity: string }) {
  const map: Record<string, { tone: string; label: string }> = {
    blocker: { tone: "red", label: "Blocker" },
    risk: { tone: "amber", label: "Risk" },
    warning: { tone: "blue", label: "Warning" },
    info: { tone: "slate", label: "Info" },
  };
  const item = map[severity] ?? map.info;
  return <Badge tone={item.tone}>{item.label}</Badge>;
}

export function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { tone: string; label: string }> = {
    open: { tone: "amber", label: "Open" },
    in_review: { tone: "blue", label: "In review" },
    resolved: { tone: "green", label: "Resolved" },
    dismissed: { tone: "slate", label: "Dismissed" },
    escalated: { tone: "red", label: "Escalated" },
    pending: { tone: "amber", label: "Pending" },
    approved: { tone: "green", label: "Approved" },
    denied: { tone: "rose", label: "Denied" },
    expired: { tone: "slate", label: "Expired" },
    valid: { tone: "green", label: "Valid" },
    revoked: { tone: "rose", label: "Revoked" },
    admitted: { tone: "blue", label: "Admitted" },
    verified: { tone: "green", label: "Verified" },
    completed: { tone: "green", label: "Completed" },
  };
  const item = map[status] ?? { tone: "slate", label: status };
  return <Badge tone={item.tone}>{item.label}</Badge>;
}

export function Card({
  children,
  className,
  as: Tag = "section",
}: {
  children: ReactNode;
  className?: string;
  as?: "section" | "div" | "article";
}) {
  return <Tag className={clsx("card", className)}>{children}</Tag>;
}

export function SectionCard({
  title,
  description,
  action,
  children,
  className,
  bodyClassName,
}: {
  title: string;
  description?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
}) {
  return (
    <Card className={clsx("overflow-hidden", className)}>
      <div className="flex flex-wrap items-start justify-between gap-3 px-5 pt-5 pb-4 sm:px-6">
        <div>
          <h2 className="text-[15px] font-bold tracking-tight text-ink">{title}</h2>
          {description && <p className="mt-1 text-xs leading-relaxed text-ink-soft">{description}</p>}
        </div>
        {action}
      </div>
      <div className={bodyClassName}>{children}</div>
    </Card>
  );
}

export function StatCard({
  label,
  value,
  sub,
  icon,
  tone = "blue",
  className,
}: {
  label: string;
  value: ReactNode;
  sub?: ReactNode;
  icon?: ReactNode;
  tone?: "blue" | "green" | "amber" | "rose" | "navy";
  className?: string;
}) {
  const tones = {
    blue: "bg-brand-soft text-brand-dark",
    green: "bg-mint-soft text-mint",
    amber: "bg-amber-soft text-amber",
    rose: "bg-rose-soft text-rose",
    navy: "bg-navy/10 text-navy",
  };
  return (
    <Card className={clsx("relative overflow-hidden p-5", className)}>
      <div className="flex items-start justify-between gap-3">
        <p className="text-[11px] font-bold uppercase tracking-[0.14em] text-ink-soft">{label}</p>
        {icon && <span className={clsx("grid h-9 w-9 place-items-center rounded-2xl", tones[tone])}>{icon}</span>}
      </div>
      <p className="mt-3 text-[28px] leading-none font-extrabold tracking-tight text-ink">{value}</p>
      {sub && <div className="mt-2 text-xs text-ink-soft">{sub}</div>}
    </Card>
  );
}

export function ProgressBar({
  value,
  tone = "blue",
  className,
  height = "h-2",
}: {
  value: number;
  tone?: "blue" | "green" | "amber" | "rose" | "navy";
  className?: string;
  height?: string;
}) {
  const colors = {
    blue: "bg-brand",
    green: "bg-mint",
    amber: "bg-amber",
    rose: "bg-rose",
    navy: "bg-navy",
  };
  return (
    <div className={clsx("w-full overflow-hidden rounded-full bg-black/[0.06]", height, className)}>
      <div
        className={clsx("h-full rounded-full transition-all duration-700", colors[tone])}
        style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
      />
    </div>
  );
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-4">
      <div className="max-w-2xl">
        {eyebrow && (
          <p className="mb-2 text-[11px] font-bold uppercase tracking-[0.18em] text-brand">{eyebrow}</p>
        )}
        <h1 className="serif text-[30px] leading-[1.1] font-normal text-ink sm:text-[36px]">{title}</h1>
        {description && <p className="mt-2 max-w-xl text-sm leading-relaxed text-ink-soft">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </div>
  );
}

export function EmptyState({
  illustration,
  title,
  description,
  action,
  compact = false,
}: {
  illustration?: string;
  title: string;
  description?: string;
  action?: ReactNode;
  compact?: boolean;
}) {
  return (
    <div className={clsx("flex flex-col items-center justify-center px-6 text-center", compact ? "py-8" : "py-14")}>
      {illustration ? (
        <img src={illustration} alt="" className={clsx("mb-4 opacity-90", compact ? "h-24" : "h-40")} loading="lazy" />
      ) : (
        <div className="mb-4 grid h-14 w-14 place-items-center rounded-2xl bg-brand-soft text-brand">
          <ArrowUpRight className="h-6 w-6" />
        </div>
      )}
      <h3 className="text-sm font-bold text-ink">{title}</h3>
      {description && <p className="mt-1.5 max-w-sm text-xs leading-relaxed text-ink-soft">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function Alert({
  tone = "amber",
  title,
  children,
  action,
}: {
  tone?: "amber" | "blue" | "green" | "rose";
  title?: string;
  children: ReactNode;
  action?: ReactNode;
}) {
  const map = {
    amber: "border-amber/20 bg-amber-soft/70 text-amber",
    blue: "border-brand/15 bg-brand-soft/70 text-brand-dark",
    green: "border-mint/20 bg-mint-soft/70 text-mint",
    rose: "border-rose/20 bg-rose-soft/70 text-rose",
  };
  return (
    <div className={clsx("flex flex-wrap items-start justify-between gap-3 rounded-2xl border px-4 py-3 text-xs leading-relaxed", map[tone])}>
      <div>
        {title && <p className="mb-0.5 text-[12px] font-bold">{title}</p>}
        <div className="opacity-90">{children}</div>
      </div>
      {action}
    </div>
  );
}

export function Modal({
  open,
  onClose,
  title,
  description,
  children,
  wide = false,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: string;
  children: ReactNode;
  wide?: boolean;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = "";
    };
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-navy-deep/50 p-0 backdrop-blur-sm sm:items-center sm:p-6">
      <div
        className={clsx(
          "max-h-[92vh] w-full overflow-y-auto rounded-t-3xl bg-white shadow-[var(--shadow-lift)] sm:rounded-3xl",
          wide ? "sm:max-w-3xl" : "sm:max-w-lg",
        )}
        role="dialog"
        aria-modal="true"
      >
        <div className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-line bg-white/95 px-5 py-4 backdrop-blur sm:px-6">
          <div>
            <h2 className="text-[16px] font-bold text-ink">{title}</h2>
            {description && <p className="mt-1 text-xs text-ink-soft">{description}</p>}
          </div>
          <button className="btn-quiet h-9 w-9 shrink-0 !px-0" onClick={onClose} aria-label="Close">
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="px-5 py-5 sm:px-6">{children}</div>
      </div>
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={clsx("animate-pulse rounded-2xl bg-black/[0.06]", className)} />;
}

export function Tabs({
  tabs,
  active,
  onChange,
}: {
  tabs: { key: string; label: string; count?: number }[];
  active: string;
  onChange: (key: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-1 rounded-full border border-line bg-white p-1">
      {tabs.map((tab) => (
        <button
          key={tab.key}
          onClick={() => onChange(tab.key)}
          className={clsx(
            "rounded-full px-3.5 py-1.5 text-xs font-semibold transition",
            active === tab.key ? "bg-navy text-white" : "text-ink-soft hover:bg-black/5 hover:text-ink",
          )}
        >
          {tab.label}
          {tab.count !== undefined && (
            <span className={clsx("ml-1.5", active === tab.key ? "text-white/60" : "text-ink-soft/50")}>
              {tab.count}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}
