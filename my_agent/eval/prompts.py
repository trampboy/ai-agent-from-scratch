"""P8 — Evaluation prompts / judges."""

from __future__ import annotations

# 回答相关性提示
ANSWER_RELEVANCY_PROMPT = """Evaluate whether the agent's answer is relevant to the question asked.

Question: {question}
Agent's Answer: {answer}

Rate the relevancy on a scale of 1-5:
1 - Completely irrelevant
2 - Slightly relevant
3 - Somewhat relevant
4 - Mostly relevant
5 - Highly relevant

Provide your rating and a brief explanation."""

# 引用可靠性提示
CITATION_RELIABILITY_PROMPT = """Evaluate whether the agent's citations and sources are reliable.

Question: {question}
Agent's Answer: {answer}
Sources Used: {sources}

Check:
1. Are the sources real and accessible?
2. Do the sources support the claims made?
3. Are the sources authoritative for the topic?

Rate reliability on a scale of 1-5 and explain."""


# 要求符合提示
REQUIREMENT_COMPLIANCE_PROMPT = """Evaluate whether the agent's answer complies with the requirements.

Original Question: {question}
Requirements: {requirements}
Agent's Answer: {answer}

Check if the answer:
1. Addresses all parts of the question
2. Follows the specified format
3. Meets any constraints mentioned

Rate compliance on a scale of 1-5 and explain."""

# 评价系统提示
EVALUATION_SYSTEM_PROMPT = """You are an evaluation judge for AI agent responses.
Provide fair, consistent, and detailed evaluations.
Always explain your reasoning."""
