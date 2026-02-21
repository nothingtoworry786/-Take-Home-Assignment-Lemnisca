import json
import os
from datetime import datetime


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
            "timestamp": datetime.utcnow().isoformat(),
            "query": query,
            "classification": classification,
            "model_used": model_used,
            "tokens_input": tokens_input,
            "tokens_output": tokens_output,
            "latency_ms": latency_ms
        }

        # Read existing logs
        with open(self.log_file, "r") as f:
            logs = json.load(f)

        # Append new entry
        logs.append(log_entry)

        # Write back
        with open(self.log_file, "w") as f:
            json.dump(logs, f, indent=2)