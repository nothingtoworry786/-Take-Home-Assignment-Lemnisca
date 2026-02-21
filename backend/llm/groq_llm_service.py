import time
from typing import Iterator, List, Tuple

from groq import Groq

from llm.llm_interface import LLMService


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
        """
        Calls Groq LLM with RAG context and question. Optional history for conversation memory.
        """
        if classification == "complex":
            system_msg = "You are the ClearPath support assistant. For this query, provide a clear, detailed explanation that addresses everything the user asked. Answer only from the given documentation. If the user refers to earlier messages, use the conversation history for context but still base answers on the documentation context provided."
        else:
            system_msg = "You are the ClearPath support assistant. Answer only from the given documentation. If information is missing, say so clearly. You may use conversation history for context when the user refers to earlier messages."

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
        if classification == "complex":
            system_msg = "You are the ClearPath support assistant. For this query, provide a clear, detailed explanation. Answer only from the given documentation. You may use conversation history for context when the user refers to earlier messages."
        else:
            system_msg = "You are the ClearPath support assistant. Answer only from the given documentation. If information is missing, say so clearly. You may use conversation history for context when the user refers to earlier messages."
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