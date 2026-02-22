"use client";

import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";

const API_BASE =process.env.API_BASE_URL ||
  "http://localhost:8000";
type TokenUsage = {
  input_tokens?: number;
  output_tokens?: number;
  input?: number;
  output?: number;
};
type Metadata = {
  model_used: string;
  classification: string;
  tokens: TokenUsage;
  latency_ms: number;
  chunks_retrieved: number;
  evaluator_flags: string[];
  evaluator_message: string | null;
  cache_hit?: boolean;
};
type Source = {
  document: string;
  page: number | null;
  relevance_score: number | null;
};
type QueryResponse = {
  answer: string;
  metadata: Metadata;
  sources: Source[];
  conversation_id: string;
};

type Message = {
  role: "user" | "assistant";
  content: string;
  response?: QueryResponse;
};

const markdownComponents = {
  h1: ({ children }: { children?: React.ReactNode }) => <h1 className="text-xl mt-6 mb-2 first:mt-0">{children}</h1>,
  h2: ({ children }: { children?: React.ReactNode }) => <h2 className="text-lg mt-5 mb-2 first:mt-0">{children}</h2>,
  h3: ({ children }: { children?: React.ReactNode }) => <h3 className="text-base font-semibold mt-4 mb-1.5 first:mt-0">{children}</h3>,
  p: ({ children }: { children?: React.ReactNode }) => <p className="mb-3 last:mb-0">{children}</p>,
  ul: ({ children }: { children?: React.ReactNode }) => <ul className="list-disc pl-5 space-y-1">{children}</ul>,
  ol: ({ children }: { children?: React.ReactNode }) => <ol className="list-decimal pl-5 space-y-1">{children}</ol>,
  strong: ({ children }: { children?: React.ReactNode }) => <strong className="font-semibold">{children}</strong>,
};

function getTokens(res: QueryResponse) {
  const t = res.metadata.tokens;
  return { in: t.input ?? t.input_tokens ?? 0, out: t.output ?? t.output_tokens ?? 0 };
}

const HEALTH_POLL_INTERVAL_MS = 5000;
const HEALTH_POLL_DURATION_MS = 60000;

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [backendHealthy, setBackendHealthy] = useState<boolean | null>(null);
  const [healthPollActive, setHealthPollActive] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    if (!healthPollActive) return;
    const check = async () => {
      try {
        const res = await fetch(`${API_BASE}/health`);
        setBackendHealthy(res.ok);
      } catch {
        setBackendHealthy(false);
      }
    };
    check();
    const interval = setInterval(check, HEALTH_POLL_INTERVAL_MS);
    const stop = setTimeout(() => {
      clearInterval(interval);
      setHealthPollActive(false);
    }, HEALTH_POLL_DURATION_MS);
    return () => {
      clearInterval(interval);
      clearTimeout(stop);
    };
  }, [healthPollActive]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const q = input.trim();
    if (!q) return;
    setLoading(true);
    setError(null);
    setMessages((prev) => [...prev, { role: "user", content: q }, { role: "assistant", content: "" }]);
    setInput("");
    try {
      const res = await fetch(`${API_BASE}/query/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: q,
          ...(conversationId && { conversation_id: conversationId }),
        }),
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `HTTP ${res.status}`);
      }
      const reader = res.body?.getReader();
      const decoder = new TextDecoder();
      if (!reader) throw new Error("No response body");
      let buffer = "";
      let gotDone = false;
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";
        for (const part of parts) {
          const line = part.split("\n").find((l) => l.startsWith("data: "));
          if (!line) continue;
          try {
            const data = JSON.parse(line.slice(6)) as { type: string; content?: string; metadata?: Metadata; sources?: Source[]; conversation_id?: string; message?: string };
            if (data.type === "chunk" && data.content !== undefined) {
              setMessages((prev) => {
                const next = [...prev];
                const last = next[next.length - 1];
                if (last?.role === "assistant") next[next.length - 1] = { ...last, content: last.content + data.content };
                return next;
              });
            } else if (data.type === "done" && data.metadata && data.sources !== undefined && data.conversation_id) {
              gotDone = true;
              const meta = data.metadata;
              const sources = data.sources;
              const cid = data.conversation_id;
              setConversationId(cid);
              setMessages((prev) => {
                const next = [...prev];
                const last = next[next.length - 1];
                if (last?.role === "assistant")
                  next[next.length - 1] = {
                    ...last,
                    response: { answer: last.content, metadata: meta, sources, conversation_id: cid },
                  };
                return next;
              });
            } else if (data.type === "error") {
              setError(data.message || "Something went wrong");
              setMessages((prev) =>
                prev.length >= 2 && prev[prev.length - 1].role === "assistant" && prev[prev.length - 1].content === ""
                  ? prev.slice(0, -1)
                  : prev
              );
              break;
            }
          } catch (_) {}
        }
      }
      if (!gotDone) {
        setError((e) => e || "Response was interrupted or incomplete.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
      setMessages((prev) => (prev.length >= 2 && prev[prev.length - 1].role === "assistant" && prev[prev.length - 1].content === "" ? prev.slice(0, -1) : prev));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-screen bg-zinc-50 dark:bg-zinc-950 font-sans">
      {/* Header */}
      <header className="shrink-0 border-b border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 px-4 py-3 flex items-center justify-between">
        <div>
          <h1 className="text-lg font-semibold text-zinc-900 dark:text-zinc-100">ClearPath Chatbot</h1>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5 flex items-center gap-2">
            Ask about the docs · streaming + conversation memory
            {healthPollActive || backendHealthy !== null ? (
              <span className="inline-flex items-center gap-1.5 text-zinc-500 dark:text-zinc-400" title="Backend health (polls every 5s for 1 min)">
                <span
                  className={`inline-block h-1.5 w-1.5 rounded-full ${
                    backendHealthy === null ? "bg-amber-500 animate-pulse" : backendHealthy ? "bg-emerald-500" : "bg-red-500"
                  }`}
                />
                {backendHealthy === null ? "checking…" : backendHealthy ? "backend ok" : "backend unreachable"}
              </span>
            ) : null}
          </p>
        </div>
        <button
          type="button"
          onClick={() => {
            setConversationId(null);
            setMessages([]);
            setError(null);
          }}
          className="text-xs font-medium text-emerald-600 dark:text-emerald-400 hover:underline"
        >
          New conversation
        </button>
      </header>
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-2xl px-4 py-6 space-y-6">
          {messages.length === 0 && !loading && (
            <div className="text-center py-12 text-zinc-500 dark:text-zinc-400 text-sm">
              Send a message to start the conversation.
            </div>
          )}
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                  msg.role === "user"
                    ? "bg-emerald-600 text-white rounded-br-md"
                    : "bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 border border-zinc-200 dark:border-zinc-700 rounded-bl-md shadow-sm"
                }`}
              >
                {msg.role === "user" ? (
                  <p className="text-[15px] whitespace-pre-wrap">{msg.content}</p>
                ) : (
                  <div className="prose prose-zinc dark:prose-invert max-w-none text-[15px]">
                    {loading && msg.content === "" ? (
                      <span className="text-zinc-500 dark:text-zinc-400">Thinking...</span>
                    ) : (
                      <ReactMarkdown components={markdownComponents}>{msg.content}</ReactMarkdown>
                    )}
                    {msg.response?.metadata.evaluator_message && (
                      <p className="mt-3 text-amber-600 dark:text-amber-400 text-sm">
                        {msg.response.metadata.evaluator_message}
                      </p>
                    )}
                    {msg.response && msg.response.sources.length > 0 && (
                      <details className="mt-3 text-xs text-zinc-500 dark:text-zinc-400">
                        <summary className="cursor-pointer font-medium">Sources</summary>
                        <ul className="mt-1 space-y-0.5 pl-4">
                          {msg.response.sources.slice(0, 5).map((s, j) => (
                            <li key={j}>
                              {s.document}
                              {s.page != null && ` (p. ${s.page})`}
                            </li>
                          ))}
                          {msg.response.sources.length > 5 && (
                            <li>+{msg.response.sources.length - 5} more</li>
                          )}
                        </ul>
                      </details>
                    )}
                    {msg.response && (
                      <p className="mt-2 text-xs opacity-70">
                        {msg.response.metadata.model_used} · {msg.response.metadata.latency_ms}ms ·{" "}
                        {getTokens(msg.response).in + getTokens(msg.response).out} tokens
                      </p>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="shrink-0 mx-4 mb-2 rounded-lg bg-red-50 dark:bg-red-950/50 border border-red-200 dark:border-red-800 px-3 py-2 text-red-700 dark:text-red-300 text-sm">
          {error}
        </div>
      )}

      {/* Input */}
      <div className="shrink-0 border-t border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 p-4">
        <form onSubmit={handleSubmit} className="mx-auto max-w-2xl flex gap-3 items-end">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                handleSubmit(e as unknown as React.FormEvent);
              }
            }}
            placeholder="Message ClearPath..."
            rows={1}
            className="flex-1 min-h-[44px] max-h-32 resize-none rounded-xl border border-zinc-300 dark:border-zinc-600 bg-zinc-50 dark:bg-zinc-800 px-4 py-3 text-zinc-900 dark:text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="shrink-0 h-11 w-11 rounded-xl bg-emerald-600 text-white flex items-center justify-center hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            aria-label="Send"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M22 2L11 13" />
              <path d="M22 2L15 22L11 13L2 9L22 2Z" />
            </svg>
          </button>
        </form>
      </div>
    </div>
  );
}
