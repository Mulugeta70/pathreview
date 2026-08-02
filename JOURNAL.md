# PathReview Journal

## Week 7 — Issue selection

**Issue link:** https://github.com/ascherj/pathreview/issues/68

**Issue title:** Add a safety event count to the health check endpoint

**Tier:** [x] Tier 1  [ ] Tier 2  [ ] Tier 3

**Problem summary:**
The `/health` endpoint (`api/routes/health.py`) is supposed to report how many
safety events (PII detections, prompt injection attempts, bias flags, etc.)
have fired recently, via a `safety_events_last_hour` field in its JSON
response. Right now that field is a hardcoded placeholder that always returns
`0`, so operators watching `/health` have no real signal into safety-system
activity and have to go check a separate monitoring dashboard instead. The
`SafetyMonitor` class in `safety/monitoring.py` already tracks per-event-type
counts in Redis and exposes a `get_event_count()` method, so a correct fix
wires the health route up to that existing monitor (summed across the valid
event types) instead of inventing new tracking logic. A successful fix
replaces the placeholder with a real count and keeps the endpoint resilient
if Redis is unreachable.

**Branch name:** fix/68-safety-events-health-check

**Setup confirmation:** [x] App runs locally at localhost:5173

**Cohort ledger:** [x] Issue added to cohort ledger

## Week 8 — Reproduction & solution planning

**Reproduction commit link:** https://github.com/Mulugeta70/pathreview/commit/a6bc4d35ea9c9074c12ed34b48aa76fcbd805fb8

**Reproduction summary:**
Added `tests/unit/test_health_safety_events.py`, which mocks Redis to
report a recorded `pii_detected` safety event and calls `health_check()`
directly. The test fails with `assert 0 == 1`: `safety_events_last_hour`
comes back `0` even though a real event was "recorded," because
`api/routes/health.py` never reads from `SafetyMonitor` — it just hardcodes
the field. Postgres, Redis, and vector DB dependency checks all report
healthy in the test, isolating the failure to exactly this field. Also
found and documented (in PLAN.md, out of scope for this fix) that
`core/config.py`'s `Settings` has no `redis_host`/`redis_port`, only
`redis_url`, which makes `health.py`'s real Redis dependency check always
fail with a silently-swallowed `AttributeError`.

**PLAN.md link:** https://github.com/Mulugeta70/pathreview/blob/fix/68-safety-events-health-check/PLAN.md

**Walkthrough video (recommended):**

**Blockers or open questions:**
Need to confirm with a mentor whether the `redis_host`/`redis_port` vs
`redis_url` bug should be fixed as a prerequisite in this same PR (since a
working Redis client is needed either way to read safety event counts) or
filed as a separate issue. Also unsure whether "last hour" should be taken
literally — `SafetyMonitor`'s Redis keys currently use a flat 24-hour TTL
with no actual hourly bucketing, so an honest fix may need to either rework
the storage scheme or relabel the field's real semantics. Noted both in
PLAN.md's Risks & unknowns section.

## Week 9 — Solution building & PR submission

### Check-in 1 (mid-week)

**Current progress:**
Implemented the fix end to end: added `SafetyMonitor.get_total_event_count()`
(`safety/monitoring.py`) to sum `get_event_count()` across
`VALID_EVENT_TYPES`, and wired `api/routes/health.py` to call it through a
Redis client built from `settings.redis_url` (kept separate from the
pre-existing, out-of-scope `redis_host`/`redis_port` bug in the dependency
check above it). Resolved both open questions from Week 8's PLAN.md myself
rather than blocking on a mentor: left the `redis_host`/`redis_port` bug
alone (documented, separate issue) since the new client sidesteps it
entirely, and kept the "last hour" field name with an honest doc-comment
about the underlying 24h TTL rather than reworking the storage scheme.
Turned the single reproduction test into a full suite
(`tests/unit/test_health_safety_events.py`: zero events, single type,
multiple types summed, Redis unavailable, client-construction failure) and
added `tests/unit/test_safety_monitoring.py` for the new
`SafetyMonitor.get_total_event_count()` method directly. Verified against a
real Redis instance (not just mocks) that logged events are correctly
reflected in `/health`. All sub-tasks from PLAN.md's Plan section (steps
1-5) are done.

**Next steps:**
Open the draft PR, get peer/mentor feedback, then mark ready for review.

**Blockers:**
None.

---

### Check-in 2 (end of week)

**PR link:** https://github.com/ascherj/pathreview/pull/535

**Branch:** `fix/68-safety-events-health-check`

**What you built:**
`/health`'s `safety_events_last_hour` field was hardcoded to `0`. It now
calls a new `SafetyMonitor.get_total_event_count()` helper that sums real
per-event-type counts from Redis (PII detections, injection attempts,
content filtering, bias flags, rate limiting), via a Redis client scoped to
the safety check so it's unaffected by an unrelated, pre-existing
`redis_host`/`redis_port` bug in the health route's dependency check. A
Redis failure degrades the count to `0` without marking `/health` overall
unhealthy.

**Tests added or updated:**
- `tests/unit/test_health_safety_events.py` — rewritten from a single
  reproduction case into 5 tests covering the `/health` endpoint: no
  events, one event type, multiple event types summed, Redis unavailable,
  and safety-client construction failure.
- `tests/unit/test_safety_monitoring.py` (new) — 9 tests for
  `SafetyMonitor`, including `get_total_event_count()`'s summing,
  zero-event, partial-event-type, and partial-Redis-error behavior.

**Self-review confirmation:** [x] make check passes  [x] make test-unit passes
(53 pre-existing unit-test failures and 175 pre-existing ruff errors remain,
all unrelated to this change — see PR description for the documented
baseline; my changes introduce zero new failures.)

**Draft PR feedback received from:** none
