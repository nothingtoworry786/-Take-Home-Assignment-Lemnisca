from typing import Dict, List

MAX_TURNS = 5 


class ConversationStore:
    def __init__(self):
        self._store: Dict[str, List[Dict[str, str]]] = {}

    def get(self, conversation_id: str) -> List[Dict[str, str]]:
        return self._store.get(conversation_id, [])

    def append(self, conversation_id: str, role: str, content: str) -> None:
        messages = self._store.get(conversation_id, [])
        messages.append({"role": role, "content": content})
        if len(messages) > MAX_TURNS * 2:
            messages = messages[-(MAX_TURNS * 2) :]
        self._store[conversation_id] = messages
