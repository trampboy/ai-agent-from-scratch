"""P4 — Session management（多轮对话短期记忆）。

自己实现提示（对照 demos/05_memory.py 的 A）：
  1) Session 至少要有 session_id、events、state（events 用来跨 run 恢复对话）
  2) BaseSessionManager：create / get / save 为抽象；get_or_create = get 或 create
  3) InMemorySessionManager：用 dict[str, Session] 做进程内存储即可
  4) create 时若 id 已存在 → ValueError；get 不存在 → None
  5) 不要改 scratch_agents/；Agent 接线在 agent.py，本文件只负责存取

Agent 接线提示（下一步，不在本文件）：
  run(session_id=...) → get_or_create → 把 session.events/state 拷进 context
  结束时把 context.events/state 写回 session → save
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Session(BaseModel):
    """跨多次 run() 保存的会话状态。字段可按需要增减，demo A 会读 session_id / events。"""

    session_id: str
    user_id: str | None = None
    events: list[Any] = Field(default_factory=list)
    state: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class BaseSessionManager(ABC):
    """存储抽象。子类实现后端；get_or_create 可在基类用 get+create 拼出来。"""

    @abstractmethod
    async def create(
        self,
        session_id: str,
        user_id: str | None = None,
    ) -> Session:
        raise NotImplementedError

    @abstractmethod
    async def get(self, session_id: str) -> Session | None:
        raise NotImplementedError

    @abstractmethod
    async def save(self, session: Session) -> None:
        raise NotImplementedError

    async def get_or_create(
        self,
        session_id: str,
        user_id: str | None = None,
    ) -> Session:
        # get → 没有则 create → 返回
        session = await self.get(session_id)
        if not session:
            session = await self.create(session_id)
        return session

class InMemorySessionManager(BaseSessionManager):
    """进程内实现。提示：__init__ 里 self._sessions: dict[str, Session] = {}。"""

    def __init__(self) -> None:
        # 初始化内存字典
        self.sessions: dict[str, Session] = {}

    async def create(
        self,
        session_id: str,
        user_id: str | None = None,
    ) -> Session:
        # TODO: 已存在则 ValueError；否则 new Session 并放入字典
        session = await self.get(session_id)
        if session:
            raise ValueError('该 session 已经存在')
        session = Session(session_id=session_id, user_id=user_id)
        self.sessions[session_id] = session
        return session

    async def get(self, session_id: str) -> Session | None:
        # TODO: dict.get
        return self.sessions.get(session_id)

    async def save(self, session: Session) -> None:
        # TODO: 写回字典；可选更新 updated_at
        session.updated_at = datetime.now()
        self.sessions[session.session_id] = session
