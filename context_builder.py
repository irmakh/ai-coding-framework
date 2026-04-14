#!/usr/bin/env python3
"""
AI Frame — Context Builder
Assembles all .ai-frame/ context files into a single compressed briefing
that can be pasted into Claude Code or any LLM chat interface.

Usage:
    python context_builder.py              (uses current directory)
    python context_builder.py --project-dir PATH
    python context_builder.py --output FILE    (write to file instead of stdout)
    python context_builder.py --compact        (minimal format, fewer tokens)
    python context_builder.py --sections progress,decisions  (select sections)
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from textwrap import indent


# ─── Config ───────────────────────────────────────────────────────────────────

ALL_SECTIONS = ["config", "progress", "architecture", "decisions", "sessions"]

MAX_LINES = {
    "progress":     60,
    "architecture": 80,
    "decisions":    60,
    "sessions":     40,   # per session file
}

# ─── Helpers ──────────────────────────────────────────────────────────────────

def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def read_truncated(path: Path, max_lines: int) -> str:
    if not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) <= max_lines:
        return "\n".join(lines)
    kept = lines[:max_lines]
    return "\n".join(kept) + f"\n... [{len(lines) - max_lines} lines omitted for brevity]"


def strip_comments(text: str) -> str:
    """Remove HTML comment blocks (<!-- ... -->) used as placeholders."""
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL).strip()


def strip_empty_sections(text: str) -> str:
    """Remove markdown sections whose body is empty after stripping."""
    lines = text.splitlines()
    output = []
    i = 0
    while i < len(lines):
        line = lines[i]
        # Check if this is a heading
        if re.match(r"^#{1,3} ", line):
            # Collect body until next heading or EOF
            body_lines = []
            j = i + 1
            while j < len(lines) and not re.match(r"^#{1,3} ", lines[j]):
                body_lines.append(lines[j])
                j += 1
            body = "\n".join(body_lines).strip()
            if body:
                output.append(line)
                output.extend(body_lines)
            i = j
        else:
            output.append(line)
            i += 1
    return "\n".join(output)


def count_tokens_approx(text: str) -> int:
    """Very rough estimate: 1 token ≈ 4 characters."""
    return len(text) // 4

# ─── Section Builders ─────────────────────────────────────────────────────────

def build_config_section(cfg: dict) -> str:
    if not cfg:
        return ""
    interesting = [
        "project_name", "language", "runtime_version", "framework",
        "architecture", "testing_strategy", "current_phase", "team_size"
    ]
    lines = []
    for k in interesting:
        v = cfg.get(k, "")
        if v:
            lines.append(f"- **{k.replace('_', ' ')}:** {v.replace('_', ' ')}")
    return "## Project Config\n\n" + "\n".join(lines) if lines else ""


def build_progress_section(ai_frame_dir: Path, compact: bool) -> str:
    path = ai_frame_dir / "progress.md"
    if not path.exists():
        return ""
    raw = read_truncated(path, MAX_LINES["progress"])
    raw = strip_comments(raw)
    if compact:
        raw = strip_empty_sections(raw)
    return raw.strip()


def build_architecture_section(ai_frame_dir: Path, compact: bool) -> str:
    path = ai_frame_dir / "architecture.md"
    if not path.exists():
        return ""
    raw = read_truncated(path, MAX_LINES["architecture"])
    raw = strip_comments(raw)
    if compact:
        raw = strip_empty_sections(raw)
    return raw.strip()


def build_decisions_section(ai_frame_dir: Path, compact: bool) -> str:
    path = ai_frame_dir / "decisions.md"
    if not path.exists():
        return ""
    raw = read_truncated(path, MAX_LINES["decisions"])
    raw = strip_comments(raw)
    # In compact mode, only keep last N decision blocks
    if compact:
        blocks = re.split(r"(?=^### )", raw, flags=re.MULTILINE)
        # Keep heading block + last 3 decisions
        heading_blocks = [b for b in blocks if not b.startswith("###")]
        decision_blocks = [b for b in blocks if b.startswith("###")]
        raw = "".join(heading_blocks) + "".join(decision_blocks[-3:])
    return raw.strip()


def build_sessions_section(ai_frame_dir: Path, compact: bool, n_sessions: int = 3) -> str:
    sessions_dir = ai_frame_dir / "sessions"
    if not sessions_dir.exists():
        return ""
    files = sorted(sessions_dir.glob("*.md"), reverse=True)[:n_sessions]
    if not files:
        return ""

    parts = []
    for f in files:
        raw = read_truncated(f, MAX_LINES["sessions"])
        raw = strip_comments(raw)
        if compact:
            raw = strip_empty_sections(raw)
        if raw.strip():
            parts.append(raw.strip())

    return "\n\n---\n\n".join(parts) if parts else ""

# ─── Assembler ────────────────────────────────────────────────────────────────

def build_context(
    project_dir: Path,
    ai_frame_dir: Path,
    sections: list[str],
    compact: bool,
) -> str:
    cfg = load_json(ai_frame_dir / "config.json")
    name = cfg.get("project_name", project_dir.name)
    date = datetime.now().strftime("%Y-%m-%d %H:%M")

    parts: list[str] = []

    header = (
        f"# AI Frame Context — {name}\n"
        f"_Generated {date}. Do not edit — regenerate with context_builder.py._\n"
    )
    parts.append(header)

    section_map = {
        "config":       lambda: build_config_section(cfg),
        "progress":     lambda: build_progress_section(ai_frame_dir, compact),
        "architecture": lambda: build_architecture_section(ai_frame_dir, compact),
        "decisions":    lambda: build_decisions_section(ai_frame_dir, compact),
        "sessions":     lambda: build_sessions_section(ai_frame_dir, compact),
    }

    for sec in sections:
        builder = section_map.get(sec)
        if not builder:
            continue
        content = builder()
        if content:
            parts.append(content)

    return "\n\n".join(parts)

# ─── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="AI Frame — build a compressed context briefing from .ai-frame/ files"
    )
    parser.add_argument(
        "--project-dir",
        default=".",
        help="Path to the project directory (default: current directory)",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Write output to this file instead of stdout",
    )
    parser.add_argument(
        "--compact", "-c",
        action="store_true",
        help="Compact mode: strip placeholder comments and empty sections",
    )
    parser.add_argument(
        "--sections", "-s",
        default=",".join(ALL_SECTIONS),
        help=f"Comma-separated list of sections to include. Options: {', '.join(ALL_SECTIONS)}",
    )
    args = parser.parse_args()

    project_dir = Path(args.project_dir).resolve()
    ai_frame_dir = project_dir / ".ai-frame"

    if not ai_frame_dir.exists():
        print(
            f"Error: No .ai-frame/ directory found in {project_dir}.\n"
            f"Run init_project.py first to initialise this project.",
            file=sys.stderr,
        )
        sys.exit(1)

    sections = [s.strip() for s in args.sections.split(",") if s.strip()]
    invalid = [s for s in sections if s not in ALL_SECTIONS]
    if invalid:
        print(
            f"Error: unknown section(s): {', '.join(invalid)}\n"
            f"Valid sections: {', '.join(ALL_SECTIONS)}",
            file=sys.stderr,
        )
        sys.exit(1)

    context = build_context(project_dir, ai_frame_dir, sections, compact=args.compact)

    approx_tokens = count_tokens_approx(context)

    if args.output:
        out_path = Path(args.output)
        out_path.write_text(context, encoding="utf-8")
        print(
            f"Written to {out_path} (~{approx_tokens:,} tokens)",
            file=sys.stderr,
        )
    else:
        print(context)
        print(
            f"\n{'─'*60}\n~{approx_tokens:,} estimated tokens",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
