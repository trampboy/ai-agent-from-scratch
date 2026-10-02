"""P0 — Tool schema helpers."""

from __future__ import annotations

from typing import Any, Callable, Dict
import inspect
from typing import get_type_hints, get_origin, get_args


def function_to_input_schema(func: Callable) -> Dict[str, Any]:
    """Build JSON-schema parameters from a function signature + docstring."""
    try:
        hints = get_type_hints(func)
    except Exception:
        hints = {
            name: param.annotation
            for name, param in inspect.signature(func).parameters.items()
            if param.annotation is not inspect.Parameter.empty
        }

    signature = inspect.signature(func)
    parameters = {}
    required = []
    for name, param in signature.parameters.items():
        # 跳过上下文参数
        if name == "context":
            continue
        # 跳过可变参数
        if param.kind in [inspect.Parameter.VAR_KEYWORD, inspect.Parameter.VAR_POSITIONAL]:
            continue
        # 如果默认参数为空，则认为是必填参数
        if param.default is inspect.Parameter.empty:
            required.append(name)

        hint = hints.get(name)
        if hint is str:
            prop: Dict[str, Any] = {"type": "string"}
        elif hint is int:
            prop = {"type": "integer"}
        elif hint is float:
            prop = {"type": "number"}
        elif hint is bool:
            prop = {"type": "boolean"}
        elif hint is list or get_origin(hint) is list:
            prop = {"type": "array"}
            args = get_args(hint) if hint is not list else ()
            if args:
                item_type = args[0]
                if item_type is str:
                    prop["items"] = {"type": "string"}
                elif item_type is int:
                    prop["items"] = {"type": "integer"}
                elif hasattr(item_type, "model_json_schema"):
                    prop["items"] = item_type.model_json_schema()
        elif hasattr(hint, "model_json_schema"):
            prop = hint.model_json_schema()
        elif hint is dict or get_origin(hint) is dict:
            prop = {"type": "object"}
        else:
            prop = {"type": "string"}

        prop["description"] = f"Parameter: {name}"
        parameters[name] = prop
    return {
        "type": "object",
        "properties": parameters,
        "required": required,
    }


# {
#   "type": "function",
#   "function": {
#     "name": "calculator",
#     "description": "Perform basic arithmetic operations.",
#     "parameters": {
#       "type": "object",
#       "properties": {
#         "operator": { "type": "string", "description": "..." },
#         "first_number": { "type": "number" },
#         "second_number": { "type": "number" }
#       },
#       "required": ["operator", "first_number", "second_number"]
#     }
#   }
# }
def format_tool_definition(
    name: str,
    description: str,
    parameters: Dict[str, Any],
) -> Dict[str, Any]:
    """Build an OpenAI-style tool definition dict."""
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": parameters,
        }
    }
