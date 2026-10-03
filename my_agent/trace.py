"""Colored agent debug trace (opt-in via MY_AGENT_TRACE)."""

from __future__ import annotations

import json
import os
from typing import Any, Iterable, Optional

from rich.console import Console, Group
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text

from my_agent.types import Message, ToolCall, ToolResult

ENV_VAR = "MY_AGENT_TRACE"
_TRUE = {"1", "true", "yes", "on"}
_DEFAULT_MAX_CHARS = 500
_CODE_MAX_CHARS = 4000
_CODE_KEYS = {"code", "script", "source", "python", "program"}


def trace_enabled() -> bool:
    return os.getenv(ENV_VAR, "").strip().lower() in _TRUE


def _truncate(text: str, max_chars: int = _DEFAULT_MAX_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}…(+{len(text) - max_chars} chars)"


def _syntax(code: str, lexer: str, *, max_chars: int = _CODE_MAX_CHARS) -> Syntax | Text:
    rendered = _truncate(code, max_chars)
    try:
        return Syntax(
            rendered,
            lexer,
            theme="monokai",
            line_numbers=True,
            word_wrap=True,
            background_color="default",
        )
    except Exception:
        return Text(rendered)


def _json_block(data: Any) -> Syntax | Text:
    try:
        rendered = json.dumps(data, ensure_ascii=False, indent=2)
    except TypeError:
        rendered = str(data)
    return _syntax(rendered, "json", max_chars=800)


def _looks_like_code(text: str) -> bool:
    if "\n" in text and any(token in text for token in ("def ", "import ", "print(", "class ", "return ")):
        return True
    return False


def _format_arguments(arguments: dict | None) -> Any:
    """Render tool args; pull out code fields as highlighted Python blocks."""
    if not arguments:
        return Text("(no arguments)", style="dim")

    parts: list[Any] = []
    rest: dict[str, Any] = {}
    for key, value in arguments.items():
        if isinstance(value, str) and (key.lower() in _CODE_KEYS or _looks_like_code(value)):
            label = Text()
            label.append(f"{key}:", style="bold dim")
            parts.append(label)
            parts.append(_syntax(value, "python"))
        else:
            rest[key] = value
    if rest:
        parts.append(_json_block(rest))
    if not parts:
        return _json_block(arguments)
    return Group(*parts) if len(parts) > 1 else parts[0]


def _loads_json(text: str) -> Any | None:
    stripped = text.strip()
    if not stripped or stripped[0] not in "{[\"":
        return None
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return None


def _unwrap_json(content: Any, *, depth: int = 3) -> Any:
    current = content
    for _ in range(depth):
        if not isinstance(current, str):
            return current
        parsed = _loads_json(current)
        if parsed is None:
            return current
        current = parsed
    return current


def _format_payload(content: Any) -> Any:
    """Pretty-print tool results; expand nested JSON / stdout when possible."""
    parsed = _unwrap_json(content)
    if isinstance(parsed, dict):
        logs = parsed.get("logs")
        if isinstance(logs, str):
            logs = _unwrap_json(logs)
        if isinstance(logs, dict) and isinstance(logs.get("stdout"), list):
            stdout = "".join(str(line) for line in logs["stdout"])
            parts: list[Any] = [Text("stdout:", style="bold dim"), _syntax(stdout, "text")]
            if logs.get("stderr"):
                parts.append(Text("stderr:", style="bold dim"))
                parts.append(_syntax("".join(str(x) for x in logs["stderr"]), "text"))
            other = {k: v for k, v in parsed.items() if k != "logs"}
            if other:
                parts.append(_json_block(other))
            return Group(*parts)
        return _json_block(parsed)
    if isinstance(parsed, list):
        return _json_block(parsed)
    text = str(parsed) if parsed is not None else ""
    if "\n" in text:
        return _syntax(text, "text")
    return Text(_truncate(text))


def _format_item(item: Any) -> Text | Group:
    if isinstance(item, Message):
        body = Text()
        body.append(f"[{item.role}] ", style="bold green" if item.role == "user" else "bold yellow")
        body.append(_truncate(item.content or ""))
        return body
    if isinstance(item, ToolCall):
        head = Text()
        head.append("▶ tool ", style="bold magenta")
        head.append(item.name, style="magenta")
        head.append(f"  id={item.tool_call_id}", style="dim")
        return Group(head, _format_arguments(item.arguments))
    if isinstance(item, ToolResult):
        head = Text()
        style = "bold green" if item.status == "success" else "bold red"
        head.append("◀ result ", style=style)
        head.append(item.name, style=style)
        head.append(f"  ({item.status})", style="dim")
        content = item.content[0] if item.content else ""
        return Group(head, _format_payload(content))
    return Text(f"{type(item).__name__}: {_truncate(str(item))}")

class AgentTrace:
    """Terminal timeline for agent debugging. Disabled unless MY_AGENT_TRACE is set."""

    def __init__(self, enabled: bool | None = None, console: Console | None = None):
        self.enabled = trace_enabled() if enabled is None else enabled
        self.console = console or Console()
        self._index = 0

    def _next(self) -> str:
        self._index += 1
        return f"{self._index:02d}"

    def _rule(self, title: str, style: str) -> None:
        if not self.enabled:
            return
        self.console.print(f"[bold {style}][{self._next()}] {title}[/]")

    def run_start(self, name: str = "agent") -> None:
        if not self.enabled:
            return
        self.console.rule(f"[bold]Agent run · {name}[/]", style="dim")
        self._rule("run.start", "dim")

    def run_done(self, status: str, output: Any = None, tools: Optional[Iterable[str]] = None) -> None:
        if not self.enabled:
            return
        meta = Text()
        meta.append("status=", style="dim")
        meta.append(status, style="bold")
        if tools is not None:
            meta.append("  tools=", style="dim")
            meta.append(str(list(tools)))
        if output is not None:
            meta.append("\n")
            meta.append(_truncate(str(output), 300))
        self.console.print(Panel(meta, title=f"[{self._next()}] run.done", border_style="dim"))

    def skill_discovered(self, name: str, description: str = "", path: Any = None) -> None:
        if not self.enabled:
            return
        body = Text()
        body.append(name, style="bold cyan")
        if description:
            body.append(f"\n{_truncate(description, 200)}", style="dim")
        if path is not None:
            body.append(f"\n{path}", style="dim")
        self.console.print(Panel(body, title=f"[{self._next()}] skill.discovered", border_style="cyan"))

    def llm_request(self, request: Any, model: str | None = None) -> None:
        if not self.enabled:
            return
        lines: list[Any] = []
        header = Text()
        if model:
            header.append("model=", style="dim")
            header.append(str(model))
        if getattr(request, "tool_choice", None):
            header.append("  tool_choice=", style="dim")
            header.append(str(request.tool_choice))
        tools = getattr(request, "tools", None) or []
        names = [getattr(t, "name", type(t).__name__) for t in tools]
        if names:
            header.append("  tools=", style="dim")
            header.append(", ".join(names))
        if header.plain:
            lines.append(header)

        for instruction in getattr(request, "instructions", None) or []:
            block = Text()
            block.append("[system] ", style="bold cyan")
            block.append(_truncate(str(instruction)))
            lines.append(block)

        for item in getattr(request, "contents", None) or []:
            lines.append(_format_item(item))

        self.console.print(
            Panel(Group(*lines) if lines else Text("(empty)"), title=f"[{self._next()}] ▶ llm.request", border_style="cyan")
        )

    def llm_response(
        self,
        response: Any,
        *,
        finish_reason: str | None = None,
        model: str | None = None,
    ) -> None:
        if not self.enabled:
            return
        lines: list[Any] = []
        meta = Text()
        if model:
            meta.append("model=", style="dim")
            meta.append(str(model))
        if finish_reason:
            meta.append("  finish=", style="dim")
            meta.append(str(finish_reason), style="bold")
        usage = getattr(response, "usage_metadata", None) or {}
        if usage:
            meta.append(
                f"  tokens in={usage.get('input_tokens')} out={usage.get('output_tokens')}",
                style="dim",
            )
        if meta.plain:
            lines.append(meta)

        if getattr(response, "error_message", None):
            lines.append(Text(str(response.error_message), style="bold red"))

        for item in getattr(response, "content", None) or []:
            lines.append(_format_item(item))

        self.console.print(
            Panel(Group(*lines) if lines else Text("(empty)"), title=f"[{self._next()}] ◀ llm.response", border_style="yellow")
        )

    def tool_execute(self, name: str, arguments: dict) -> None:
        if not self.enabled:
            return
        head = Text()
        head.append(name, style="bold magenta")
        self.console.print(
            Panel(
                Group(head, _format_arguments(arguments)),
                title=f"[{self._next()}] ▶ tool.execute",
                border_style="magenta",
            )
        )

    def tool_result(self, name: str, status: str, content: Any) -> None:
        if not self.enabled:
            return
        style = "green" if status == "success" else "red"
        head = Text()
        head.append(name, style=f"bold {style}")
        head.append(f"  ({status})", style="dim")
        body = Group(head, _format_payload(content))
        self.console.print(Panel(body, title=f"[{self._next()}] ◀ tool.result", border_style=style))

    def error(self, err: Any) -> None:
        if not self.enabled:
            return
        self.console.print(Panel(Text(str(err), style="bold red"), title=f"[{self._next()}] error", border_style="red"))
