import { useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import clsx from "clsx";
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  Check,
  CheckCircle2,
  Download,
  FileSpreadsheet,
  Loader2,
  Sparkles,
  UploadCloud,
  X,
} from "lucide-react";
import { api, apiBlob, downloadBlob } from "../lib/api";
import { num, pct } from "../lib/format";
import type { UploadBatch } from "../lib/types";
import { Alert, Badge, Card, PageHeader, ProgressBar, SectionCard } from "../components/ui";

interface PreviewField {
  key: string;
  label: string;
  required: boolean;
}

interface PreviewResponse {
  filename: string;
  headers: string[];
  row_count: number;
  suggested_mapping: Record<string, { source_column: string | null; confidence: number }>;
  unmapped_columns: string[];
  fields: PreviewField[];
  sample_rows: string[][];
}

interface UploadRow {
  row_number: number;
  status: string;
  codes: string[];
  errors: { code: string; fields?: string[]; message: string }[];
  row: Record<string, string>;
}

interface UploadDetail {
  batch: UploadBatch;
  rows: UploadRow[];
}

const STEPS = ["Choose file", "Confirm mapping", "Results"];

export default function UploadWizard() {
  const [step, setStep] = useState(0);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [batchId, setBatchId] = useState<number | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const previewMutation = useMutation({
    mutationFn: async (upload: File) => {
      const form = new FormData();
      form.append("file", upload);
      return api<PreviewResponse>("/uploads/preview", { method: "POST", body: form });
    },
    onSuccess: (data) => {
      setPreview(data);
      const initial: Record<string, string> = {};
      for (const field of data.fields) {
        initial[field.key] = data.suggested_mapping[field.key]?.source_column ?? "";
      }
      setMapping(initial);
      setStep(1);
      setLocalError(null);
    },
    onError: (error: Error) => setLocalError(error.message),
  });

  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!file || !preview) throw new Error("Choose a file first.");
      const form = new FormData();
      form.append("file", file);
      const payload: Record<string, { source_column: string; confidence: number }> = {};
      for (const [key, column] of Object.entries(mapping)) {
        if (column) {
          const confidence = preview.suggested_mapping[key]?.source_column === column
            ? preview.suggested_mapping[key]?.confidence ?? 0.5
            : 1;
          payload[key] = { source_column: column, confidence };
        }
      }
      form.append("mapping", JSON.stringify(payload));
      return api<{ batch: UploadBatch; duplicate_upload: boolean }>("/uploads", { method: "POST", body: form });
    },
    onSuccess: (data) => {
      setBatchId(data.batch.id);
      setStep(2);
      queryClient.invalidateQueries({ queryKey: ["institution-dashboard"] });
      queryClient.invalidateQueries({ queryKey: ["findings"] });
    },
    onError: (error: Error) => setLocalError(error.message),
  });

  const detailQuery = useQuery({
    queryKey: ["upload", batchId],
    queryFn: () => api<UploadDetail>(`/uploads/${batchId}`),
    enabled: batchId !== null && step === 2,
  });

  function acceptFile(candidate: File | undefined | null) {
    if (!candidate) return;
    const extension = candidate.name.split(".").pop()?.toLowerCase();
    if (!["csv", "xlsx"].includes(extension ?? "")) {
      setLocalError("Use a .csv or .xlsx file.");
      return;
    }
    if (candidate.size > 5 * 1024 * 1024) {
      setLocalError("The file is larger than the 5 MB limit.");
      return;
    }
    setFile(candidate);
    setLocalError(null);
    setPreview(null);
    setBatchId(null);
    previewMutation.mutate(candidate);
  }

  function reset() {
    setStep(0);
    setFile(null);
    setPreview(null);
    setMapping({});
    setBatchId(null);
    setLocalError(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  async function errorCsv() {
    if (!batchId) return;
    const blob = await apiBlob(`/uploads/${batchId}/errors.csv`);
    downloadBlob(blob, `upload-${batchId}-errors.csv`);
  }

  const missingRequired = preview
    ? preview.fields.filter((field) => field.required && !mapping[field.key])
    : [];

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Ingestion"
        title="Bring in an admission file."
        description="Column mapping is suggested, then confirmed by you. A rejected row never fails the whole batch."
        actions={<Badge tone="slate">CSV · XLSX · max 5 MB</Badge>}
      />

      <ol className="flex flex-wrap items-center gap-2 text-[11px] font-semibold">
        {STEPS.map((label, index) => (
          <li key={label} className="flex items-center gap-2">
            <span
              className={clsx(
                "grid h-6 w-6 place-items-center rounded-full text-[10px]",
                index < step ? "bg-mint text-white" : index === step ? "bg-brand text-white" : "bg-black/5 text-ink-soft",
              )}
            >
              {index < step ? <Check className="h-3 w-3" /> : index + 1}
            </span>
            <span className={index === step ? "text-ink" : "text-ink-soft"}>{label}</span>
            {index < STEPS.length - 1 && <span className="mx-1 h-px w-8 bg-line" />}
          </li>
        ))}
      </ol>

      {localError && (
        <Alert tone="rose" title="That did not work" action={<button onClick={() => setLocalError(null)}><X className="h-4 w-4" /></button>}>
          {localError}
        </Alert>
      )}

      {step === 0 && (
        <div className="grid gap-5 lg:grid-cols-[1.2fr_0.8fr]">
          <Card className="p-3">
            <div
              onDragOver={(event) => {
                event.preventDefault();
                setDragOver(true);
              }}
              onDragLeave={() => setDragOver(false)}
              onDrop={(event) => {
                event.preventDefault();
                setDragOver(false);
                acceptFile(event.dataTransfer.files?.[0]);
              }}
              className={clsx(
                "relative flex min-h-[420px] flex-col items-center justify-center overflow-hidden rounded-[1.6rem] border-2 border-dashed p-8 text-center transition",
                dragOver ? "border-brand bg-brand-soft/50" : "border-line bg-gradient-to-b from-white to-paper",
              )}
            >
              <img src="/illustrations/Online learning-rafiki.svg" alt="" className="mb-4 h-44 opacity-95" />
              <h2 className="text-[17px] font-bold text-ink">Drop an admission file here</h2>
              <p className="mt-1.5 max-w-sm text-[12px] leading-relaxed text-ink-soft">
                Different colleges use different headers. We suggest the mapping from an alias dictionary and fuzzy matching — you confirm it on the next step.
              </p>
              <button
                onClick={() => inputRef.current?.click()}
                className="btn-primary mt-5"
                disabled={previewMutation.isPending}
              >
                {previewMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <UploadCloud className="h-4 w-4" />}
                {previewMutation.isPending ? "Reading headers…" : "Choose a file"}
              </button>
              <input
                ref={inputRef}
                type="file"
                accept=".csv,.xlsx"
                className="hidden"
                onChange={(event) => acceptFile(event.target.files?.[0])}
              />
              <p className="mt-4 text-[10px] font-semibold uppercase tracking-[0.14em] text-ink-soft/50">
                Same file twice = same batch. No duplicates.
              </p>
            </div>
          </Card>

          <div className="space-y-4">
            <SectionCard title="Try the demo files" description="Seeded files live in data/synthetic with deliberately messy headers.">
              <div className="space-y-2 px-5 pb-5">
                {[
                  ["SYN-MH-001_admissions_2026-27.csv", "Messy headers · all problem types"],
                  ["SYN-KA-004_admissions_2026-27.xlsx", "Excel workbook · alternative headers"],
                  ["SYN-TN-008_admissions_2026-27.csv", "Last-week upload spike"],
                ].map(([name, note]) => (
                  <div key={name} className="rounded-2xl border border-line bg-paper/60 px-3.5 py-3">
                    <div className="flex items-center gap-2">
                      <FileSpreadsheet className="h-4 w-4 text-mint" />
                      <p className="truncate text-[11px] font-semibold text-ink">{name}</p>
                    </div>
                    <p className="mt-1 text-[10px] text-ink-soft">{note}</p>
                  </div>
                ))}
                <p className="text-[10px] leading-relaxed text-ink-soft/70">
                  These are on the server, not downloadable in the browser demo. Upload your own CSV with the same shape to see the wizard.
                </p>
              </div>
            </SectionCard>
            <Alert tone="blue" title="What happens to a row?">
              Required fields → date parsing → APAAR format → programme match. Malformed rows are rejected with codes; the batch still completes.
            </Alert>
          </div>
        </div>
      )}

      {step === 1 && preview && (
        <div className="space-y-5">
          <Card className="flex flex-wrap items-center justify-between gap-3 p-4">
            <div className="flex items-center gap-3">
              <span className="grid h-10 w-10 place-items-center rounded-2xl bg-brand-soft text-brand">
                <FileSpreadsheet className="h-5 w-5" />
              </span>
              <div>
                <p className="text-[13px] font-bold text-ink">{preview.filename}</p>
                <p className="text-[11px] text-ink-soft">{num(preview.row_count)} rows · {preview.headers.length} columns</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge tone={missingRequired.length ? "amber" : "green"}>
                {missingRequired.length ? `${missingRequired.length} required field(s) unmapped` : "Required fields mapped"}
              </Badge>
              <button onClick={reset} className="btn-quiet text-xs">Cancel</button>
            </div>
          </Card>

          <SectionCard
            title="Confirm the column mapping"
            description="Green means the alias dictionary or fuzzy matcher is confident. Change anything that looks wrong."
            bodyClassName="overflow-x-auto"
          >
            <table className="table-base min-w-[620px]">
              <thead>
                <tr>
                  <th>Canonical field</th>
                  <th>Your column</th>
                  <th>Confidence</th>
                </tr>
              </thead>
              <tbody>
                {preview.fields.map((field) => {
                  const confidence = preview.suggested_mapping[field.key]?.confidence ?? 0;
                  const active = mapping[field.key];
                  return (
                    <tr key={field.key}>
                      <td>
                        <div className="flex items-center gap-2">
                          <span className="text-[12px] font-semibold text-ink">{field.label}</span>
                          {field.required && <span className="text-rose">*</span>}
                        </div>
                        <p className="text-[10px] text-ink-soft">{field.key}</p>
                      </td>
                      <td className="w-[280px]">
                        <select
                          value={mapping[field.key] ?? ""}
                          onChange={(event) => setMapping((current) => ({ ...current, [field.key]: event.target.value }))}
                          className={clsx("input !py-2 text-xs", field.required && !active && "border-rose/50")}
                        >
                          <option value="">— not mapped —</option>
                          {preview.headers.map((header) => (
                            <option key={header} value={header}>{header}</option>
                          ))}
                        </select>
                      </td>
                      <td>
                        {active ? (
                          <div className="flex items-center gap-2">
                            <ProgressBar value={confidence * 100} tone={confidence > 0.85 ? "green" : confidence > 0.7 ? "amber" : "rose"} height="h-1.5" className="w-20" />
                            <span className="text-[10.5px] font-semibold text-ink-soft">{pct(confidence * 100)}</span>
                          </div>
                        ) : (
                          <span className="text-[10.5px] text-ink-soft">—</span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {preview.unmapped_columns.length > 0 && (
              <div className="flex flex-wrap items-center gap-2 border-t border-line px-5 py-3 text-[10.5px] text-ink-soft">
                <span className="font-semibold">Left unmapped:</span>
                {preview.unmapped_columns.map((column) => (
                  <span key={column} className="chip bg-black/[0.04] text-ink-soft">{column}</span>
                ))}
              </div>
            )}
          </SectionCard>

          <SectionCard title="Preview · first 10 rows" description="APAAR values are masked in previews and API responses." bodyClassName="overflow-x-auto">
            <table className="table-base min-w-[760px]">
              <thead>
                <tr>{preview.headers.map((header) => <th key={header}>{header}</th>)}</tr>
              </thead>
              <tbody>
                {preview.sample_rows.map((row, rowIndex) => (
                  <tr key={rowIndex}>
                    {preview.headers.map((header, columnIndex) => (
                      <td key={header} className="max-w-[180px] truncate text-[11px] text-ink-soft">{row[columnIndex]}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </SectionCard>

          <div className="flex flex-wrap items-center justify-between gap-3">
            <button onClick={reset} className="btn-ghost text-xs">
              <ArrowLeft className="h-4 w-4" /> Choose another file
            </button>
            <button
              onClick={() => uploadMutation.mutate()}
              disabled={uploadMutation.isPending || missingRequired.length > 0}
              className="btn-primary text-xs"
            >
              {uploadMutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
              {uploadMutation.isPending ? "Validating every row…" : "Process the file"}
            </button>
          </div>
        </div>
      )}

      {step === 2 && batchId && (
        <div className="space-y-5">
          {detailQuery.isLoading ? (
            <Card className="flex min-h-[300px] items-center justify-center p-8">
              <Loader2 className="h-6 w-6 animate-spin text-brand" />
            </Card>
          ) : detailQuery.data ? (
            <>
              <Card className="overflow-hidden">
                <div className="relative bg-gradient-to-br from-navy to-[#1b3b66] px-6 py-7 text-white">
                  <div className="pointer-events-none absolute inset-0 grid-lines opacity-10" />
                  <div className="relative flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <p className="text-[10px] font-bold uppercase tracking-[0.18em] text-[#9CC4FF]">Upload complete</p>
                      <h2 className="mt-1.5 text-[22px] font-bold">{detailQuery.data.batch.filename}</h2>
                      <p className="mt-1 text-[11.5px] text-white/50">{detailQuery.data.batch.ref} · {num(detailQuery.data.batch.total_rows)} rows read</p>
                    </div>
                    <div className="grid grid-cols-3 gap-3 text-center">
                      <div className="rounded-2xl bg-white/10 px-4 py-3">
                        <p className="text-[20px] font-extrabold">{num(detailQuery.data.batch.accepted_rows)}</p>
                        <p className="text-[9px] font-bold uppercase tracking-[0.12em] text-white/50">accepted</p>
                      </div>
                      <div className="rounded-2xl bg-white/10 px-4 py-3">
                        <p className="text-[20px] font-extrabold text-[#FFC9A3]">{num(detailQuery.data.batch.rejected_rows)}</p>
                        <p className="text-[9px] font-bold uppercase tracking-[0.12em] text-white/50">rejected</p>
                      </div>
                      <div className="rounded-2xl bg-white/10 px-4 py-3">
                        <p className="text-[20px] font-extrabold text-[#9CD3B0]">{num(detailQuery.data.batch.findings_raised)}</p>
                        <p className="text-[9px] font-bold uppercase tracking-[0.12em] text-white/50">findings</p>
                      </div>
                    </div>
                  </div>
                </div>
                <div className="flex flex-wrap items-center gap-2 px-5 py-4">
                  <button onClick={errorCsv} className="btn-ghost text-xs">
                    <Download className="h-4 w-4" /> Download rejected rows (CSV)
                  </button>
                  <Link to="/app/findings" className="btn-primary text-xs">Review findings <ArrowRight className="h-4 w-4" /></Link>
                  <button onClick={reset} className="btn-quiet text-xs">Upload another file</button>
                  <button onClick={() => navigate("/app")} className="btn-quiet ml-auto text-xs">Back to dashboard</button>
                </div>
              </Card>

              <SectionCard
                title="Row-level results"
                description="Rejected rows carry a code, the affected field and a human-readable reason. Nothing here rejects a college."
              >
                {detailQuery.data.rows.filter((row) => row.status === "rejected").length === 0 ? (
                  <div className="flex items-center gap-3 px-6 py-8 text-[12px] text-mint">
                    <CheckCircle2 className="h-5 w-5" /> Every row passed validation.
                  </div>
                ) : (
                  <div className="max-h-[420px] overflow-auto">
                    <table className="table-base min-w-[820px]">
                      <thead className="sticky top-0 bg-white">
                        <tr>
                          <th>Row</th>
                          <th>Code</th>
                          <th>Reason</th>
                          <th>Student</th>
                          <th>Programme</th>
                          <th>APAAR</th>
                        </tr>
                      </thead>
                      <tbody>
                        {detailQuery.data.rows
                          .filter((row) => row.status === "rejected")
                          .map((row) => (
                            <tr key={row.row_number}>
                              <td className="tabular-nums text-ink-soft">{row.row_number}</td>
                              <td><Badge tone="rose">{row.codes[0]}</Badge></td>
                              <td className="max-w-[320px] text-[11px] text-ink-soft">{row.errors[0]?.message ?? "—"}</td>
                              <td className="text-[11.5px] font-medium text-ink">{row.row.name ?? "—"}</td>
                              <td className="text-[11px] text-ink-soft">{row.row.programme ?? "—"}</td>
                              <td className="font-mono text-[10.5px] text-ink-soft">{row.row.apaar ?? "—"}</td>
                            </tr>
                          ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </SectionCard>

              <Alert tone="blue" title="What happens next">
                Accepted rows were enrolled and the deterministic rules ran automatically. Find them under{" "}
                <Link to="/app/findings" className="font-semibold underline">Findings</Link>, with evidence and a review history.
              </Alert>
            </>
          ) : (
            <Alert tone="rose" title="Could not load the batch">Refresh the page and try again.</Alert>
          )}
        </div>
      )}

      <div className="flex items-start gap-2 px-1 text-[10.5px] text-ink-soft/70">
        <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber" />
        APAAR format checks do not prove authenticity. Identity lookups use a labelled SIMULATED adapter.
      </div>
    </div>
  );
}
