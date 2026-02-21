"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type TokenUsage = { input_tokens: number; output_tokens: number };
type Metadata = {
  model_used: string;
  classification: string;
  tokens: TokenUsage;
  latency_ms: number;
  chunks_retrieved: number;
  evaluator_flags: string[];
  evaluator_message: string | null;
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

export default function Home() {
  const [question, setQuestion] = useState("");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastResponse, setLastResponse] = useState<QueryResponse | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const q = question.trim();
    if (!q) return;
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/query`, {
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
      const data: QueryResponse = await res.json();
      setLastResponse(data);
      setConversationId(data.conversation_id);
      setQuestion("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-zinc-50 dark:bg-zinc-950 font-sans">
      <main className="mx-auto max-w-2xl min-h-screen flex flex-col py-8 px-4">
        <header className="mb-8">
          <h1 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-100">
            ClearPath Chatbot
          </h1>
          <p className="mt-1 text-sm text-zinc-500 dark:text-zinc-400">
            Ask a question about the docs. Answers use RAG and are backed by the query API.
          </p>
        </header>

        <form onSubmit={handleSubmit} className="flex flex-col gap-3 mb-6">
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Type your question..."
            rows={3}
            className="w-full rounded-lg border border-zinc-300 dark:border-zinc-600 bg-white dark:bg-zinc-900 px-4 py-3 text-zinc-900 dark:text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-2 focus:ring-zinc-400 dark:focus:ring-zinc-500 resize-none"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !question.trim()}
            className="self-end rounded-full bg-zinc-900 dark:bg-zinc-100 text-white dark:text-zinc-900 px-5 py-2.5 text-sm font-medium hover:bg-zinc-800 dark:hover:bg-zinc-200 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? "Sending…" : "Ask"}
          </button>
        </form>

        {error && (
          <div className="rounded-lg border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950/40 px-4 py-3 text-red-700 dark:text-red-300 text-sm mb-6">
            {error}
          </div>
        )}

        {lastResponse && (
          <section className="flex-1 space-y-6 rounded-lg border border-zinc-200 dark:border-zinc-700 bg-white dark:bg-zinc-900 p-5 shadow-sm">
            <div>
              <h2 className="text-sm font-medium text-zinc-500 dark:text-zinc-400 mb-2">Answer</h2>
              <div className="prose prose-zinc dark:prose-invert prose-headings:font-semibold prose-headings:tracking-tight prose-p:leading-relaxed prose-ul:my-3 prose-ol:my-3 prose-li:my-0.5 max-w-none text-zinc-900 dark:text-zinc-100">
                <ReactMarkdown
                  components={{
                    h1: ({ children }) => <h1 className="text-xl mt-6 mb-2 first:mt-0">{children}</h1>,
                    h2: ({ children }) => <h2 className="text-lg mt-5 mb-2 first:mt-0">{children}</h2>,
                    h3: ({ children }) => <h3 className="text-base font-semibold mt-4 mb-1.5 first:mt-0">{children}</h3>,
                    p: ({ children }) => <p className="mb-3 last:mb-0">{children}</p>,
                    ul: ({ children }) => <ul className="list-disc pl-5 space-y-1">{children}</ul>,
                    ol: ({ children }) => <ol className="list-decimal pl-5 space-y-1">{children}</ol>,
                    strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
                  }}
                >
                  {lastResponse.answer}
                </ReactMarkdown>
              </div>
            </div>

            {lastResponse.metadata.evaluator_message && (
              <div className="rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/40 px-4 py-3 text-amber-800 dark:text-amber-200 text-sm">
                {lastResponse.metadata.evaluator_message}
              </div>
            )}

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
              <div>
                <span className="text-zinc-500 dark:text-zinc-400">Model</span>
                <p className="font-medium text-zinc-900 dark:text-zinc-100">{lastResponse.metadata.model_used}</p>
              </div>
              <div>
                <span className="text-zinc-500 dark:text-zinc-400">Classification</span>
                <p className="font-medium text-zinc-900 dark:text-zinc-100">{lastResponse.metadata.classification}</p>
              </div>
              <div>
                <span className="text-zinc-500 dark:text-zinc-400">Latency</span>
                <p className="font-medium text-zinc-900 dark:text-zinc-100">{lastResponse.metadata.latency_ms} ms</p>
              </div>
              <div>
                <span className="text-zinc-500 dark:text-zinc-400">Tokens</span>
                <p className="font-medium text-zinc-900 dark:text-zinc-100">
                  {lastResponse.metadata.tokens.input_tokens} in / {lastResponse.metadata.tokens.output_tokens} out
                </p>
              </div>
            </div>

            {lastResponse.sources.length > 0 && (
              <div>
                <h2 className="text-sm font-medium text-zinc-500 dark:text-zinc-400 mb-2">Sources</h2>
                <ul className="space-y-2">
                  {lastResponse.sources.map((s, i) => (
                    <li key={i} className="text-sm text-zinc-700 dark:text-zinc-300">
                      <span className="font-medium">{s.document}</span>
                      {s.page != null && <span className="text-zinc-500"> (p. {s.page})</span>}
                      {s.relevance_score != null && (
                        <span className="text-zinc-500"> — score: {s.relevance_score.toFixed(2)}</span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <p className="text-xs text-zinc-400 dark:text-zinc-500">
              Conversation: {lastResponse.conversation_id}
            </p>
          </section>
        )}

        {!lastResponse && !loading && !error && (
          <p className="text-zinc-500 dark:text-zinc-400 text-sm">
            Submit a question to see the answer, metadata, and sources from the backend.
          </p>
        )}
      </main>
    </div>
  );
}
