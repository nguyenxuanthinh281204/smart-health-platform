---
description: Mandatory operational directive for Smart Health Data Platform
globs: ["**/*"]
alwaysApply: true
---

# SMART HEALTH DATA PLATFORM - AI OPERATING PROTOCOL

1. **Context Synchronization:** Always inspect `PROJECT_STATE.md` and `TASK_TRACKER.md` before proposing, authoring, or refactoring code.
2. **State Persistence:** After completing any task, automatically persist status changes into `PROJECT_STATE.md` and check off `[x]` items in `TASK_TRACKER.md`.
3. **Architectural Integrity:** Strictly conform to the Medallion Architecture (Bronze/Silver/Gold) and the Star Schema defined in `DATA_SPECIFICATION.md`.
4. **Language Standard:** All source code, schema names, dbt models, variable names, docstrings, commit messages, and markdown documentation MUST be written in professional **English**.
5. **Production Quality:** Avoid ephemeral manual scripts; containerize all services via Docker Compose and enforce automated dbt tests.
