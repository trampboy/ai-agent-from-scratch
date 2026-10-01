"""P4 — Long-term / task memory."""

from __future__ import annotations
import uuid
from pydantic import BaseModel, Field

from typing import Any, List

from my_agent import LlmClient
from my_agent import Message, ToolCall, ToolResult
import chromadb
from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

class TaskMemory(BaseModel):
    task_summary: str = Field(description="题目/任务在问什么")
    approach: str = Field(description="用了什么方法、工具、步骤")
    final_answer: str=Field(description="Agent 最终提交的答案")
    is_correct: bool=Field(description="答案是否正确")
    error_analysis: str | None = Field(description="失败原因；做对则为 None")

    def to_embedding_text(self) -> str:
        return f"Task: {self.task_summary}"

EXTRACT_TASK_MEMORY_PROMPT = """Analyze the following execution history and extract a structured task memory.

Execution History:
{execution_history}

Extract:
- task_summary: What the problem asked
- approach: Methods and tools used to solve it
- final_answer: The agent's submitted answer
- is_correct: Whether the answer was correct (true or false)
- error_analysis: If incorrect, explain why; otherwise leave null
"""

DUPLICATE_CHECK_PROMPT="""Compare the new memory against existing memories to determine if it's a duplicate.

Existing memories:
{existing_memories}

New memory:
{new_memory}

Respond with one of:
- ADD: This is new information that should be stored
- SKIP: Similar information already exists, no need to store

Judgment criteria:
- Same problem with different approach or different result counts as new information
- Same problem with same approach and same result is a duplicate
"""

class TaskMemoryManager:
    client: LlmClient

    def __init__(self, llm_client: LlmClient) -> None:
        self.client = llm_client
        self.chroma = chromadb.Client()
        self.collection = self.chroma.get_or_create_collection(
            name="task_memories",
            embedding_function=OpenAIEmbeddingFunction(model_name="text-embedding-3-small")
        )

    async def save(self, context) -> None:
        if not context.events:
            return None
        lines = []
        for event in context.events:
            if isinstance(event, Message):
                lines.append(f"[{event.role}]: {event.content}")
            elif isinstance(event, ToolCall):
                lines.append(f"[Tool Call]: {event.name}({event.arguments})")
            elif isinstance(event, ToolResult):
                preview = str(event.content[0])[:500] if event.content else ""
                lines.append(f"[Tool Result]: {event.name} -> {preview}")
        history = "\n".join(lines)
        prompt = EXTRACT_TASK_MEMORY_PROMPT.format(execution_history=history)
        taskMemory: TaskMemory = await self.client.ask(prompt=prompt, response_format=TaskMemory)

        query_result = self.collection.query(query_texts=[taskMemory.to_embedding_text()], n_results=3)
        if query_result["metadatas"][0]:
            return None

        metadata = taskMemory.model_dump()
        metadata = {k: ("" if v is None else v)for k,v in metadata.items()}
        print('metadata:', metadata)
        memory_id = str(uuid.uuid4())
        self.collection.add(ids=[memory_id], documents=[taskMemory.to_embedding_text()], metadatas=[metadata])
        return memory_id


    async def search(self, query: str, top_k: int = 3) -> List[Any]:
        query_result = self.collection.query(query_texts=[query], n_results=top_k)
        metadatas = query_result["metadatas"][0]
        if not metadatas:
            return None
        result = []
        for metadata in metadatas:
            result.append(TaskMemory(**metadata))
        return result
