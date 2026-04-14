#!/usr/bin/env python3
"""
AI Frame — All-in-one CLI for Claude Code project context management.

Commands:
    init      Initialise a project: generate CLAUDE.md and .ai-frame/ structure
    start     Print a session briefing and create today's session file
    end       Record what was accomplished and update context files
    status    Print a compact project status overview
    update    Interactively append content to a context file
    context   Build a compressed context snapshot from .ai-frame/ files

Usage:
    python ai_frame.py init    [--project-dir PATH]
    python ai_frame.py start   [--project-dir PATH]
    python ai_frame.py end     [--project-dir PATH]
    python ai_frame.py status  [--project-dir PATH]
    python ai_frame.py update  [--project-dir PATH]
    python ai_frame.py context [--project-dir PATH] [--output FILE] [--compact] [--sections LIST]
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from textwrap import dedent

# ─── Terminal colours ─────────────────────────────────────────────────────────

CYAN   = "\033[96m"
YELLOW = "\033[93m"
GREEN  = "\033[92m"
RED    = "\033[91m"
RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"

# ═══════════════════════════════════════════════════════════════════════════════
# SHARED UTILITIES
# ═══════════════════════════════════════════════════════════════════════════════

def separator(char: str = "─", width: int = 60) -> str:
    return f"{DIM}{char * width}{RESET}"


def header(text: str) -> None:
    width = 60
    print(f"\n{CYAN}{'─' * width}{RESET}")
    print(f"{BOLD}{CYAN}  {text}{RESET}")
    print(f"{CYAN}{'─' * width}{RESET}\n")


def load_config(ai_frame_dir: Path) -> dict:
    cfg_path = ai_frame_dir / "config.json"
    if not cfg_path.exists():
        return {}
    try:
        return json.loads(cfg_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def read_file_safe(path: Path, max_lines: int = 0) -> str:
    if not path.exists():
        return "_File not found._"
    text = path.read_text(encoding="utf-8").strip()
    if max_lines:
        lines = text.splitlines()
        if len(lines) > max_lines:
            text = "\n".join(lines[:max_lines]) + f"\n... ({len(lines) - max_lines} more lines)"
    return text or "_Empty._"


def latest_sessions(sessions_dir: Path, n: int = 3) -> list[Path]:
    files = sorted(sessions_dir.glob("*.md"), reverse=True)
    return files[:n]


def resolve_dirs(project_dir_arg: str, require_init: bool = True) -> tuple[Path, Path]:
    project_dir  = Path(project_dir_arg).resolve()
    ai_frame_dir = project_dir / ".ai-frame"
    if require_init and not ai_frame_dir.exists():
        print(
            f"{RED}Error:{RESET} No .ai-frame/ directory found in {project_dir}.\n"
            f"  Run {CYAN}python ai_frame.py init{RESET} first."
        )
        sys.exit(1)
    return project_dir, ai_frame_dir

# ═══════════════════════════════════════════════════════════════════════════════
# INIT — templates & question definitions
# ═══════════════════════════════════════════════════════════════════════════════

QUESTIONS = [
    {
        "key": "project_name",
        "label": "Project name",
        "type": "text",
    },
    {
        "key": "description",
        "label": "One-sentence description of what this project does",
        "type": "text",
    },
    {
        "key": "project_type",
        "label": "Project type",
        "type": "choice",
        "choices": [
            "web_app", "api_service", "cli_tool", "library",
            "data_pipeline", "mobile_app", "desktop_app", "other",
        ],
    },
    {
        "key": "language",
        "label": "Primary programming language",
        "type": "text",
        "placeholder": "e.g. Python, TypeScript, Go, Rust",
    },
    {
        "key": "runtime_version",
        "label": "Runtime / version",
        "type": "text",
        "optional": True,
        "placeholder": "e.g. Python 3.12, Node 20, Go 1.22  (leave blank to skip)",
    },
    {
        "key": "frameworks",
        "label": "Framework(s) in use",
        "type": "text",
        "optional": True,
        "placeholder": "e.g. FastAPI, React, Django  (leave blank if none)",
    },
    {
        "key": "architecture",
        "label": "Architecture style",
        "type": "choice",
        "choices": [
            "monolith", "microservices", "serverless", "mvc",
            "clean_architecture", "domain_driven_design",
            "event_driven", "layered", "other",
        ],
    },
    {
        "key": "testing_strategy",
        "label": "Testing strategy",
        "type": "choice",
        "choices": [
            "tdd", "unit_tests_only", "unit_and_integration",
            "e2e_focused", "bdd", "mixed", "minimal", "none",
        ],
    },
    {
        "key": "code_style",
        "label": "Code style / linting standard",
        "type": "text",
        "optional": True,
        "placeholder": "e.g. PEP8+Black, Airbnb ESLint, Google style, none",
    },
    {
        "key": "current_phase",
        "label": "Current project phase",
        "type": "choice",
        "choices": [
            "planning", "early_development", "active_development",
            "stabilisation", "testing", "maintenance", "refactoring",
        ],
    },
    {
        "key": "priorities",
        "label": "Top priorities (comma-separated)",
        "type": "text",
        "placeholder": "e.g. correctness, performance, readability, rapid iteration",
    },
    {
        "key": "constraints",
        "label": "Hard constraints or rules to always follow",
        "type": "text",
        "optional": True,
        "placeholder": "e.g. no external APIs, GDPR compliant, offline-first",
    },
    {
        "key": "avoid",
        "label": "Patterns / approaches to AVOID",
        "type": "text",
        "optional": True,
        "placeholder": "e.g. global mutable state, deep inheritance, sync I/O in hot paths",
    },
    {
        "key": "team_size",
        "label": "Team size",
        "type": "choice",
        "choices": ["solo", "2-3_people", "4-8_people", "8+_people"],
    },
    {
        "key": "extra_context",
        "label": "Anything else Claude should always know about this project",
        "type": "text",
        "optional": True,
        "placeholder": "e.g. integrates with legacy system, security-sensitive domain",
    },
]

CLAUDE_MD_TEMPLATE = """\
# {project_name} — Master System Prompt

> Auto-generated by AI Frame on {date}. Edit freely.
> Context files live in `.ai-frame/`. Run `python ai_frame.py` to manage sessions.

## Project Overview

- **Name:** {project_name}
- **Type:** {project_type}
- **Language:** {language}{runtime_line}
- **Framework(s):** {frameworks}
- **Architecture:** {architecture}
- **Phase:** {current_phase}
- **Team:** {team_size}

{description}

## Priorities & Goals

{priorities_block}

## Coding Standards

- **Testing:** {testing_strategy}
- **Style guide:** {code_style}
- Always write code that is consistent with the existing codebase conventions.
- Prefer clarity over cleverness. Code is read far more than it is written.
- Keep functions small and focused on a single responsibility.
- Name things explicitly — avoid abbreviations unless they are domain-standard.

## Hard Constraints

{constraints_block}

## Patterns to Avoid

{avoid_block}

## Architecture Principles

Follow **{architecture}** patterns throughout. Specifically:
- Separate concerns at module/package boundaries.
- Favour composition over inheritance.
- Keep dependencies explicit and minimal.
- Side-effects belong at the edges of the system.

## Response Behaviour

- Be concise. Prefer short responses unless depth is explicitly needed.
- When suggesting code, match the project's language, style, and naming conventions.
- Before proposing a refactor or new pattern, confirm it fits the architecture above.
- Flag breaking changes, security implications, or constraint violations explicitly.
- If uncertain about intent, ask one focused clarifying question rather than assuming.

## Session Context

At the start of each session:
1. Read `.ai-frame/progress.md` to understand current state.
2. Read `.ai-frame/decisions.md` for past architectural decisions.
3. Read `.ai-frame/architecture.md` for system design details.
4. Check `.ai-frame/sessions/` for recent session summaries.

{extra_context_block}\
"""

ARCHITECTURE_MD_TEMPLATE = """\
# Architecture Notes — {project_name}

> Keep this file updated as the system evolves. Last updated: {date}

## System Design

<!-- Describe the high-level architecture here. Diagrams as ASCII or Mermaid are welcome. -->

## Key Components

<!-- List major modules, services, or packages and their responsibilities. -->

## Data Flow

<!-- How does data move through the system? -->

## External Dependencies

<!-- Third-party services, APIs, databases, queues, etc. -->

## Known Trade-offs

<!-- Deliberate design trade-offs and their justifications. -->
"""

DECISIONS_MD_TEMPLATE = """\
# Architecture Decision Log — {project_name}

> Record significant decisions here. Format: date, decision, reasoning, alternatives considered.

## Template

```
### YYYY-MM-DD — <short title>
**Decision:** ...
**Reasoning:** ...
**Alternatives considered:** ...
**Consequences:** ...
```

---

### {date} — Project initialised with AI Frame
**Decision:** Set up AI Frame context management framework.
**Reasoning:** Reduce token usage across Claude Code sessions by persisting context locally.
**Alternatives considered:** None at this stage.
**Consequences:** Sessions should be started/ended with `python ai_frame.py start/end`.
"""

PROGRESS_MD_TEMPLATE = """\
# Current Progress — {project_name}

> Update this after each session. This is the first thing Claude reads. Last updated: {date}

## Status

**Phase:** {current_phase}

## What's Working

<!-- List features / components that are complete and stable. -->

## In Progress

<!-- What is actively being built right now? -->

## Next Up

<!-- Immediate next tasks in priority order. -->

## Blockers

<!-- Anything blocking progress. Remove when resolved. -->

## Recent Decisions

<!-- Latest significant decisions (link to decisions.md for full log). -->
"""

CONFIG_TEMPLATE: dict = {
    "version": "1.0",
    "project_name": "",
    "created": "",
    "project_type": "",
    "language": "",
    "runtime_version": "",
    "framework": "",
    "architecture": "",
    "testing_strategy": "",
    "current_phase": "",
    "team_size": "",
}

# ─── Init helpers ─────────────────────────────────────────────────────────────

def ask_text(label: str, placeholder: str = "", optional: bool = False) -> str:
    hint = f"  {YELLOW}({placeholder}){RESET}" if placeholder else ""
    opt  = f" {YELLOW}[optional]{RESET}" if optional else ""
    while True:
        raw = input(f"{BOLD}{label}{opt}{RESET}{hint}\n  > ").strip()
        if raw:
            return raw
        if optional:
            return ""
        print(f"  {YELLOW}This field is required.{RESET}")


def ask_choice(label: str, choices: list[str]) -> str:
    print(f"{BOLD}{label}{RESET}")
    for i, c in enumerate(choices, 1):
        print(f"  {CYAN}{i:>2}.{RESET} {c.replace('_', ' ')}")
    while True:
        raw = input("  > ").strip()
        if raw.isdigit() and 1 <= int(raw) <= len(choices):
            selected = choices[int(raw) - 1]
            print(f"  {GREEN}✓ {selected.replace('_', ' ')}{RESET}")
            return selected
        matches = [c for c in choices if c.lower().startswith(raw.lower())]
        if len(matches) == 1:
            print(f"  {GREEN}✓ {matches[0].replace('_', ' ')}{RESET}")
            return matches[0]
        print(f"  {YELLOW}Enter a number 1–{len(choices)}.{RESET}")


def ask(q: dict) -> str:
    print()
    if q["type"] == "choice":
        return ask_choice(q["label"], q["choices"])
    return ask_text(
        q["label"],
        placeholder=q.get("placeholder", ""),
        optional=q.get("optional", False),
    )


def bullet_list(text: str, fallback: str = "_None specified._") -> str:
    if not text:
        return fallback
    items = [i.strip() for i in text.split(",") if i.strip()]
    return "\n".join(f"- {item}" for item in items)


def build_claude_md(answers: dict) -> str:
    runtime_line = (
        f"\n- **Runtime/version:** {answers['runtime_version']}"
        if answers.get("runtime_version") else ""
    )
    return CLAUDE_MD_TEMPLATE.format(
        project_name=answers["project_name"],
        date=datetime.now().strftime("%Y-%m-%d"),
        project_type=answers["project_type"].replace("_", " "),
        language=answers["language"],
        runtime_line=runtime_line,
        frameworks=answers.get("frameworks") or "None",
        architecture=answers["architecture"].replace("_", " "),
        current_phase=answers["current_phase"].replace("_", " "),
        team_size=answers["team_size"].replace("_", " "),
        description=answers["description"],
        priorities_block=bullet_list(answers.get("priorities", "")),
        testing_strategy=answers["testing_strategy"].replace("_", " "),
        code_style=answers.get("code_style") or "Not specified",
        constraints_block=bullet_list(
            answers.get("constraints", ""), "_No hard constraints specified._"
        ),
        avoid_block=bullet_list(answers.get("avoid", ""), "_None specified._"),
        extra_context_block=(
            f"\n## Extra Context\n\n{answers['extra_context']}\n"
            if answers.get("extra_context") else ""
        ),
    )


def write_project_files(project_dir: Path, answers: dict) -> None:
    ai_frame_dir = project_dir / ".ai-frame"
    sessions_dir = ai_frame_dir / "sessions"

    ai_frame_dir.mkdir(parents=True, exist_ok=True)
    sessions_dir.mkdir(parents=True, exist_ok=True)

    date = datetime.now().strftime("%Y-%m-%d")
    name = answers["project_name"]

    claude_md = project_dir / "CLAUDE.md"
    if claude_md.exists():
        backup = project_dir / f"CLAUDE.md.bak.{datetime.now().strftime('%Y%m%d%H%M%S')}"
        claude_md.rename(backup)
        print(f"  Existing CLAUDE.md backed up to {backup.name}")
    claude_md.write_text(build_claude_md(answers), encoding="utf-8")
    print(f"  {GREEN}✓{RESET} CLAUDE.md")

    config = {**CONFIG_TEMPLATE}
    config.update({
        "project_name":    name,
        "created":         date,
        "project_type":    answers["project_type"],
        "language":        answers["language"],
        "runtime_version": answers.get("runtime_version", ""),
        "framework":       answers.get("frameworks", ""),
        "architecture":    answers["architecture"],
        "testing_strategy": answers["testing_strategy"],
        "current_phase":   answers["current_phase"],
        "team_size":       answers["team_size"],
    })
    (ai_frame_dir / "config.json").write_text(
        json.dumps(config, indent=2), encoding="utf-8"
    )
    print(f"  {GREEN}✓{RESET} .ai-frame/config.json")

    (ai_frame_dir / "architecture.md").write_text(
        ARCHITECTURE_MD_TEMPLATE.format(project_name=name, date=date), encoding="utf-8"
    )
    print(f"  {GREEN}✓{RESET} .ai-frame/architecture.md")

    (ai_frame_dir / "decisions.md").write_text(
        DECISIONS_MD_TEMPLATE.format(project_name=name, date=date), encoding="utf-8"
    )
    print(f"  {GREEN}✓{RESET} .ai-frame/decisions.md")

    (ai_frame_dir / "progress.md").write_text(
        PROGRESS_MD_TEMPLATE.format(
            project_name=name,
            date=date,
            current_phase=answers["current_phase"].replace("_", " "),
        ),
        encoding="utf-8",
    )
    print(f"  {GREEN}✓{RESET} .ai-frame/progress.md")

# ═══════════════════════════════════════════════════════════════════════════════
# SESSION COMMANDS
# ═══════════════════════════════════════════════════════════════════════════════

def cmd_start(project_dir: Path, ai_frame_dir: Path) -> None:
    cfg          = load_config(ai_frame_dir)
    sessions_dir = ai_frame_dir / "sessions"
    sessions_dir.mkdir(exist_ok=True)
    name = cfg.get("project_name", project_dir.name)

    print()
    print(separator("═"))
    print(f"{BOLD}{CYAN}  SESSION BRIEFING — {name}{RESET}")
    print(f"  {DIM}{datetime.now().strftime('%Y-%m-%d %H:%M')}{RESET}")
    print(separator("═"))

    print(f"\n{BOLD}── Current Progress{RESET}")
    print(read_file_safe(ai_frame_dir / "progress.md", max_lines=40))

    recent = latest_sessions(sessions_dir, n=2)
    if recent:
        print(f"\n{BOLD}── Recent Session Notes{RESET}")
        for s in recent:
            print(f"\n{YELLOW}{s.stem}{RESET}")
            print(read_file_safe(s, max_lines=30))

    print(f"\n{BOLD}── Project Config{RESET}")
    for k in ["language", "framework", "architecture", "testing_strategy", "current_phase"]:
        v = cfg.get(k, "")
        if v:
            print(f"  {k.replace('_', ' '):20s}: {v.replace('_', ' ')}")

    print()
    print(separator("═"))
    print(
        f"\n{GREEN}Tip:{RESET} Tell Claude: "
        f"\"Read .ai-frame/progress.md and recent sessions to get context.\"\n"
    )

    today        = datetime.now().strftime("%Y-%m-%d")
    session_file = sessions_dir / f"{today}.md"
    if not session_file.exists():
        session_file.write_text(
            f"# Session — {today}\n\n## Goals\n\n"
            f"<!-- What do you want to accomplish today? -->\n\n"
            f"## Notes\n\n## Summary\n\n"
            f"<!-- Fill this in when you run `python ai_frame.py end` -->\n",
            encoding="utf-8",
        )
        print(f"  {DIM}Created session file: .ai-frame/sessions/{today}.md{RESET}")


def cmd_end(project_dir: Path, ai_frame_dir: Path) -> None:
    sessions_dir = ai_frame_dir / "sessions"
    sessions_dir.mkdir(exist_ok=True)

    today        = datetime.now().strftime("%Y-%m-%d")
    session_file = sessions_dir / f"{today}.md"
    cfg  = load_config(ai_frame_dir)
    name = cfg.get("project_name", project_dir.name)

    print()
    print(separator("═"))
    print(f"{BOLD}{CYAN}  SESSION END — {name}{RESET}")
    print(separator("═"))
    print()

    def multiline_input(prompt: str) -> list[str]:
        print(f"{BOLD}{prompt}{RESET}")
        print(f"  {DIM}(One item per line. Blank line to finish.){RESET}")
        lines = []
        while True:
            line = input("  > ").strip()
            if not line:
                break
            lines.append(line)
        return lines

    accomplished = multiline_input("What did you accomplish this session?")
    decisions    = multiline_input("Any architectural/design decisions made?")
    next_tasks   = multiline_input("What are the immediate next tasks?")
    blockers     = multiline_input("Any blockers or open questions?")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    nl = "\n"

    summary = dedent(f"""\
        # Session — {today}

        **Recorded:** {timestamp}

        ## Accomplished

        {nl.join(f"- {a}" for a in accomplished) or "_Nothing recorded._"}

        ## Decisions Made

        {nl.join(f"- {d}" for d in decisions) or "_None._"}

        ## Next Tasks

        {nl.join(f"- {t}" for t in next_tasks) or "_Not recorded._"}

        ## Blockers

        {nl.join(f"- {b}" for b in blockers) or "_None._"}
    """)

    session_file.write_text(summary, encoding="utf-8")
    print(f"\n  {GREEN}✓{RESET} Session saved: .ai-frame/sessions/{today}.md")

    print()
    if input(
        f"  Update {CYAN}progress.md{RESET} with next tasks? [Y/n] > "
    ).strip().lower() in ("", "y", "yes"):
        progress_path = ai_frame_dir / "progress.md"
        current = progress_path.read_text(encoding="utf-8") if progress_path.exists() else ""

        def replace_section(text: str, heading: str, new_body: str) -> str:
            block = f"\n## {heading}\n\n{new_body}\n"
            if f"## {heading}" in text:
                before, _, after = text.partition(f"## {heading}")
                rest = after.split("\n## ", 1)
                tail = ("\n## " + rest[1]) if len(rest) > 1 else ""
                return before + block + tail
            return text.rstrip() + "\n" + block

        next_body    = "\n".join(f"- {t}" for t in next_tasks) if next_tasks else "_Not recorded._"
        blocker_body = "\n".join(f"- {b}" for b in blockers)   if blockers   else "_None._"
        current = replace_section(current, "Next Up", next_body)
        current = replace_section(current, "Blockers", blocker_body)
        if "Last updated:" in current:
            current = re.sub(r"Last updated: \S+", f"Last updated: {today}", current)
        progress_path.write_text(current, encoding="utf-8")
        print(f"  {GREEN}✓{RESET} .ai-frame/progress.md updated")

    if decisions:
        print()
        if input(
            f"  Append decisions to {CYAN}decisions.md{RESET}? [Y/n] > "
        ).strip().lower() in ("", "y", "yes"):
            decisions_path = ai_frame_dir / "decisions.md"
            existing = decisions_path.read_text(encoding="utf-8") if decisions_path.exists() else ""
            entries = "\n".join(
                f"### {today} — {d}\n**Decision:** {d}\n**Reasoning:** _Add reasoning here._\n"
                for d in decisions
            )
            decisions_path.write_text(existing + "\n---\n\n" + entries, encoding="utf-8")
            print(f"  {GREEN}✓{RESET} .ai-frame/decisions.md updated")

    print(f"\n  {GREEN}Session closed.{RESET} See you next time!\n")


def cmd_status(project_dir: Path, ai_frame_dir: Path) -> None:
    cfg          = load_config(ai_frame_dir)
    sessions_dir = ai_frame_dir / "sessions"
    name         = cfg.get("project_name", project_dir.name)
    session_count = len(list(sessions_dir.glob("*.md"))) if sessions_dir.exists() else 0

    print()
    print(separator())
    print(f"{BOLD}{CYAN}  {name} — Status{RESET}")
    print(separator())
    print(f"  Phase    : {cfg.get('current_phase', 'unknown').replace('_', ' ')}")
    print(f"  Language : {cfg.get('language', '?')}  {cfg.get('framework', '')}")
    print(f"  Sessions : {session_count} recorded")
    recent = latest_sessions(sessions_dir, n=1)
    if recent:
        print(f"  Last     : {recent[0].stem}")
    print()
    print(separator())
    print(f"\n{BOLD}Progress{RESET}")
    print(read_file_safe(ai_frame_dir / "progress.md", max_lines=20))
    print()


def cmd_update(project_dir: Path, ai_frame_dir: Path) -> None:
    files = {
        "1": ("progress.md",     "Current progress / next tasks"),
        "2": ("architecture.md", "Architecture notes"),
        "3": ("decisions.md",    "Decision log"),
    }

    print()
    print(f"{BOLD}Which file to update?{RESET}")
    for k, (f, label) in files.items():
        print(f"  {CYAN}{k}.{RESET} {f:25s} — {label}")
    print(f"  {CYAN}q.{RESET} Cancel")

    choice = input("  > ").strip()
    if choice not in files:
        print("Cancelled.")
        return

    fname, _ = files[choice]
    path     = ai_frame_dir / fname
    current  = path.read_text(encoding="utf-8") if path.exists() else ""

    print(f"\n{DIM}Current content (first 30 lines):{RESET}")
    for line in current.splitlines()[:30]:
        print(f"  {line}")

    print(f"\n{BOLD}Content to APPEND{RESET} (blank line to finish):")
    new_lines = []
    while True:
        line = input("  > ")
        if not line:
            break
        new_lines.append(line)

    if new_lines:
        path.write_text(current + "\n" + "\n".join(new_lines) + "\n", encoding="utf-8")
        print(f"  {GREEN}✓{RESET} {fname} updated.")
    else:
        print("  No changes made.")

# ═══════════════════════════════════════════════════════════════════════════════
# CONTEXT BUILDER
# ═══════════════════════════════════════════════════════════════════════════════

ALL_SECTIONS = ["config", "progress", "architecture", "decisions", "sessions"]

MAX_LINES = {
    "progress":     60,
    "architecture": 80,
    "decisions":    60,
    "sessions":     40,
}


def read_truncated(path: Path, max_lines: int) -> str:
    if not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) <= max_lines:
        return "\n".join(lines)
    return "\n".join(lines[:max_lines]) + f"\n... [{len(lines) - max_lines} lines omitted]"


def strip_comments(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL).strip()


def strip_empty_sections(text: str) -> str:
    lines  = text.splitlines()
    output = []
    i = 0
    while i < len(lines):
        line = lines[i]
        if re.match(r"^#{1,3} ", line):
            body_lines, j = [], i + 1
            while j < len(lines) and not re.match(r"^#{1,3} ", lines[j]):
                body_lines.append(lines[j])
                j += 1
            if "\n".join(body_lines).strip():
                output.append(line)
                output.extend(body_lines)
            i = j
        else:
            output.append(line)
            i += 1
    return "\n".join(output)


def build_config_section(cfg: dict) -> str:
    if not cfg:
        return ""
    keys = ["project_name", "language", "runtime_version", "framework",
            "architecture", "testing_strategy", "current_phase", "team_size"]
    lines = [
        f"- **{k.replace('_', ' ')}:** {cfg[k].replace('_', ' ')}"
        for k in keys if cfg.get(k)
    ]
    return ("## Project Config\n\n" + "\n".join(lines)) if lines else ""


def _process(path: Path, max_lines: int, compact: bool) -> str:
    raw = read_truncated(path, max_lines)
    raw = strip_comments(raw)
    if compact:
        raw = strip_empty_sections(raw)
    return raw.strip()


def build_decisions_section(ai_frame_dir: Path, compact: bool) -> str:
    raw = _process(ai_frame_dir / "decisions.md", MAX_LINES["decisions"], compact)
    if compact and raw:
        blocks = re.split(r"(?=^### )", raw, flags=re.MULTILINE)
        heading = [b for b in blocks if not b.startswith("###")]
        decision = [b for b in blocks if b.startswith("###")]
        raw = "".join(heading) + "".join(decision[-3:])
    return raw.strip()


def build_sessions_section(ai_frame_dir: Path, compact: bool, n: int = 3) -> str:
    sessions_dir = ai_frame_dir / "sessions"
    if not sessions_dir.exists():
        return ""
    files = sorted(sessions_dir.glob("*.md"), reverse=True)[:n]
    parts = [
        p for f in files
        if (p := _process(f, MAX_LINES["sessions"], compact))
    ]
    return "\n\n---\n\n".join(parts)


def build_context(
    project_dir: Path,
    ai_frame_dir: Path,
    sections: list[str],
    compact: bool,
) -> str:
    cfg  = load_config(ai_frame_dir)
    name = cfg.get("project_name", project_dir.name)
    date = datetime.now().strftime("%Y-%m-%d %H:%M")

    parts = [
        f"# AI Frame Context — {name}\n"
        f"_Generated {date}. Regenerate with `python ai_frame.py context`._\n"
    ]

    section_map = {
        "config":       lambda: build_config_section(cfg),
        "progress":     lambda: _process(ai_frame_dir / "progress.md",     MAX_LINES["progress"],     compact),
        "architecture": lambda: _process(ai_frame_dir / "architecture.md", MAX_LINES["architecture"], compact),
        "decisions":    lambda: build_decisions_section(ai_frame_dir, compact),
        "sessions":     lambda: build_sessions_section(ai_frame_dir, compact),
    }

    for sec in sections:
        if sec in section_map:
            content = section_map[sec]()
            if content:
                parts.append(content)

    return "\n\n".join(parts)


def cmd_context(project_dir: Path, ai_frame_dir: Path, args: argparse.Namespace) -> None:
    sections = [s.strip() for s in args.sections.split(",") if s.strip()]
    invalid  = [s for s in sections if s not in ALL_SECTIONS]
    if invalid:
        print(
            f"Error: unknown section(s): {', '.join(invalid)}\n"
            f"Valid: {', '.join(ALL_SECTIONS)}",
            file=sys.stderr,
        )
        sys.exit(1)

    context       = build_context(project_dir, ai_frame_dir, sections, compact=args.compact)
    approx_tokens = len(context) // 4

    if args.output:
        Path(args.output).write_text(context, encoding="utf-8")
        print(f"Written to {args.output} (~{approx_tokens:,} tokens)", file=sys.stderr)
    else:
        print(context)
        print(f"\n{'─'*60}\n~{approx_tokens:,} estimated tokens", file=sys.stderr)

# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ai_frame.py",
        description="AI Frame — Claude Code project context manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=dedent("""\
            examples:
              python ai_frame.py init                        # wizard: set up a new project
              python ai_frame.py start                       # session briefing
              python ai_frame.py end                         # record session summary
              python ai_frame.py status                      # quick project overview
              python ai_frame.py update                      # append to a context file
              python ai_frame.py context --compact           # compressed context snapshot
              python ai_frame.py context -o ctx.md --compact # write snapshot to file
        """),
    )
    parser.add_argument(
        "command",
        choices=["init", "start", "end", "status", "update", "context"],
        help="Command to run",
    )
    parser.add_argument(
        "--project-dir", "-d",
        default=".",
        help="Project directory (default: current directory)",
    )

    # context-specific flags
    parser.add_argument("--output", "-o", default=None, help="[context] Write output to file")
    parser.add_argument("--compact", "-c", action="store_true",  help="[context] Strip placeholder comments and empty sections")
    parser.add_argument(
        "--sections", "-s",
        default=",".join(ALL_SECTIONS),
        help=f"[context] Comma-separated sections: {', '.join(ALL_SECTIONS)}",
    )

    args = parser.parse_args()

    # init does not require .ai-frame/ to exist yet
    if args.command == "init":
        project_dir = Path(args.project_dir).resolve()
        if not project_dir.exists():
            print(f"Error: directory does not exist: {project_dir}")
            sys.exit(1)
        header("AI Frame — Project Initialisation Wizard")
        print(f"  Target directory: {CYAN}{project_dir}{RESET}")
        print("  Answer the questions below to generate your CLAUDE.md master prompt.")
        print("  Press Ctrl-C at any time to abort without writing files.\n")
        answers: dict[str, str] = {}
        try:
            for q in QUESTIONS:
                answers[q["key"]] = ask(q)
        except KeyboardInterrupt:
            print(f"\n\n  {YELLOW}Aborted. No files written.{RESET}\n")
            sys.exit(0)
        header("Generating project files")
        write_project_files(project_dir, answers)
        header("Done!")
        print(f"  Next steps:\n")
        print(f"  1. Open {CYAN}{project_dir}{RESET} in Claude Code — CLAUDE.md loads automatically")
        print(f"  2. Fill in {CYAN}.ai-frame/architecture.md{RESET} with system design details")
        print(f"  3. Run {CYAN}python ai_frame.py start{RESET} at the beginning of each session")
        print(f"  4. Run {CYAN}python ai_frame.py end{RESET} at the end of each session\n")
        return

    project_dir, ai_frame_dir = resolve_dirs(args.project_dir)

    if args.command == "context":
        cmd_context(project_dir, ai_frame_dir, args)
    elif args.command == "start":
        cmd_start(project_dir, ai_frame_dir)
    elif args.command == "end":
        cmd_end(project_dir, ai_frame_dir)
    elif args.command == "status":
        cmd_status(project_dir, ai_frame_dir)
    elif args.command == "update":
        cmd_update(project_dir, ai_frame_dir)


if __name__ == "__main__":
    main()
