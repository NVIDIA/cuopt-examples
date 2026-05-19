# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import datetime
import logging
import os
import re
import uuid
from collections.abc import AsyncGenerator, AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from nat.builder.builder import Builder
from nat.builder.framework_enum import LLMFrameworkEnum
from nat.builder.function_info import FunctionInfo
from nat.cli.register_workflow import register_function
from nat.data_models.api_server import (
    ChatRequest,
    ChatRequestOrMessage,
    ChatResponse,
    ChatResponseChunk,
    Usage,
    UserMessageContentRoleType,
)
from nat.data_models.component_ref import FunctionRef, LLMRef
from nat.data_models.function import FunctionBaseConfig
from nat.utils.type_converter import GlobalTypeConverter
from pydantic import Field

logger = logging.getLogger(__name__)

# Streaming tuning (not NAT workflow YAML keys — adjust here, not in config-deepagent.yml).
_STREAM_MAX_SEGMENT_CHARS = 48
_STREAM_PROGRESS_UPDATES = True


class DeepAgentConfig(FunctionBaseConfig, name="deepagent_fn"):
    """Langchain DeepAgents agent that delegates to subagents via create_deep_agent.

    Subagents are defined as separate NAT functions (``subagent_factory``)
    in the YAML ``functions:`` section and referenced here by name.
    """

    llm_name: LLMRef = Field(
        description="The name of the configured LLM to use for the orchestrator.",
    )
    description: str = Field(
        default="Orchestrator agent",
        description="Function description.",
    )
    skills_dir: list[Path] | Path | None = Field(
        default=None,
        description=(
            "Directory or list of directories (relative to cwd or absolute) whose "
            "skill sub-folders are merged into .skills/ in the sandbox."
        ),
    )
    agents_md_path: Path | None = Field(
        default=None,
        description="Path to AGENTS.md (relative to cwd or absolute) copied into the sandbox.",
    )
    skills: list[str] | None = Field(
        default=None,
        description=(
            "Skill paths passed to create_deep_agent (relative to sandbox). "
            "None = auto ([SANDBOX_SKILLS_DIR] if skills_dir resolved, else []). "
            "Explicit [] = no skills even if skills_dir exists."
        ),
    )
    memory: list[str] | None = Field(
        default=None,
        description=(
            "Memory file paths passed to create_deep_agent (relative to sandbox). "
            "None = auto ([SANDBOX_AGENTS_MD] if agents_md resolved, else []). "
            "Explicit [] = no memory even if AGENTS.md exists."
        ),
    )
    tools: list[str] = Field(
        default_factory=list,
        description="Additional tool names passed to create_deep_agent. Default [] = built-in backend tools only.",
    )
    subagents: list[FunctionRef] = Field(
        default_factory=list,
        description=(
            "References to sub_agent_factory functions defined in the YAML functions: section. "
            "Each is resolved via builder.get_function() at startup and yields a subagent dict "
            "passed to create_deep_agent(subagents=[...])."
        ),
    )
    workspace_dirs: list[Path] = Field(
        default_factory=list,
        description=(
            "Directories whose files are copied into the sandbox root at invocation time. "
            "Use for data files (CSVs, scripts) the agent should have access to."
        ),
    )
    system_prompt: str = Field(
        default="",
        description=(
            "System prompt for the orchestrator agent. "
            "Use for coordination instructions, delegation guidance, or output formatting. "
            "Empty string = no system prompt."
        ),
    )
    venv_path: Path | None = Field(
        default=None,
        description="Path to venv for sandbox (None = inherit_env only, e.g. in container).",
    )
    max_retries: int = Field(
        default=2,
        description="Max retry attempts for transient LLM failures (429, 5xx, timeouts).",
    )
    retry_backoff_factor: float = Field(
        default=2.0,
        description="Exponential backoff multiplier between retries.",
    )
    retry_initial_delay: float = Field(
        default=1.0,
        description="Initial delay in seconds before first retry.",
    )
    retry_max_delay: float = Field(
        default=120.0,
        description="Maximum delay cap in seconds between retries.",
    )
    strip_reasoning_pattern: str = Field(
        default=r"<think>.*?</think>\s*|<think>.*",
        description=(
            "Regex pattern (re.DOTALL) to strip from the final response. "
            "Matches are removed before returning to the caller. "
            "Set to empty string to disable stripping."
        ),
    )
@register_function(config_type=DeepAgentConfig, framework_wrappers=[LLMFrameworkEnum.LANGCHAIN])
async def deep_agent(config: DeepAgentConfig, builder: Builder):
    import psutil
    from deepagents import create_deep_agent
    from deepagents.backends.local_shell import LocalShellBackend
    from deepagents.middleware.memory import MemoryMiddleware
    from langchain.agents.middleware.model_retry import ModelRetryMiddleware

    from .utils import (
        SANDBOX_AGENTS_MD,
        SANDBOX_SKILLS_DIR,
        FixToolNamesMiddleware,
        ToolRetryMiddleware,
        kill_orphaned_children,
        populate_sandbox,
        resolve_skills_dirs,
        strip_pattern,
    )

    # resolve skills directories
    skills_src_dirs = resolve_skills_dirs(config.skills_dir)

    # resolve agents_md_path
    agents_md_src: Path | None = None
    if config.agents_md_path:
        candidate = Path(config.agents_md_path)
        if candidate.is_file():
            agents_md_src = candidate
        else:
            logger.warning("agents_md_path not found (cwd=%s): %s", Path.cwd(), candidate)

    logger.info("Resolved skills dirs: %s", skills_src_dirs or "(none)")
    logger.info("Resolved AGENTS.md: %s", agents_md_src or "(none)")

    # Instantiate LLM with NAT builder
    llm = await builder.get_llm(config.llm_name, wrapper_type=LLMFrameworkEnum.LANGCHAIN)

    # Resolve venv path if provided for use in sandbox
    env: dict[str, str] = {}
    if config.venv_path is not None:
        venv = Path(config.venv_path)
        env = {
            "PATH": f"{venv / 'bin'}:{os.environ.get('PATH', '')}",
            "VIRTUAL_ENV": str(venv),
        }

    # Resolve effective skills and memory paths used in agent configuration
    effective_skills = config.skills if config.skills is not None else ([SANDBOX_SKILLS_DIR] if skills_src_dirs else [])
    effective_memory = config.memory if config.memory is not None else ([SANDBOX_AGENTS_MD] if agents_md_src else [])

    # Workaround to strip reasoning patterns from the final response with minimax model
    strip_re = re.compile(config.strip_reasoning_pattern, re.DOTALL) if config.strip_reasoning_pattern else None

    @asynccontextmanager
    async def _agent_session(
        chat_request: ChatRequest,
    ) -> AsyncIterator[tuple[object, list]]:
        """Yield (agent, messages_dict_list) inside a sandbox; cleans up child processes on exit."""
        messages = [m.model_dump() for m in chat_request.messages]
        with TemporaryDirectory() as sandbox_dir:
            sandbox = Path(sandbox_dir)
            populate_sandbox(sandbox, skills_src_dirs, agents_md_src, config.workspace_dirs)
            backend = LocalShellBackend(
                root_dir=sandbox,
                virtual_mode=True,
                inherit_env=True,
                env=env,
            )
            sub_agent_dicts: list[dict] = []
            for ref in config.subagents:
                fn = await builder.get_function(ref)
                sa_dict = await fn.ainvoke(None)
                memory = sa_dict.pop("memory")
                sa_dict["middleware"].append(MemoryMiddleware(backend=backend, sources=memory))
                sub_agent_dicts.append(sa_dict)

            logger.info(
                "Resolved %d subagent(s): %s", len(sub_agent_dicts), [sa.get("name", "?") for sa in sub_agent_dicts]
            )

            middleware = [
                FixToolNamesMiddleware(),
                ToolRetryMiddleware(),
                ModelRetryMiddleware(
                    max_retries=config.max_retries,
                    backoff_factor=config.retry_backoff_factor,
                    initial_delay=config.retry_initial_delay,
                    max_delay=config.retry_max_delay,
                    jitter=True,
                    on_failure="continue",
                ),
            ]

            agent_kwargs: dict = dict(
                tools=config.tools,
                model=llm,
                backend=backend,
                middleware=middleware,
                subagents=sub_agent_dicts,
            )
            if config.system_prompt:
                agent_kwargs["system_prompt"] = config.system_prompt
            if effective_skills:
                agent_kwargs["skills"] = effective_skills
            if effective_memory:
                agent_kwargs["memory"] = effective_memory

            agent = create_deep_agent(**agent_kwargs)
            pre_children = {c.pid for c in psutil.Process().children(recursive=True)}
            try:
                yield agent, messages
            finally:
                kill_orphaned_children(pre_children)

    def _usage_for_content(chat_request: ChatRequest, content: str) -> Usage:
        prompt_tokens = sum(len(str(m.content).split()) for m in chat_request.messages)
        completion_tokens = len(content.split()) if content else 0
        return Usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )

    def _response_model(chat_request: ChatRequest) -> str:
        return (chat_request.model or "").strip() or "unknown-model"

    async def _single(chat_request_or_message: ChatRequestOrMessage) -> ChatResponse:
        """Non-streaming OpenAI chat completion (root JSON object, no ``value`` wrapper)."""
        chat_request = GlobalTypeConverter.get().convert(chat_request_or_message, to_type=ChatRequest)
        async with _agent_session(chat_request) as (agent, messages):
            agent_result = await agent.ainvoke({"messages": messages})
            result_messages = agent_result["messages"]
            content = result_messages[-1].content if result_messages else ""
            content = strip_pattern(content, strip_re)
        usage = _usage_for_content(chat_request, content)
        return ChatResponse.from_string(content, usage=usage, model=_response_model(chat_request))

    def _extract_text_content(content: object) -> str:
        if content is None:
            return ""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: list[str] = []
            for block in content:
                if isinstance(block, str):
                    parts.append(block)
                elif isinstance(block, dict) and block.get("type") == "text":
                    parts.append(str(block.get("text", "")))
                elif hasattr(block, "text"):
                    parts.append(str(block.text))
            return "".join(parts)
        return str(content)

    def _iter_stream_segments(text: str, max_chars: int) -> list[str]:
        if not text:
            return []
        if max_chars <= 0 or len(text) <= max_chars:
            return [text]
        segments: list[str] = []
        start = 0
        length = len(text)
        while start < length:
            end = min(start + max_chars, length)
            if end < length and text[end - 1] not in " \n\t":
                boundary = text.rfind(" ", start, end)
                if boundary > start:
                    end = boundary + 1
            segment = text[start:end]
            if segment:
                segments.append(segment)
            start = end if end > start else start + 1
        return segments

    def _namespace_tuple(ns: object) -> tuple:
        if isinstance(ns, str):
            return (ns,)
        if ns is None:
            return ()
        return tuple(ns)

    def _is_subagent_namespace(ns: tuple) -> bool:
        return any(isinstance(s, str) and s.startswith("tools:") for s in ns)

    def _message_token_text(token: object) -> str:
        if getattr(token, "type", None) not in ("ai", None):
            return ""
        if getattr(token, "tool_call_chunks", None):
            return ""
        return _extract_text_content(getattr(token, "content", None))

    def _progress_from_update(chunk: dict) -> str | None:
        ns = _namespace_tuple(chunk.get("ns"))
        if _is_subagent_namespace(ns):
            return None
        data = chunk.get("data")
        if not isinstance(data, dict):
            return None
        if "tools" in data:
            return "Running tools…\n"
        if "model_request" in data and not ns:
            return None
        return None

    async def _stream_llm_chunks(agent: object, messages: list) -> AsyncGenerator[str, None]:
        """Yield main-agent assistant text (LLM tokens and optional progress lines)."""

        async def _yield_from_astream_events() -> AsyncGenerator[str, None]:
            astream_events = getattr(agent, "astream_events", None)
            if astream_events is None:
                return
            async for event in astream_events({"messages": messages}, version="v2"):
                if not isinstance(event, dict) or event.get("event") != "on_chat_model_stream":
                    continue
                data = event.get("data") or {}
                llm_chunk = data.get("chunk")
                text = _message_token_text(llm_chunk)
                if text:
                    yield text

        emitted = False
        try:
            async for text in _yield_from_astream_events():
                emitted = True
                yield text
        except Exception:
            logger.debug("astream_events token stream unavailable", exc_info=True)

        if emitted:
            return

        stream_modes: list[str] = ["messages"]
        if _STREAM_PROGRESS_UPDATES:
            stream_modes.append("updates")

        try:
            astream = agent.astream(
                {"messages": messages},
                stream_mode=stream_modes,
                subgraphs=True,
                version="v2",
            )
        except TypeError:
            astream = agent.astream(
                {"messages": messages},
                stream_mode="messages",
                subgraphs=True,
            )

        async for chunk in astream:
            if not isinstance(chunk, dict):
                continue
            chunk_type = chunk.get("type")
            ns = _namespace_tuple(chunk.get("ns"))

            if chunk_type == "updates" and _STREAM_PROGRESS_UPDATES:
                if _is_subagent_namespace(ns):
                    continue
                progress = _progress_from_update(chunk)
                if progress:
                    yield progress
                continue

            if chunk_type != "messages":
                continue
            if _is_subagent_namespace(ns):
                continue
            payload = chunk.get("data")
            if not isinstance(payload, (list, tuple)) or len(payload) < 1:
                continue
            token = payload[0]
            text = _message_token_text(token)
            if text:
                yield text

    async def _stream(chat_request_or_message: ChatRequestOrMessage) -> AsyncGenerator[ChatResponseChunk, None]:
        """OpenAI-style SSE chunks via NAT ``ChatResponseChunk`` (``data:`` lines when framed by NAT)."""
        chat_request = GlobalTypeConverter.get().convert(chat_request_or_message, to_type=ChatRequest)
        response_model = _response_model(chat_request)
        stream_id = str(uuid.uuid4())
        created = datetime.datetime.now(datetime.UTC)
        assembled: list[str] = []

        async with _agent_session(chat_request) as (agent, messages):
            yield ChatResponseChunk.create_streaming_chunk(
                "",
                id_=stream_id,
                created=created,
                model=response_model,
                role=UserMessageContentRoleType.ASSISTANT,
            )
            try:
                async for text in _stream_llm_chunks(agent, messages):
                    assembled.append(text)
                    for segment in _iter_stream_segments(text, _STREAM_MAX_SEGMENT_CHARS):
                        yield ChatResponseChunk.create_streaming_chunk(
                            segment,
                            id_=stream_id,
                            created=created,
                            model=response_model,
                        )
            except Exception:
                logger.exception("Token streaming failed; falling back to buffered completion")
                agent_result = await agent.ainvoke({"messages": messages})
                result_messages = agent_result["messages"]
                content = result_messages[-1].content if result_messages else ""
                content = strip_pattern(content, strip_re)
                assembled.clear()
                assembled.append(content)
                for segment in _iter_stream_segments(content, _STREAM_MAX_SEGMENT_CHARS):
                    yield ChatResponseChunk.create_streaming_chunk(
                        segment,
                        id_=stream_id,
                        created=created,
                        model=response_model,
                    )

            content = strip_pattern("".join(assembled), strip_re)

        usage = _usage_for_content(chat_request, content)
        yield ChatResponseChunk.create_streaming_chunk(
            "",
            id_=stream_id,
            created=created,
            model=response_model,
            finish_reason="stop",
            usage=usage,
        )

    yield FunctionInfo.create(
        single_fn=_single,
        stream_fn=_stream,
        description=config.description,
    )
