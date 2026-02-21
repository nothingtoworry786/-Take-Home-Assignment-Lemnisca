import time
from typing import Tuple

from groq import Groq

from llm.llm_interface import LLMService


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
        classification: str = "simple"
    ) -> Tuple[str, int, int]:
        """
        Calls Groq LLM with RAG context and question.

        Returns:
            answer (str),
            input_tokens (int),
            output_tokens (int)
        """

        start_time = time.time()

        if classification == "complex":
            prompt = f"""You are a customer support assistant for ClearPath, a project management SaaS tool.

Instructions:
- The user has asked a question that may have multiple parts or need a detailed answer. Explain in detail what they asked, addressing each part clearly.
- Use ONLY the context below. Do not use external knowledge.
- If something is not in the context, say so clearly and suggest they contact support.
- Structure your answer so it is easy to follow (e.g. use short paragraphs or bullet points per sub-question). Cite document names when relevant.

Context (from ClearPath documentation):
---
{context}
---

User question:
{question}

Your detailed answer:"""
            system_msg = "You are the ClearPath support assistant. For this query, provide a clear, detailed explanation that addresses everything the user asked. Answer only from the given documentation."
        else:
            prompt = f"""You are a customer support assistant for ClearPath, a project management SaaS tool. Be concise, accurate, and professional.

Instructions:
- Answer using ONLY the context below. Do not use external knowledge.
- If the answer is not in the context, respond clearly that you cannot find it in the documentation and suggest the user contact support.
- Cite document names when relevant. Do not invent or assume details.

Context (from ClearPath documentation):
---
{context}
---

User question:
{question}

Your answer:"""
            system_msg = "You are the ClearPath support assistant. Answer only from the given documentation. If information is missing, say so clearly."

        response = self.client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt}
            ]
        )

        end_time = time.time()

        answer = response.choices[0].message.content

        # Groq provides token usage info
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens

        return answer, input_tokens, output_tokens