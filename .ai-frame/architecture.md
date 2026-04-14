# Architecture Notes — AI Frame

> Keep this file updated as the system evolves. Last updated: 2026-04-14

## System Design

Single Python file (`ai_frame.py`) with subcommand dispatch via `argparse`. No classes —
all logic is plain functions grouped by responsibility. Designed to be copied anywhere and
run with just `python ai_frame.py <command>`.

```
ai_frame.py
├── Shared utilities   (colours, separator, load_config, read_file_safe, resolve_dirs)
├── Init section       (QUESTIONS list, templates, ask/ask_choice, write_project_files)
├── Session section    (cmd_start, cmd_end, cmd_status, cmd_update)
├── Context section    (build_context, build_*_section helpers)
└── main()             (argparse subcommand dispatch)
```

## Key Components

- **`main()`** — argparse entry point; dispatches to the six subcommand functions.
- **`write_project_files()`** — generates `CLAUDE.md` and all `.ai-frame/` files from wizard answers.
- **`cmd_start/end/status/update()`** — session lifecycle management; reads/writes `.ai-frame/`.
- **`build_context()`** — assembles `.ai-frame/` files into a compressed context snapshot.
- **Templates** — `CLAUDE_MD_TEMPLATE`, `PROGRESS_MD_TEMPLATE`, etc. are module-level strings.

## Data Flow

```
User runs: python ai_frame.py <cmd> [--project-dir PATH]
  └─> resolve_dirs() verifies .ai-frame/ exists
        └─> cmd_*() reads .ai-frame/config.json, *.md, sessions/*.md
              └─> writes updated files back to .ai-frame/
```

For `init`, the wizard collects answers → `build_claude_md()` renders the template →
files are written to the target project directory.

## External Dependencies

None. Pure Python 3.10+ standard library only: `argparse`, `json`, `re`, `pathlib`,
`datetime`, `textwrap`.

## Known Trade-offs

- **Single file over package structure** — easier to distribute (just copy the file),
  but all code lives in one ~500-line module. Acceptable at this scale.
- **No `--non-interactive` flag for `init`** — currently requires stdin piping for
  scripted use. A future `--answers-file` option would improve this.
- **Approximate token counting** — `len(text) // 4` is a rough heuristic, not exact.
- **Windows terminal encoding** — box-drawing characters require `PYTHONIOENCODING=utf-8`
  on Windows when piping stdin. Interactive sessions work fine without it.
