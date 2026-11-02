# Week 5 Write-up
Tip: To preview this markdown file
- On Mac, press `Command (⌘) + Shift + V`
- On Windows/Linux, press `Ctrl + Shift + V`

## INSTRUCTIONS

Fill out all of the `TODO`s in this file.

## SUBMISSION DETAILS

Name: **TODO** \
SUNet ID: **TODO** \
Citations: Course week5 assignment.md / docs/TASKS.md; Cursor IDE agent workflows (Warp Agent unavailable — TA approved Cursor equivalents).

This assignment took me about **TODO** hours to do. 


## YOUR RESPONSES
### Automation A: Cursor rules / commands (Warp Drive equivalent)

> Note: Warp Agent was unavailable in our environment. TA approved using Cursor as the Warp Drive / agentic IDE substitute. Automation A maps Warp Drive saved prompts/rules to Cursor project rules + reusable agent commands under `week5/`.

a. Design of each automation, including goals, inputs/outputs, steps
> **Goal:** Give every Cursor agent a stable, repo-local playbook for Week 5 tasks so list/search/pagination work stays consistent (API envelope `{items,total,...}`, page_size clamp at 100, SQLite `created_at`, static UI pagination) without re-explaining the starter each time.
>
> **Inputs:** Task id from `docs/TASKS.md` (e.g. Task 8 easy, Task 2 medium), path `week5/`, conda env `cs146s`, `make test`.
>
> **Outputs:** Focused diffs under `week5/backend`, `week5/frontend`, `week5/backend/tests`, plus green `make test`.
>
> **Steps:** (1) Read `docs/TASKS.md` + current routers/schemas/models. (2) Apply `.cursor/rules/week5-task-runner.mdc` constraints (paginate both collections, clamp page_size, register `/notes/search` before `/{note_id}`, update static UI not React). (3) Implement + extend pytest. (4) Run `make test` and fix until green.

b. Before vs. after (i.e. manual workflow vs. automated workflow)
> **Before:** Manually open each file, remember FastAPI route order pitfalls, rewrite list tests that still expect bare arrays, and rediscover that the starter UI is static HTML/JS (not React) every session.
>
> **After:** Cursor loads the week5 rule automatically; the agent already knows envelope shape, clamp policy, `created_at` migration, and static UI controls. One command-style prompt (“implement Task 8 then Task 2”) produces backend + frontend + tests in a single supervised pass.

c. Autonomy levels used for each completed task (what code permissions, why, and how you supervised)
> Full edit access limited to `week5/**`. Agent may run `make test` / lint. No git push, no edits outside week5. Supervised by reviewing the pagination envelope, search sort options, and test output before committing.

d. (if applicable) Multi‑agent notes: roles, coordination strategy, and concurrency wins/risks/failures
> N/A for Automation A (single-agent rule/command harness). Multi-agent coordination is covered in Automation B.

e. How you used the automation (what pain point it resolves or accelerates)
> Removes repeated context setup and “bare list vs `{items,total}`” regressions. Accelerates Task 8 (easy list pagination) and Task 2 (medium search + sort) by encoding acceptance checks that agents must satisfy before claiming done.



### Automation B: Multi‑agent workflows (two sequential Cursor agent chats)

> Warp multi-tab agents were unavailable; used two sequential Cursor agent chats as the multi-agent substitute (same coordination idea: separate agents own separate TASKS.md items).

a. Design of each automation, including goals, inputs/outputs, steps
> **Goal:** Split Week 5 implementation across agents so each owns one self-contained TASKS.md item and a clean handoff.
>
> **Agent 1 (Task 8 — easy):** Add `page`/`page_size` to `GET /notes` and `GET /action-items`, return `{items,total}`, clamp page_size to 100, update static list UI next/prev, update list tests (empty last page, oversized page_size).
>
> **Agent 2 (Task 2 — medium):** Add `created_at`, upgrade `GET /notes/search` with `q`/`page`/`page_size`/`sort`, case-insensitive title+content match, search UI + tests; consume Task 8’s paginated envelope so search stays consistent.
>
> **Handoff:** Agent 1 finishes when list endpoints + UI pager + list tests are green. Agent 2 starts from that tree, avoids reworking list pagination, focuses on search/sort/UI search box.

b. Before vs. after (i.e. manual workflow vs. automated workflow)
> **Before:** One long manual session mixing list pagination and search, easy to break list tests while adding search, or ship search still returning a bare array.
>
> **After:** Agent 1 locks the collection envelope; Agent 2 only composes filters/order/offset on top. Failures stay localized (list vs search).

c. Autonomy levels used for each completed task (what code permissions, why, and how you supervised)
> Each agent: edit `week5/**`, run tests. Human reviews the Task 8 diff before starting Task 2, then reviews search route registration order and sort tests. Commit only after full `make test` is green.

d. (if applicable) Multi‑agent notes: roles, coordination strategy, and concurrency wins/risks/failures
> **Roles:** Agent 1 = pagination owner; Agent 2 = search/sort owner.
> **Strategy:** Sequential (not parallel) to avoid clobbering the same routers on a shared worktree — Warp-style concurrent tabs would need `git worktree`; here sequential chats were safer.
> **Wins:** Clear ownership; Task 2 reused Task 8’s `Paginated` schema.
> **Risks/failures avoided:** Parallel edits to `notes.py`/`app.js` would conflict; sequential handoff removed that. Residual risk: Agent 2 must not revert list endpoints to bare arrays.

e. How you used the automation (what pain point it resolves or accelerates)
> Speeds delivery of two TASKS.md items with less merge pain and clearer review boundaries. Pain point resolved: one agent trying to hold all of pagination + search + UI + tests in working memory at once.


### (Optional) Automation C: Any Additional Automations
a. Design of each automation, including goals, inputs/outputs, steps
> Skipped — Automations A and B satisfy the two-automation requirement.

b. Before vs. after (i.e. manual workflow vs. automated workflow)
> N/A

c. Autonomy levels used for each completed task (what code permissions, why, and how you supervised)
> N/A

d. (if applicable) Multi‑agent notes: roles, coordination strategy, and concurrency wins/risks/failures
> N/A

e. How you used the automation (what pain point it resolves or accelerates)
> N/A