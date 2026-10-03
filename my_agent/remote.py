"""P7 — Remote agent client (A2A)."""

from __future__ import annotations

from typing import Any
import httpx
from  my_agent.context import AgentResult, ExecutionContext


class RemoteAgent:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    async def send(self, message: str, **kwargs: Any) -> Any:
        context = kwargs.get('context') or ExecutionContext()
        
        async with httpx.AsyncClient() as client:
            respones = await client.post(
                f"{self.base_url}/task/send",
                json={
                    "jsonrpc": "2.0",
                    "method": "task/send",
                    "params": {
                        "message": {
                            "role": "user",
                            "parts": [{"type": "text", "text": message}]
                        }
                    }
                },
                timeout=120
            )
            data = respones.json()
        output = ""
        task = data.get('result') or {}
        for artifact in task.get("artifacts", []):
            for part in artifact.get("parts", []):
                if part.get("type") == "text":
                    output += (part.get("text") or "") + "\n"
        output = output.strip()

        return AgentResult(output=output, context=context)
