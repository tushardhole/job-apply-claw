"""Core agent loop that orchestrates LLM reasoning with browser tools.

The agent repeatedly:
1. Asks the LLM to decide the next action (given tool definitions).
2. Executes the chosen tool via ``BrowserToolsPort``.
3. Feeds the tool result back to the LLM.
4. Stops when the LLM calls the ``done`` tool or the step limit is hit.
"""

from __future__ import annotations

import json
from typing import Any

from domain.models import (
    AgentResult,
    AgentStep,
    AgentTask,
    LLMToolResponse,
    ToolCall,
)
from domain.ports import BrowserToolsPort, LLMClientPort, LoggerPort
from domain.prompts import SYSTEM_PROMPT, build_apply_task_prompt


class BrowserAgent:
    """Implements ``BrowserAgentPort``."""

    def __init__(
        self,
        *,
        llm: LLMClientPort,
        browser_tools: BrowserToolsPort,
        logger: LoggerPort,
    ) -> None:
        self._llm = llm
        self._tools = browser_tools
        self._logger = logger

    async def execute_task(self, task: AgentTask) -> AgentResult:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": self._build_initial_message(task)},
        ]
        steps: list[AgentStep] = []
        tool_defs = self._tools.available_tools()

        for step_num in range(task.max_steps):
            response: LLMToolResponse = await self._llm.complete_with_tools(
                messages=messages,
                tools=tool_defs,
            )

            if not response.tool_calls:
                if response.text:
                    messages.append({"role": "assistant", "content": response.text})
                continue

            for tc in response.tool_calls:
                if tc.name == "done":
                    return AgentResult(
                        status=tc.arguments.get("status", "success"),
                        reason=tc.arguments.get("reason"),
                        data=tc.arguments,
                        steps_taken=steps,
                    )

                result_text = await self._tools.execute(tc)

                step = AgentStep(
                    step_number=step_num,
                    tool_name=tc.name,
                    tool_args=tc.arguments,
                    tool_result=result_text,
                )
                steps.append(step)

                self._logger.info(
                    "agent_step",
                    step=step_num,
                    tool=tc.name,
                    result_preview=result_text[:120],
                )

                messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{
                        "id": f"call_{step_num}_{tc.name}",
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments),
                        },
                    }],
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": f"call_{step_num}_{tc.name}",
                    "content": result_text,
                })

        self._logger.warning(
            "agent_max_steps_exceeded",
            max_steps=task.max_steps,
        )
        return AgentResult(
            status="failed",
            reason=f"Agent exceeded maximum steps ({task.max_steps})",
            steps_taken=steps,
        )

    @staticmethod
    def _build_initial_message(task: AgentTask) -> str:
        ctx = task.context
        profile_data = ctx.get("profile")
        if profile_data:
            from domain.models import UserProfile
            profile = UserProfile(
                full_name=profile_data.get("full_name", ""),
                email=profile_data.get("email", ""),
                phone=profile_data.get("phone"),
                address=profile_data.get("address"),
            )
            return build_apply_task_prompt(
                job_url=ctx.get("job_url", task.objective),
                company_name=ctx.get("company", "Unknown"),
                job_title=ctx.get("job_title", ""),
                profile=profile,
                resume_available=ctx.get("resume_available", False),
                cover_letter_available=ctx.get("cover_letter_available", False),
                debug=task.debug,
            )
        return task.objective
