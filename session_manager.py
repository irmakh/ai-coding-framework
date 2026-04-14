#!/usr/bin/env python3
"""
AI Frame — Session Manager
Manages Claude Code session context: start briefings, end summaries, status checks.

Usage:
    python session_manager.py start   [--project-dir PATH]
    python session_manager.py end     [--project-dir PATH]
    python session_manager.py status  [--project-dir PATH]
    python session_manager.py update  [--project-dir PATH]
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from textwrap import dedent

# ─── Helpers ──────────────────────────────────────────────────────────────────

CYAN   = "\033[96m"
YELLOW = "\033[93m"
GREEN  = "\033[92m"
RED    = "\033[91m"
RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"


def separator(char: str = "─", width: int = 60) -> str:
    return f"{DIM}{char * width}{RESET}"


def load_config(ai_frame_dir: Path) -> dict:
    cfg_path = ai_frame_dir / "config.json"
    if not cfg_path.exists():
        return {}
    return json.loads(cfg_path.read_text(encoding="utf-8"))


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


def resolve_dirs(project_dir_arg: str) -> tuple[Path, Path]:
    project_dir = Path(project_dir_arg).resolve()
    ai_frame_dir = project_dir / ".ai-frame"
    if not ai_frame_dir.exists():
        print(
            f"{RED}Error:{RESET} No .ai-frame/ directory found in {project_dir}.\n"
            f"  Run {CYAN}init_project.py{RESET} first to initialise this project."
        )
        sys.exit(1)
    return project_dir, ai_frame_dir

# ─── Commands ─────────────────────────────────────────────────────────────────

def cmd_start(project_dir: Path, ai_frame_dir: Path) -> None:
    """Print a context briefing to paste into Claude Code at session start."""
    cfg = load_config(ai_frame_dir)
    sessions_dir = ai_frame_dir / "sessions"
    sessions_dir.mkdir(exist_ok=True)

    name = cfg.get("project_name", project_dir.name)

    print()
    print(separator("═"))
    print(f"{BOLD}{CYAN}  SESSION BRIEFING — {name}{RESET}")
    print(f"  {DIM}{datetime.now().strftime('%Y-%m-%d %H:%M')}{RESET}")
    print(separator("═"))

    # ── Progress
    print(f"\n{BOLD}── Current Progress{RESET}")
    progress = read_file_safe(ai_frame_dir / "progress.md", max_lines=40)
    print(progress)

    # ── Recent sessions
    recent = latest_sessions(sessions_dir, n=2)
    if recent:
        print(f"\n{BOLD}── Recent Session Notes{RESET}")
        for s in recent:
            print(f"\n{YELLOW}{s.stem}{RESET}")
            print(read_file_safe(s, max_lines=30))

    # ── Quick config reminder
    print(f"\n{BOLD}── Project Config{RESET}")
    interesting = ["language", "framework", "architecture", "testing_strategy", "current_phase"]
    for k in interesting:
        v = cfg.get(k, "")
        if v:
            print(f"  {k.replace('_', ' '):20s}: {v.replace('_', ' ')}")

    print()
    print(separator("═"))
    print(
        f"\n{GREEN}Tip:{RESET} Paste this briefing into Claude Code with:\n"
        f"  {CYAN}python session_manager.py start{RESET}\n"
        f"Or copy the output above and paste it as your first message.\n"
    )

    # Record session start
    today = datetime.now().strftime("%Y-%m-%d")
    session_file = sessions_dir / f"{today}.md"
    if not session_file.exists():
        session_file.write_text(
            f"# Session — {today}\n\n## Goals\n\n<!-- What do you want to accomplish today? -->\n\n"
            f"## Notes\n\n## Summary\n\n<!-- Fill this in when you run `session_manager.py end` -->\n",
            encoding="utf-8",
        )
        print(f"  {DIM}Created session file: .ai-frame/sessions/{today}.md{RESET}")


def cmd_end(project_dir: Path, ai_frame_dir: Path) -> None:
    """Interactively record a session summary and optionally update progress."""
    sessions_dir = ai_frame_dir / "sessions"
    sessions_dir.mkdir(exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    session_file = sessions_dir / f"{today}.md"

    cfg = load_config(ai_frame_dir)
    name = cfg.get("project_name", project_dir.name)

    print()
    print(separator("═"))
    print(f"{BOLD}{CYAN}  SESSION END — {name}{RESET}")
    print(separator("═"))
    print()

    def multiline_input(prompt: str) -> str:
        print(f"{BOLD}{prompt}{RESET}")
        print(f"  {DIM}(Enter one item per line. Blank line to finish.){RESET}")
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

    summary_block = dedent(f"""\
        # Session — {today}

        **Recorded:** {timestamp}

        ## Accomplished

        {chr(10).join(f"- {a}" for a in accomplished) or "_Nothing recorded._"}

        ## Decisions Made

        {chr(10).join(f"- {d}" for d in decisions) or "_None._"}

        ## Next Tasks

        {chr(10).join(f"- {t}" for t in next_tasks) or "_Not recorded._"}

        ## Blockers

        {chr(10).join(f"- {b}" for b in blockers) or "_None._"}
    """)

    session_file.write_text(summary_block, encoding="utf-8")
    print(f"\n  {GREEN}✓{RESET} Session saved: .ai-frame/sessions/{today}.md")

    # Offer to update progress.md
    print()
    update_progress = input(
        f"  Update {CYAN}progress.md{RESET} with next tasks? [Y/n] > "
    ).strip().lower()

    if update_progress in ("", "y", "yes"):
        progress_path = ai_frame_dir / "progress.md"
        current = progress_path.read_text(encoding="utf-8") if progress_path.exists() else ""

        next_block = (
            "\n## Next Up\n\n"
            + ("\n".join(f"- {t}" for t in next_tasks) if next_tasks else "_Not recorded._")
            + "\n"
        )

        # Replace or append the "Next Up" section
        if "## Next Up" in current:
            before, _, after = current.partition("## Next Up")
            # Find the next section
            sections = after.split("\n## ")
            new_section = next_block + ("\n## " + "\n## ".join(sections[1:]) if len(sections) > 1 else "")
            current = before + new_section
        else:
            current = current.rstrip() + "\n" + next_block

        # Append blockers section update
        blocker_block = (
            "\n## Blockers\n\n"
            + ("\n".join(f"- {b}" for b in blockers) if blockers else "_None._")
            + "\n"
        )
        if "## Blockers" in current:
            before, _, after = current.partition("## Blockers")
            sections = after.split("\n## ")
            current = before + blocker_block + ("\n## " + "\n## ".join(sections[1:]) if len(sections) > 1 else "")
        else:
            current = current.rstrip() + "\n" + blocker_block

        # Update the "Last updated" date
        if "Last updated:" in current:
            import re
            current = re.sub(r"Last updated: \S+", f"Last updated: {today}", current)

        progress_path.write_text(current, encoding="utf-8")
        print(f"  {GREEN}✓{RESET} .ai-frame/progress.md updated")

    # Prompt to add architectural decisions
    if decisions:
        print()
        add_decisions = input(
            f"  Append decisions to {CYAN}decisions.md{RESET}? [Y/n] > "
        ).strip().lower()
        if add_decisions in ("", "y", "yes"):
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
    """Print a compact status overview."""
    cfg = load_config(ai_frame_dir)
    sessions_dir = ai_frame_dir / "sessions"

    name = cfg.get("project_name", project_dir.name)
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
        print(f"  Last session : {recent[0].stem}")
    print()
    print(separator())

    print(f"\n{BOLD}Progress{RESET}")
    print(read_file_safe(ai_frame_dir / "progress.md", max_lines=20))
    print()


def cmd_update(project_dir: Path, ai_frame_dir: Path) -> None:
    """Interactively update a specific context file."""
    files = {
        "1": ("progress.md", "Current progress / next tasks"),
        "2": ("architecture.md", "Architecture notes"),
        "3": ("decisions.md", "Decision log"),
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
    path = ai_frame_dir / fname

    current = path.read_text(encoding="utf-8") if path.exists() else ""
    print(f"\n{DIM}Current content (first 30 lines):{RESET}")
    lines = current.splitlines()
    for line in lines[:30]:
        print(f"  {line}")
    if len(lines) > 30:
        print(f"  {DIM}... ({len(lines) - 30} more lines){RESET}")

    print(f"\n{BOLD}Enter new content to APPEND{RESET} (blank line to finish):")
    new_lines = []
    while True:
        line = input("  > ")
        if not line:
            break
        new_lines.append(line)

    if new_lines:
        addition = "\n" + "\n".join(new_lines) + "\n"
        path.write_text(current + addition, encoding="utf-8")
        print(f"  {GREEN}✓{RESET} {fname} updated.")
    else:
        print("  No changes made.")

# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="AI Frame — manage Claude Code session context",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=dedent("""\
            Commands:
              start   Print a session briefing and create today's session file
              end     Record what was accomplished and update context files
              status  Print a compact project status overview
              update  Append content to a specific context file
        """),
    )
    parser.add_argument("command", choices=["start", "end", "status", "update"])
    parser.add_argument(
        "--project-dir",
        default=".",
        help="Path to the project directory (default: current directory)",
    )
    args = parser.parse_args()

    project_dir, ai_frame_dir = resolve_dirs(args.project_dir)

    dispatch = {
        "start":  cmd_start,
        "end":    cmd_end,
        "status": cmd_status,
        "update": cmd_update,
    }
    dispatch[args.command](project_dir, ai_frame_dir)


if __name__ == "__main__":
    main()
