# Q1 — Routing Logic

## Router Rules

The router classifies a query as **simple** if it meets *all* of the following criteria:
- Does **not** contain question words such as "why", "how", "explain", or "describe".
- Contains two or fewer entities (detected via a simple NER pass or by counting proper nouns/phrases).
- No explicit request for reasoning or multi-step operation is detected (e.g., "compare", "summarize", "reason about").
- Query length is under 15 words.

All other queries are considered **complex**.

**Boundary rationale:**  
The line is drawn to favor high precision for "simple" queries — that is, queries that can be answered with a direct factual lookup or simple extraction. The router errs on the side of marking ambiguous or multi-step queries as complex to ensure quality, since those require synthesis or reasoning.

**Example Misclassification:**  
_Query:_ "What year did Ada Lovelace write the first algorithm and who helped her?"

**Classification:** Simple  
**What happened:** The router counted only two entities and short length, but missed that it's actually a two-part, reasoning style question — thus it would benefit from the complex path.  
**Why:** The rule set did not properly catch implicit requests for synthesis ("and who helped her").

**Improvement without LLM:**  
- Incorporate more advanced syntactic parsing to explicitly detect conjunctions ("and", "or"), multi-part questions, or sentences with multiple verbs, indicating complexity.
- Use keyword lists/phrase detection for common reasoning triggers.

---

# Q2 — Retrieval Failures

**Realistic Failure Case:**

- **Query:** "Who were Ada Lovelace's collaborators besides Charles Babbage?"
- **What was retrieved:** Chunk describing Ada Lovelace’s biography but only mentioning Charles Babbage, not secondary collaborators.
- **Why did it fail:** Keyword-based retrieval matched "Lovelace" and "Babbage" (common co-occurrence), but the nuance of "besides Charles Babbage" wasn't recognized by the retriever, so it didn't prioritize chunks mentioning other collaborators.
- **What would fix it:** 
  - Add negative keyword handling — deprioritize or filter out chunks referencing "Charles Babbage" when asked "besides Charles Babbage."
  - Integrate basic query rewriting to clarify to the retriever what *not* to include.
  - Use retrieval models with better semantic understanding, even if not full LLMs (like smaller bi-encoders).

---

# Q3 — Cost and Scale

## Daily Token Usage Estimate (5,000 queries, Groq free-tier as reference)

- **Router Model (if any):** If rule-based, 0 tokens. If using a model, assume mini-LM: ~50 tokens/query → 250,000 tokens/day.
- **Retriever Model:** Query embedding or search, typically negligible unless using encode API (assume negligible for classical retrievers).  
- **Final Answer Model (e.g., Mixtral-8x7B):**
    - Context: ~1,000 tokens input per query (retrieved chunks + query)
    - Output: ~100 tokens per answer
    - **Total per query:** 1,100 tokens
    - **Total per day:** 1,100 x 5,000 = **5,500,000 tokens/day**

**Biggest cost driver:**  
The LLM model that synthesizes the final answer (i.e., Mixtral-8x7B’s combined input + output). Over 95% of the daily token usage.

**Single highest-ROI optimization (without hurting quality):**  
Reduce the number/size of retrieved chunks passed to the answer model (e.g., only pass top-2 instead of top-5), perhaps aided by a re-ranker. This directly shrinks token input for every answer with relatively little impact on answer quality if chunk selection is strong.

**Avoided Optimization & Why:**  
"Prompt truncation"—blindly sending less context or only part of the document to the model. Hurts accuracy and answer completeness. Context is critical for high quality in RAG: improving chunk selection is safer than simply sending less data indiscriminately.

---

# Q4 — What Is Broken

**Most significant flaw:**  
The system is brittle to nuanced or ambiguous queries. The router and retriever rely on heuristics and keyword matching, lacking robust semantic understanding. This means queries with negations, "compare/contrast", or implicit information needs (e.g., "Who *didn't* work on X?") often yield irrelevant, incomplete, or wrong results.

**Why ship with it:**  
Shipping with rule-based/keyword solutions enables fast prototyping, cost control, and transparency. Semantic/query understanding with small models (not LLMs) is still non-trivial, and full LLM-based routing/retrieval was out of scope for the project or exceeded compute/cost budgets.

**Fix, given more time:**  
Integrate a small transformer or bi-encoder-based semantic retriever, or at least a neural re-ranker, to better handle ambiguity and query intent. Alternatively, invest in a more sophisticated, possibly statistical, query classifier for the router.

---

## Conversation memory

**Design decisions:**

- **In-memory store keyed by `conversation_id`:** No DB dependency; simple and fast for a single backend process. History is lost on restart — acceptable for a take-home/demo.
- **Last 5 turns only:** Each “turn” is one user message + one assistant message, so we keep at most 10 messages (5 user + 5 assistant). This bounds context size and avoids unbounded growth in long chats.
- **When to use history:** History is fetched and passed to the LLM only when the client sends a `conversation_id` (i.e. a follow-up in an existing thread). The first message in a thread has no history.
- **Cache and memory:** When `conversation_id` is present we skip the exact-question cache, so follow-ups always get a fresh answer that can refer to prior turns.

**Token cost tradeoff:**

- Sending history increases **input tokens** every time (each turn adds ~2 messages to the prompt). Capping at 5 turns keeps a predictable upper bound (e.g. on the order of hundreds to low thousands of extra tokens per request).
- Tradeoff: more turns → better coherence and “remember what I asked” vs. higher cost and slower responses. The 5-turn cap is a compromise: enough for short multi-turn threads without blowing up context.

## Streaming and structured output

**Where structured output parsing breaks with streaming:**

- **Streaming is token-by-token:** The client (and the backend) see incremental text, not a single final blob. You can’t “parse” a JSON or other structured payload until you have a complete unit (e.g. a full JSON object).
- **Our flow:** We stream **plain text** (the answer body) only. Metadata (model, tokens, latency, sources, `conversation_id`) is sent in a **separate final SSE event** (`type: "done"`) after the stream ends. So we never try to parse structured output from the stream itself — we only parse the `done` event, which is one complete JSON object.
- **If we had streamed structured output:** For example, if the LLM were instructed to output JSON (e.g. `{"answer": "...", "sources": [...]`), then:
  - **Mid-stream:** You only have a prefix (e.g. `{"answer": "The`), which is invalid JSON. You cannot reliably parse or validate until the closing `}` (and any nested content) has arrived.
  - **Incremental parsing:** You’d need a streaming JSON parser or to buffer until a complete top-level object is received, which adds complexity and can be fragile (e.g. JSON with embedded newlines or unescaped content).
- **Evaluator:** Our evaluator runs **after** the full answer is collected (post-stream), so it always sees the complete text. No parsing of partial output.

---


**prompts**

- *"Read the backend file and update the frontend file"* — to connect the Next.js UI to the `/query` API and show answer, metadata, and sources.
- *"Make the frontend like how I chat GPT"* — to turn the page into a chat-style UI with user/assistant bubbles, conversation history, and fixed bottom input.
- *"Add stream to this"* — to add streaming (SSE) on the backend and consume it on the frontend so the answer appears token-by-token.
- *"Is the error handling happening properly?"* — to add backend stream error events and frontend handling for errors and interrupted streams.
- *"In the frontend add health endpoint where it will request the backend every 5 sec for one min"* — to add health polling and the status indicator in the header.


