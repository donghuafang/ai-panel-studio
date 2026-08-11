# Task 7 Report: 讨论编排引擎

## Status: COMPLETE

## Summary
Created `backend/app/services/orchestration_service.py` — the `DiscussionOrchestrator` class, the core orchestration engine for AI Panel Studio.

## Files Created
- `backend/app/services/orchestration_service.py` (327 lines)

## Commits
- `e2540ae` — feat: add DiscussionOrchestrator - core orchestration engine (Task 7)
- (current) — fix: address 3 important findings from code review (I1, I2, I4)

## Implementation Details

### DiscussionOrchestrator class

| Method | Purpose |
|--------|---------|
| `__init__()` | Initialize event queues dict + threading lock |
| `subscribe(discussion_id)` | Register SSE client, return its dedicated `asyncio.Queue` |
| `unsubscribe(discussion_id, queue)` | Unregister SSE client |
| `_broadcast(discussion_id, event, data)` | Thread-safe broadcast to all subscribers |
| `_build_context(speeches, guests)` | Build LLM message context from prior speeches |
| `run_discussion(session_factory, discussion_id)` | Full auto-discussion in background thread |
| `_set_agent_state(db, guest, state)` | Update and persist guest agent state |
| `_save_speech(...)` | Persist a speech record and return it |
| `_speech_to_event(speech)` | Convert Speech ORM to SSE event dict |
| `_generate_summary(...)` | LLM-driven consensus + divergence extraction |

### Discussion Flow (per round)
1. Host opening/guidance speech (intro on round 1, synthesis on subsequent rounds)
2. Each expert speaks in sequence with stance-aligned views
3. Host round summary extracting key points
4. State transitions broadcast: idle -> thinking -> speaking -> ready

### Post-discussion
- LLM extracts consensus items (with supporter guest IDs)
- LLM extracts divergence items (with opposing guest name pairs)
- Name-to-ID mapping resolves LLM output to database guest IDs
- `discussion_ended` SSE event with final consensus/divergence payloads

### Global Singleton
- `orchestrator = DiscussionOrchestrator()` at module level

## Verification

### Import Test
Command: `cd backend && python -c "from app.services.orchestration_service import orchestrator; print('Orchestrator singleton created OK')"`

**Note:** Python runtime not available in current environment. Manual code review performed instead:

- All imports verified against existing project modules:
  - `backend.app.models` exports `Discussion`, `Guest`, `Speech`, `Consensus`, `Divergence` — confirmed
  - `backend.app.services.llm_client.LLMClient` — confirmed with `generate_speech()`, `chat_completion()` methods
  - All stdlib imports (`asyncio`, `json`, `threading`, `datetime`) are standard
- Code transcribed exactly from task brief — diff verification passed

## Self-Review Checklist

- [x] Code matches the task brief exactly
- [x] All imports resolve to existing project modules
- [x] Class structure: event queue management, broadcast, discussion execution, summary generation
- [x] Thread safety: `threading.Lock` guards all queue mutations
- [x] SSE events: `guest_state_changed`, `speech_added`, `consensus_updated`, `divergence_updated`, `discussion_ended`, `error`
- [x] Database session management: proper commit/refresh patterns, session closed in `finally`
- [x] Error handling: try/except broadcasts error event, session always closed
- [x] Global singleton exported for use by routers and other services
- [x] File committed to git

## Concerns
- None. The implementation is a direct transcription of the approved task brief.

## Post-Review Fixes (2026-08-11)

Three important findings addressed:

| ID | Issue | Fix |
|----|-------|-----|
| I1 | Missing `db.rollback()` on error path | Added `db.rollback()` before error broadcast in `run_discussion` except block |
| I2 | Discussion status not persisted as failed | Set `discussion.status = "error"` with best-effort `db.commit()` after rollback |
| I4 | `_generate_summary` JSON failure causes silent loss | Wrapped JSON parse + consensus/divergence save logic in try/except; summary failure is best-effort, discussion still ends |
