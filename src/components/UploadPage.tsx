import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom"; // <-- add this
import DropZone from "../components/DropZone";
import { API_BASE, watchProgress, ProgressState } from "../../utils/progress";


type FileItem = {
  id: string;
  file: File;
  sizeMB: number;
  jobId?: string;
  progress: number; // 0..100
  stage?: string;
  message?: string;
  error?: string | null;
  done?: boolean;
};

function Bar({ value }: { value: number }) {
  return (
    <div style={{ width: "100%", height: 6, background: "#eef2ff", borderRadius: 999 }}>
      <div
        style={{
          width: `${Math.max(0, Math.min(100, value))}%`,
          height: 6,
          background: "#2563eb",
          borderRadius: 999,
          transition: "width 200ms linear",
        }}
      />
    </div>
  );
}

export default function UploadPage() {
  const navigate = useNavigate();
  const [items, setItems] = useState<FileItem[]>([]);
  const [busy, setBusy] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);
  const [redirectIn, setRedirectIn] = useState(2);

  const overall = useMemo(() => {
    if (!items.length) return 0;
    const sum = items.reduce((acc, it) => acc + (it.progress || 0), 0);
    return Math.round(sum / items.length);
  }, [items]);

  const allDone = items.length > 0 && items.every((x) => x.done);
  const hasErrors = items.some((x) => !!x.error);

  const onFiles = (files: File[]) => {
    const next = files
      .filter((f) => f.type === "application/pdf")
      .slice(0, 10 - items.length)
      .map<FileItem>((f) => ({
        id: crypto.randomUUID(),
        file: f,
        sizeMB: f.size / 1024 / 1024,
        progress: 0,
        stage: "queued",
      }));
    setItems((prev) => [...prev, ...next]);
  };

  const removeItem = (id: string) => setItems((prev) => prev.filter((x) => x.id !== id));

  async function uploadOne(fi: FileItem): Promise<FileItem> {
    const form = new FormData();
    form.append("file", fi.file);
    const r = await fetch(`${API_BASE}/upload`, { method: "POST", body: form });
    if (!r.ok) throw new Error(`Upload failed (${r.status})`);
    const data = await r.json();
    return { ...fi, jobId: data.jobId, stage: "extracting", progress: 5, message: "Reading PDF…" };
  }

  function startWatcher(fi: FileItem) {
    if (!fi.jobId) return;
    const update = (p: ProgressState) => {
      setItems((prev) =>
        prev.map((x) =>
          x.id === fi.id
            ? {
                ...x,
                progress: p.progress ?? x.progress,
                stage: p.stage ?? x.stage,
                message: p.message ?? x.message,
                error: p.error ?? null,
                done: p.done ?? false,
              }
            : x
        )
      );
    };
    watchProgress(fi.jobId, update, update);
  }

  const process = async () => {
    if (!items.length) return;
    setBusy(true);
    for (let i = 0; i < items.length; i++) {
      const curr = items[i];
      if (curr.jobId) continue;
      try {
        const withJob = await uploadOne(curr);
        setItems((prev) => prev.map((x) => (x.id === curr.id ? withJob : x)));
        startWatcher(withJob);
      } catch (e: any) {
        setItems((prev) =>
          prev.map((x) =>
            x.id === curr.id
              ? { ...x, error: e?.message || "Upload failed", stage: "error", progress: 100, done: true }
              : x
          )
        );
      }
    }
    setBusy(false);
  };

  useEffect(() => {
    sessionStorage.removeItem("indexed");
  }, []);

  // When all files finish successfully, show banner then auto-proceed
  useEffect(() => {
    if (allDone && !hasErrors) {
      setShowSuccess(true);
      setRedirectIn(2);
      sessionStorage.setItem("indexed", "1"); 
      const to = setTimeout(() => navigate("/query", { replace: true }), 1500);
      return () => clearTimeout(to);
    }
  }, [allDone, hasErrors, navigate]);

  useEffect(() => {
    if (!showSuccess) return;
    const t = setInterval(() => setRedirectIn((s) => s - 1), 1000);
    return () => clearInterval(t);
  }, [showSuccess]);

  

  return (
    <div className="min-h-screen bg-white">
      <div className="max-w-6xl mx-auto px-5 py-10">
        <h1 className="text-4xl font-extrabold text-slate-900 mb-2">Upload Documents</h1>
        <p className="text-slate-600 mb-6">
          Add your PDFs to index. The pipeline runs: <b>upload → extract → chunk → embed</b>.
        </p>

        {showSuccess && !hasErrors && (
        <div className="mb-4 flex items-center gap-3 rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-2 text-emerald-800">
          <span className="text-xl">✅</span>
          <span className="font-semibold">Processing complete.</span>
          <span className="ml-auto text-sm">Continuing to Query in {redirectIn}s…</span>
          <button
            onClick={() => navigate("/query")}  // <-- change here
            className="ml-2 rounded-md bg-emerald-600 px-3 py-1.5 text-white font-semibold"
          >
            Go now
          </button>
        </div>
      )}

      {hasErrors && (
        <div className="mb-4 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-rose-800">
          Some files had errors. You can still proceed—only successfully indexed chunks will be available.
          <button
            onClick={() => navigate("/query")}  // <-- change here
            className="ml-3 rounded-md bg-rose-600 px-3 py-1.5 text-white font-semibold"
          >
            Go to Query
          </button>
        </div>
      )}

        <div className="rounded-2xl border border-slate-200 bg-white shadow-xl shadow-slate-900/5 p-6">
          <DropZone onFiles={onFiles} disabled={busy} />

          <div className="flex items-center gap-3 mt-4">
            <div className="grow">
              <Bar value={overall} />
            </div>
            <div className="w-40 text-right text-slate-500 text-sm">
              Overall progress: <b>{overall}%</b>
            </div>
          </div>

          <div className="mt-4 grid gap-3">
            {items.map((it) => (
              <div key={it.id} className="rounded-xl border border-slate-200 bg-white p-3">
                <div className="flex items-center gap-3">
                  <div className="text-xl">📄</div>
                  <div className="grow">
                    <div className="font-semibold text-slate-900">{it.file.name}</div>
                    <div className="text-xs text-slate-500">{(it.sizeMB).toFixed(1)} MB</div>
                  </div>
                  <button
                    className="text-slate-400 hover:text-slate-600"
                    title="Remove"
                    onClick={() => removeItem(it.id)}
                    disabled={it.progress > 0 && !it.done}
                  >
                    ✕
                  </button>
                </div>
                <div className="mt-2">
                  <Bar value={it.progress} />
                </div>
                <div
                  className={`mt-1 text-sm ${
                    it.error ? "text-rose-700" : it.done ? "text-emerald-700 font-semibold" : "text-slate-600"
                  }`}
                >
                  {it.error ? `Error: ${it.error}` : it.done ? "Processing complete." : it.message || it.stage}
                </div>
              </div>
            ))}
          </div>

          <div className="mt-4 flex items-center gap-3">
            <button
              disabled={!items.length || busy}
              onClick={process}
              className={`rounded-lg px-4 py-2 font-bold text-white shadow-md ${
                !items.length || busy ? "bg-blue-300 cursor-not-allowed" : "bg-blue-600 hover:bg-blue-700"
              }`}
            >
              {busy ? "Processing…" : "Process & Index"}
            </button>
            <span className="text-slate-500 text-sm">
              Tip: large PDFs may take a while. Keep this tab open.
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
