# AI Frame

A lightweight, single-file Python CLI for managing Claude Code sessions across projects. It reduces context window usage and token costs by persisting project knowledge locally, and uses a generated master system prompt to enforce consistent coding standards in every session.

---

## The Problem

Every new Claude Code session starts blank. You repeat yourself — re-explaining architecture, conventions, current state, and recent decisions — burning tokens and wasting time. Over many sessions this compounds significantly.

## The Solution

AI Frame does three things:

1. **Generates a `CLAUDE.md`** master system prompt tailored to your project by asking targeted questions during initialisation. Claude Code reads this file automatically in every session.

2. **Maintains local context files** (`.ai-frame/`) that capture architecture notes, decisions, and session summaries — small, human-readable markdown files you curate over time.

3. **Provides session commands** to start a session with a pre-built briefing, and end a session by recording what was accomplished, updating progress state, and logging decisions.

---

## File Structure

```
ai-frame/                    ← This repository (one file)
└── ai_frame.py              ← The entire CLI

your-project/                ← Your actual coding project
├── CLAUDE.md                ← Generated master system prompt (auto-read by Claude Code)
└── .ai-frame/
    ├── config.json          ← Project metadata (auto-generated)
    ├── progress.md          ← Current status, in-progress work, next tasks  ← EDIT REGULARLY
    ├── architecture.md      ← System design, components, data flow          ← EDIT AS DESIGN CHANGES
    ├── decisions.md         ← Log of architectural and design decisions      ← APPEND WHEN DECIDED
    └── sessions/
        ├── 2025-01-15.md    ← Session summary (auto-generated)
        └── 2025-01-16.md
```

---

## Quick Start

### 1. Get the script

```bash
git clone https://github.com/irmakh/ai-coding-framework.git
# or just download ai_frame.py anywhere convenient
```

### 2. Initialise your project

```bash
cd your-project
python /path/to/ai_frame.py init
```

The wizard asks about your stack, architecture, testing strategy, coding standards, constraints, and more. It generates:

- `CLAUDE.md` — master system prompt, loaded by Claude Code automatically
- `.ai-frame/config.json` — project metadata
- `.ai-frame/progress.md` — progress tracker (fill in after init)
- `.ai-frame/architecture.md` — architecture doc (fill in after init)
- `.ai-frame/decisions.md` — decision log with first entry

### 3. Start a session

```bash
python /path/to/ai_frame.py start
```

Prints a formatted briefing: current progress, recent sessions, project config. Open Claude Code — `CLAUDE.md` loads automatically. Optionally tell Claude:

> "Read `.ai-frame/progress.md` and the latest file in `.ai-frame/sessions/` to get up to speed."

### 4. End a session

```bash
python /path/to/ai_frame.py end
```

Records what you accomplished, any decisions made, next tasks, and blockers. Optionally updates `progress.md` and `decisions.md`.

---

## All Commands

```
python ai_frame.py <command> [options]
```

| Command | Description |
|---------|-------------|
| `init` | Wizard: generate `CLAUDE.md` and `.ai-frame/` in a project |
| `start` | Print session briefing, create today's session file |
| `end` | Record session summary, update progress and decisions |
| `status` | Compact project status overview |
| `update` | Interactively append content to a context file |
| `context` | Build a compressed context snapshot from `.ai-frame/` files |

### Global option

```
--project-dir PATH, -d PATH    Target project directory (default: current directory)
```

### `context`-specific options

```
--output FILE, -o FILE         Write to file instead of stdout
--compact, -c                  Strip placeholder comments and empty sections
--sections LIST, -s LIST       Comma-separated subset: config, progress, architecture, decisions, sessions
```

### Examples

```bash
# Initialise a project in a different directory
python ai_frame.py init -d ~/projects/my-api

# Start/end session for a project elsewhere
python ai_frame.py start -d ~/projects/my-api
python ai_frame.py end   -d ~/projects/my-api

# Get a token count estimate
python ai_frame.py context --compact 2>&1 | tail -1
# ~1,847 estimated tokens

# Build a context file to paste into another LLM interface
python ai_frame.py context --compact -o context.md

# Only include progress and recent sessions
python ai_frame.py context -s progress,sessions
```

---

## Recommended Workflow

```
Session start
─────────────────────────────────────────────────────────────
1. python ai_frame.py start        ← see what's happening
2. Open project in Claude Code     ← CLAUDE.md loads automatically
3. Tell Claude to read .ai-frame/progress.md if needed

During session
─────────────────────────────────────────────────────────────
- Work normally in Claude Code
- Note any significant decisions
- python ai_frame.py update        ← if you need to update context mid-session

Session end
─────────────────────────────────────────────────────────────
1. python ai_frame.py end          ← record accomplishments and next tasks
2. git commit .ai-frame/           ← persist context alongside code changes
```

---

## Using in VSCode

Claude Code's VSCode extension reads `CLAUDE.md` automatically, just like the CLI.

Run the scripts from VSCode's integrated terminal (`Ctrl+` `` ` ``). To make them one-key accessible, add to `.vscode/tasks.json`:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "AI Frame: Start Session",
      "type": "shell",
      "command": "python /path/to/ai_frame.py start",
      "presentation": { "reveal": "always", "panel": "shared" }
    },
    {
      "label": "AI Frame: End Session",
      "type": "shell",
      "command": "python /path/to/ai_frame.py end",
      "presentation": { "reveal": "always", "panel": "shared" }
    }
  ]
}
```

Run via `Ctrl+Shift+P` → "Tasks: Run Task" → select the task.

---

## Keeping Context Lean

| File | Strategy |
|------|----------|
| `progress.md` | Replace, don't append. Keep only the current "Next Up" and "Blockers". |
| `architecture.md` | High-level only. Link to code files rather than copying code into the doc. |
| `decisions.md` | Move old entries to `decisions_archive.md` once no longer actively relevant. |
| `sessions/` | Only the last 2–3 sessions matter. Delete or archive older ones. |
| `CLAUDE.md` | Bullet points, not prose. Rarely needs to exceed 100–150 lines. |

---

## Multiple Projects

Each project has its own `CLAUDE.md` and `.ai-frame/`. Use `-d` to target any project:

```bash
python ~/tools/ai_frame.py start -d ~/projects/my-api
python ~/tools/ai_frame.py start -d ~/projects/my-cli
```

---

## Requirements

- Python 3.10+
- No external dependencies — standard library only

---

## Tips

- **Commit `.ai-frame/`** to version control alongside your code.
- **`CLAUDE.md` is the highest-leverage file.** 10 minutes refining it saves multiples across future sessions.
- **Session files are searchable history.** `grep -r "auth" .ai-frame/sessions/` finds when something was decided.
- **For new team members**, point them to `.ai-frame/` before their first session — instant project context.
