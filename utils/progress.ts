// src/utils/progress.ts
export type ProgressState = {
    stage: string;
    progress: number;   // 0..100
    message?: string;
    done?: boolean;
    error?: string | null;
  };
  
  export const API_BASE = "http://localhost:8000";
  
  export function watchProgress(
    jobId: string,
    onUpdate: (p: ProgressState) => void,
    onDone?: (p: ProgressState) => void,
    onError?: (err: any) => void
  ) {
    let closed = false;
    let pollTimer: any = null;
  
    const finish = (p: ProgressState) => {
      if (closed) return;
      onUpdate(p);
      if (p.done) {
        onDone?.(p);
        close();
      }
    };
  
    const poll = async () => {
      if (closed) return;
      try {
        const r = await fetch(`${API_BASE}/progress_json?jobId=${encodeURIComponent(jobId)}`);
        const data = (await r.json()) as ProgressState;
        finish(data);
      } catch (e) {
        onError?.(e);
      } finally {
        if (!closed) pollTimer = setTimeout(poll, 700);
      }
    };
  
    // Primary: SSE
    let es: EventSource | null = null;
    try {
      es = new EventSource(`${API_BASE}/progress?jobId=${encodeURIComponent(jobId)}`);
  
      // If SSE doesn’t deliver anything quickly, fall back to polling.
      const guard = setTimeout(() => {
        if (!closed) {
          es?.close();
          poll();
        }
      }, 2500);
  
      es.onmessage = (ev) => {
        try {
          const payload = JSON.parse(ev.data) as ProgressState;
          onUpdate(payload);
          if (payload.done) {
            clearTimeout(guard);
            onDone?.(payload);
            close();
          }
        } catch {}
      };
  
      es.onerror = () => {
        clearTimeout(guard);
        es?.close();
        poll();
      };
    } catch {
      poll();
    }
  
    function close() {
      closed = true;
      es?.close();
      if (pollTimer) clearTimeout(pollTimer);
    }
  
    return { close };
  }
  