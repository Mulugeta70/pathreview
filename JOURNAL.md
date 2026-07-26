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

**Reproduction commit link:** [to be filled in after commit — see below]

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

**PLAN.md link:** [PLAN.md](./PLAN.md) (root of this fork, branch
`fix/68-safety-events-health-check`)

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
