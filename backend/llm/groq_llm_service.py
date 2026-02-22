import time
from typing import Iterator, List, Tuple

from groq import Groq

from llm.llm_interface import LLMService


# Detailed system prompt so the model has full context and rules.
SYSTEM_PROMPT_SIMPLE = """You are the ClearPath customer support assistant. ClearPath is a project management SaaS product (tasks, projects, plans, integrations, etc.).

Your role:
- Answer only using the documentation context provided below. Do not use external knowledge or make things up.
- If the answer is not in the context, say clearly that you cannot find it in the ClearPath documentation and suggest the user contact support.
- If the question is unrelated to ClearPath (e.g. weather, sports, general knowledge), you must refuse: say "I cannot assist" or "that is not in the ClearPath documentation" and that you only answer questions about ClearPath documentation. Do not answer the off-topic question.
- When relevant, cite document names (e.g. "According to the User Guide...") so the user can look them up.
- Be concise and professional. Use short paragraphs or bullets when it helps clarity.
- If the user refers to earlier messages in the conversation, use the conversation history for context, but still base your answer only on the documentation context provided for this turn."""

SYSTEM_PROMPT_COMPLEX = """You are the ClearPath customer support assistant. ClearPath is a project management SaaS product (tasks, projects, plans, integrations, workflows, etc.).

Your role:
- Provide clear, detailed explanations that address every part of the user's question. Use the documentation context below as your only source of truth. Do not use external knowledge or invent information.
- If something is not in the context, say so clearly and suggest the user contact support.
- If the question is unrelated to ClearPath (e.g. weather, sports, general knowledge), you must refuse: say "I cannot assist" or "that is not in the ClearPath documentation" and that you only answer questions about ClearPath documentation. Do not answer the off-topic question.
- Structure your answer so it is easy to follow: use numbered steps for procedures, short paragraphs per sub-question, or bullet points where appropriate. Cite document names when relevant (e.g. "As described in the API Documentation...").
- If the user refers to earlier messages, use the conversation history for context but still base your answer only on the documentation context provided for this turn.
- Be thorough but stay on topic; do not add information that is not in the documentation."""


def _build_messages(
    system_msg: str,
    context: str,
    question: str,
    history: List[dict] | None,
) -> List[dict]:
    """Build messages list: system, optional history, then current user prompt."""
    prompt = f"""Context (from ClearPath documentation):
---
{context}
---

User question:
{question}

Your answer:"""
    messages = [{"role": "system", "content": system_msg}]
    if history:
        for m in history:
            messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": prompt})
    return messages


class GroqLLMService(LLMService):
    """
    Groq implementation of LLMService.
    """

    def __init__(self, api_key: str):
        self.client = Groq(api_key=api_key)

    def generate(
        self,
        model: str,
        context: str,
        question: str,
        classification: str = "simple",
        history: List[dict] | None = None,
    ) -> Tuple[str, int, int]:

        system_msg = SYSTEM_PROMPT_COMPLEX if classification == "complex" else SYSTEM_PROMPT_SIMPLE
        messages = _build_messages(system_msg, context, question, history)

        response = self.client.chat.completions.create(
            model=model,
            messages=messages,
        )

        end_time = time.time()

        answer = response.choices[0].message.content

        # Groq provides token usage info
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens

        return answer, input_tokens, output_tokens

    def generate_stream(
        self,
        model: str,
        context: str,
        question: str,
        classification: str = "simple",
        history: List[dict] | None = None,
    ) -> Iterator[Tuple[str, int, int]]:
        """Stream LLM response as text deltas. Final yield is ("", input_tokens, output_tokens)."""
        system_msg = SYSTEM_PROMPT_COMPLEX if classification == "complex" else SYSTEM_PROMPT_SIMPLE
        messages = _build_messages(system_msg, context, question, history)

        stream = self.client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
        )
        input_tokens = 0
        output_tokens = 0
        for chunk in stream:
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if getattr(delta, "content", None):
                    yield delta.content, 0, 0
            if getattr(chunk, "usage", None):
                input_tokens = getattr(chunk.usage, "prompt_tokens", 0) or input_tokens
                output_tokens = getattr(chunk.usage, "completion_tokens", 0) or output_tokens
        yield "", input_tokens, output_tokens