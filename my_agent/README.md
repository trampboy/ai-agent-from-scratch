# my_agent — 教学复刻工作区

对照《Build an AI Agent from Scratch》手写完整 Agent。实现写在 `my_agent/`，练习时不要改 `scratch_agents/`。

## 纪律

- 写某一 Phase 时，不要边看 `scratch_agents/*.py` 边写。
- 卡住超过约 30 分钟，再打开对应章的 `notebooks/chXX/` 快照；优先看快照，而不是最终包。
- 该 Phase 的 demo **退出码为 0** 才算完成。

## Phase 清单

| Phase | 内容 | 验收 |
|------|------|------|
| **P0** | `types`、`llm`、`tools/base` + `helpers` + `calculator` | `demos/01_llm_and_tools.py` |
| **P1** | `context`、`agent` ReAct 循环 | `demos/02_react_calc.py` |
| **P2** | `search`（可选 `mcp`） | `demos/03_search_agent.py` |
| **P3** | `rag`、`file_tools`、`callbacks` | `demos/04_rag_files.py` |
| **P4** | `memory/*`、`memory_tool`、工具确认 | `demos/05_memory.py` |
| **P5** | `planning` | `demos/06_planning.py` |
| **P6** | `code_execution`、`skills` | `demos/07_code_skills.py` |
| **P7** | `workflows`、`transfer`、`agent_tool`、`remote`、`a2a_server` | `demos/08_multi_agent.py` |
| **P8** | `eval` | `demos/09_eval.py` |

## 运行 demo

```bash
uv run python my_agent/demos/01_llm_and_tools.py
```

## 模型建议

日常迭代优先用 `deepseek/deepseek-chat`（省钱）。要对齐书本示例或跑 GAIA 时，再切回 OpenAI。

可用环境变量覆盖默认模型：

```bash
export MY_AGENT_MODEL=deepseek/deepseek-chat
```

## 建议动手顺序（P0）

1. `tools/calculator.py`
2. `tools/helpers.py` + `tools/base.py`
3. `llm.py`（补全 `types.Event` 可穿插）
4. 跑通 `01_llm_and_tools.py` 后再进 P1（`context.py` + `agent.py`）
