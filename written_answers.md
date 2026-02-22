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

