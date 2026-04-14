# Architecture Decision Log — AI Frame

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

### 2026-04-14 — Project initialised with AI Frame
**Decision:** Set up AI Frame context management framework to manage itself.
**Reasoning:** Dogfooding — if the tool can manage its own development, it validates the workflow.
**Alternatives considered:** Managing the repo manually without context files.
**Consequences:** Sessions should be started/ended with `python ai_frame.py start/end`.

---

### 2026-04-14 — Merge three scripts into a single file
**Decision:** Consolidated `init_project.py`, `session_manager.py`, `context_builder.py` into `ai_frame.py`.
**Reasoning:** A single file is easier to distribute (download one file, run anywhere) and removes the cognitive overhead of remembering which script does what.
**Alternatives considered:** Keep three separate files; use a package with `__main__.py`.
**Consequences:** All functionality accessed via subcommands: `init`, `start`, `end`, `status`, `update`, `context`. File is ~500 lines — still readable at this size.

---

### 2026-04-14 — No external dependencies
**Decision:** Restrict to Python standard library only.
**Reasoning:** Zero install friction. Users should be able to run the tool on any Python 3.10+ environment without `pip install`.
**Alternatives considered:** Using `rich` for prettier terminal output; `click` for CLI parsing.
**Consequences:** Box-drawing characters cause encoding issues on Windows when piping stdin. Workaround: set `PYTHONIOENCODING=utf-8`.
