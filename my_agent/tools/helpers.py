"""P0 — Tool schema helpers."""

from __future__ import annotations

from typing import Any, Callable, Dict
import inspect


def function_to_input_schema(func: Callable) -> Dict[str, Any]:
    """Build JSON-schema parameters from a function signature + docstring."""
    signature = inspect.signature(func)
    parameters = {}
    for name, param in signature.parameters.items():
        if name == "context":
            continue
        if param.annotation is str:
            json_type = "string"
        elif param.annotation is int:
            json_type = "integer"
        elif param.annotation is float:
            json_type = "number"
        elif param.annotation is bool:
            json_type = "boolean"
        elif param.annotation is list:
            json_type = "array"
        elif param.annotation is dict:
            json_type = "object"
        else:
            json_type = "string"
        parameters[name] = { "type": json_type, "description": f"Parameter: {name}", }
        
    required = []
    if param.default is inspect.Parameter.empty:
        required.append(name)
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
