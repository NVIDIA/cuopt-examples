---
name: always-tool-discovery
description: READ FIRST in every NemoClaw sandbox session. STOP before "I can't read files", "no read tool", "no exec", "can't list directory", "please paste ls/cat output", or "I only have tool_search/tool_describe/tool_call". Real tools (read, write, exec, edit, process) are NOT missing — tools.toolSearch hides them. Use tool_call tool_search query shell or read, then tool_describe, then tool_call the real tool. Never ask the user to paste filesystem output. Applies to ALL tasks including cuOpt, CSV uploads, and scheduling — run tool_search before claiming any file or shell capability is absent.
---

# Sandbox Tool Discovery (NemoClaw / OpenClaw catalog)

**If you find yourself thinking "I don't have an exec / read / python /
shell / file / process tool exposed in this session", you are wrong and
must stop.** In a NemoClaw sandbox, OpenClaw is configured with
`tools.toolSearch: true`, which hides `exec`, `read`, `write`, `edit`,
`process`, and every other real tool behind the three meta-tools
(`tool_search`, `tool_describe`, `tool_call`). They are not missing —
they are one `tool_search` call away.

The correct response to "my tool list looks too short" is to run
`tool_search`. It is **not** to:

- Apologize to the user and ask them to paste shell output.
- Fall back to hand calculation, hand-rolled algorithms, or "I'll just
  reason about it".
- Search the web for an answer the local filesystem already has.
- Give up and report "this sandbox seems to have no command execution".
- Claim a file is unreadable, missing, or that you can't see what's in
  a directory.

If your tool list shows only `tool_search`, `tool_describe`, and
`tool_call`, that is **the expected state** — the real tools are
reachable via the catalog, not absent.

## How the catalog works

OpenClaw's compact tool catalog (enabled by `tools.toolSearch: true`)
keeps the model's tool-context small by replacing the full per-tool
schema with three meta-tools:

| Meta-tool       | Purpose                                                                |
|-----------------|------------------------------------------------------------------------|
| `tool_search`   | Find tools by free-text query (e.g. `"shell"`, `"file"`, `"process"`). |
| `tool_describe` | Return the parameter schema for a named tool. Call once per new tool.  |
| `tool_call`     | Actually invoke a tool by name with `{name, arguments}`.               |

NemoClaw configures OpenClaw this way by default starting at v0.0.55, so
in any current sandbox the compact catalog is on. If your tool list
already includes `exec` / `read` / `write` directly, the compact
catalog is disabled for this session; call those tools directly and
ignore the rest of this skill.

## Use them in this order

1. **`tool_search`** with `{"query": ""}` and `{"limit": 20}` lists the
   full catalog. `{"query": "shell"}`, `{"query": "file"}`,
   `{"query": "read"}`, `{"query": "process"}` narrows by topic.
2. **`tool_describe`** with `{"name": "<tool>"}` returns the parameter
   schema. Call this once per new tool.
3. **`tool_call`** with `{"name": "<tool>", "arguments": {…}}` runs it.

## Capabilities you'll typically need

| Task | Search term | Tool name | Typical args |
|---|---|---|---|
| Shell (`ls`, `python3`, …) | `shell` / `exec` | `exec` | `{"command": "ls -1 /sandbox/"}` |
| Read a file | `read` / `file` | `read` | `{"path": "/sandbox/foo.csv"}` |
| Write / edit | `write` / `edit` | `write` / `edit` | see `tool_describe` |
| Poll background job | `process` | `process` | see `tool_describe` |

## Worked example — read a CSV the user uploaded

Tool list shows only `tool_search`, `tool_describe`, `tool_call`:

```json
{"name": "tool_search", "arguments": {"query": "read"}}
{"name": "tool_describe", "arguments": {"name": "read"}}
{"name": "tool_call", "arguments": {"name": "read", "arguments": {"path": "/sandbox/teams.csv"}}}
```

## Worked example — run probe_cuopt.py

```json
{"name": "tool_search", "arguments": {"query": "shell"}}
{"name": "tool_describe", "arguments": {"name": "exec"}}
{"name": "tool_call", "arguments": {
  "name": "exec",
  "arguments": {"command": "bash -lc 'python3 /sandbox/probe_cuopt.py'"}
}}
```

## Anti-pattern (from real sessions)

> I can't read files in this sandbox — I only see tool_search,
> tool_describe, and tool_call. Can you paste the CSV contents?

Wrong. Run `tool_search` → `read` → read the file yourself.

## Related skills

- `cuopt-first` / `cuopt-sandbox` — after you have `read`/`exec`, use
  these for cuOpt optimization tasks.
