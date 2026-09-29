"""P3 — Callbacks (approval, search compression, etc.)."""

from __future__ import annotations

from typing import Any
from my_agent.rag import chunk_text, embed_texts, search_similar
from my_agent.types import ToolCall, ToolResult
import json

async def approval_callback(context, tool_call: ToolCall) -> Any:
    if not tool_call.name in ["delete_file"]:
        return None
    print(f"\n危险工具: {tool_call.name}")
    print(f"参数: {tool_call.arguments}")

    response = input("是否确认执行？(y/n): ").lower().strip()
    if response == "y":
        return None
    else:
        return f"已取消执行: {tool_call.name}"


async def search_compressor(context, tool_result) -> Any:
    if not tool_result.name == "search":
        return None
    # 将结果转换为字符串,不进行编码,中文原样保留
    result = json.dumps(tool_result.content[0], ensure_ascii=False)
    if len(result) < 2000:
        return None
    chunks = chunk_text(result, chunk_size=500, overlap=50)
    chunk_embeddings = embed_texts(chunks)
    for event in context.events:
        if isinstance(event, ToolCall) and event.tool_call_id == tool_result.tool_call_id:
            query = event.arguments["query"]
            similar_chunks = search_similar(query, chunks, chunk_embeddings, top_k=3)
            compressed = "\n\n".join([chunk["chunk"] for chunk in similar_chunks])
            return ToolResult(tool_call_id=tool_result.tool_call_id, name=tool_result.name, status="success", content=[compressed])
    return None
