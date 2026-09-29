import { useRef, useState } from "react";
import { api, type ChatResponse } from "../api";

interface Msg {
  role: "user" | "assistant";
  text: string;
  meta?: ChatResponse | null;
  error?: boolean;
}

const SUGGESTIONS = [
  "أي مضخة محتاجة صيانة قريب؟",
  "ما حالة MP-03؟",
  "إيه إجراءات فحص البيرنج؟",
  "لخص لي التنبيهات الحرجة",
];

function confBadge(c: string) {
  const map: Record<string, { label: string; cls: string }> = {
    HIGH: { label: "ثقة عالية", cls: "ok" },
    MEDIUM: { label: "ثقة متوسطة", cls: "warn" },
    LOW: { label: "ثقة منخفضة", cls: "muted" },
  };
  const info = map[c] ?? { label: c, cls: "muted" };
  return <span className={`badge ${info.cls}`}>{info.label}</span>;
}

export default function ChatPage() {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement | null>(null);

  const send = async (q: string) => {
    const question = q.trim();
    if (!question || busy) return;
    setInput("");
    setMsgs((prev) => [...prev, { role: "user", text: question }]);
    setBusy(true);
    try {
      const resp = await api<ChatResponse>("/api/ai/chat", {
        method: "POST",
        body: JSON.stringify({ question }),
      });
      setMsgs((prev) => [...prev, { role: "assistant", text: resp.answer, meta: resp }]);
    } catch (e) {
      setMsgs((prev) => [
        ...prev,
        { role: "assistant", text: `تعذّر الحصول على إجابة: ${String((e as Error).message ?? e)}`, error: true },
      ]);
    } finally {
      setBusy(false);
      setTimeout(() => endRef.current?.scrollIntoView({ behavior: "smooth" }), 60);
    }
  };

  return (
    <div>
      <h2 className="page-title">المساعد الذكي — RAG (§28)</h2>
      <p className="page-desc">
        اسأل عن حالة الأسطول، مضخة محددة، أو إجراءات المانوالات — المساعد يبني الإجابة من بيانات النظام
        ومقتطفات المانوالات، وكل إجابة تحمل مصادرها وثقتها (LLM محلي — بدون إنترنت).
      </p>

      <div className="card">
        {msgs.length === 0 && (
          <div className="suggestions">
            {SUGGESTIONS.map((s) => (
              <button key={s} className="btn" onClick={() => void send(s)}>
                {s}
              </button>
            ))}
          </div>
        )}
        <div className="chat-wrap">
          {msgs.map((m, i) => (
            <div key={i} className={`chat-msg ${m.role}${m.error ? " err" : ""}`}>
              {m.text}
              {m.meta && (
                <div className="chat-meta">
                  {confBadge(m.meta.confidence)}
                  {m.meta.related_assets.map((a) => (
                    <span key={a} className="badge info mono">
                      {a}
                    </span>
                  ))}
                  {m.meta.sources.map((s, j) => (
                    <span key={j} className="badge muted">
                      {s.type === "MANUAL"
                        ? `Manual #${s.manual_id ?? "?"} · ص ${s.page ?? "?"}`
                        : s.asset_code ?? s.type}
                    </span>
                  ))}
                  {m.meta.sources_dropped > 0 && (
                    <span className="badge muted">استُبعد {m.meta.sources_dropped} مرجع غير موثّق</span>
                  )}
                </div>
              )}
            </div>
          ))}
          {busy && <div className="chat-msg assistant waiting">المساعد يكتب… (قد يستغرق حتى دقيقة)</div>}
          <div ref={endRef} />
        </div>
        <div className="chat-input-row">
          <input
            type="text"
            placeholder="اكتب سؤالك… مثال: أي مضخة محتاجة صيانة؟"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void send(input);
            }}
            disabled={busy}
          />
          <button className="btn primary" onClick={() => void send(input)} disabled={busy || !input.trim()}>
            إرسال
          </button>
        </div>
      </div>
    </div>
  );
}
