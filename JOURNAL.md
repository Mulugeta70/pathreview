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
