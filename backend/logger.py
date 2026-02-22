import json
import os


class RoutingLogger:
    """
    Logs routing decisions and token usage to a JSON file.
    """

    def __init__(self, log_file: str = "backend/logs/routing_logs.json"):
        self.log_file = log_file

        # Ensure logs directory exists
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)

        # Create file if it doesn't exist
        if not os.path.exists(self.log_file):
            with open(self.log_file, "w") as f:
                json.dump([], f)

    def log(
        self,
        query: str,
        classification: str,
        model_used: str,
        tokens_input: int,
        tokens_output: int,
        latency_ms: int
    ) -> None:

        log_entry = {
            "query": query,
            "classification": classification,
            "model_used": model_used,
            "tokens_input": tokens_input,
            "tokens_output": tokens_output,
            "latency_ms": latency_ms,
        }

        try:
            with open(self.log_file, "r") as f:
                content = f.read().strip()
                logs = json.loads(content) if content else []
        except (json.JSONDecodeError, FileNotFoundError):
            logs = []

        logs.append(log_entry)

        with open(self.log_file, "w") as f:
            json.dump(logs, f, indent=2)