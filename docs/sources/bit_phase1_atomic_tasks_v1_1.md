# bit Phase 1 Atomic Tasks v1.1

**Status**: 10 sequential tasks + integration testing  
**Total estimate**: 64 hours (solo at 80% efficiency)  
**Dependencies**: Control plane philosophy + WEC principles locked

---

## CONTEXT

Each task is vertical slice (end-to-end): code + tests + docs.

**Key constraints from WEC** (Phase 1 principles):
- All outputs are artifacts (files/logs), not prose
- Approval gates before execution (hard requirement)
- Determinism (same input = same output, verifiable)
- No silent decisions (all logged)

---

## TASK 1: Workspace Bootstrap (6 hours)

**Objective**: Create and validate workspace structure

**CLI commands**: `bit init`, `bit ws open`

**Deliverables**:
- Workspace directory structure
  ```
  workspace/
  ├── context/        (active session state)
  ├── jobs/           (job specs + plans)
  ├── artifacts/      (outputs + logs)
  ├── logs/           (event log)
  ├── cache/          (determinism cache)
  └── scratch/        (temp files, safe to delete)
  ```
- Workspace metadata (config.toml, validation)
- Validation: directory created, survives restart

**Acceptance**: `bit ws open` reads workspace; all directories exist and valid

---

## TASK 2: Modes + Session State (4 hours)

**Objective**: Implement reasoning bias modes (don't affect job schema)

**CLI commands**: `bit mode list`, `bit mode set`, `bit mode show`

**Modes**: chat, code, snap, xform

**Deliverables**:
- Mode catalog (read-only)
- Session state (current mode persisted in context/)
- Validation: mode persists across commands, doesn't change job schema

**Acceptance**: Mode set/get works; mode info in job provenance only

---

## TASK 3: Intent Synthesis (6 hours)

**Objective**: Synthesize mode-neutral intents

**CLI command**: `bit intent synth <text>`

**Deliverables**:
- Intent schema (YAML/JSON)
  ```yaml
  intent_id: uuid
  mode: chat|code|snap|xform
  distilled_intent: "..."
  success_criteria: "..."
  constraints: [...]
  created_at: timestamp
  intent_hash: deterministic_hash
  ```
- Artifact creation (stored in artifacts/)
- Hash stability (same input = same hash)
- Validation: intent_hash verifiable

**Acceptance**: Intent created; hash stable across runs

---

## TASK 4: Job Spec Drafting (6 hours)

**Objective**: Draft job from intent

**CLI command**: `bit job from-intent <intent_id>`

**Deliverables**:
- Job YAML schema
  ```yaml
  job_id: uuid
  intent_ref: intent_id
  intent_hash: hash
  job_spec_hash: hash
  status: DRAFT
  created_at: timestamp
  ```
- Job spec validation (Pydantic)
- Hashes locked (immutable after creation)

**Acceptance**: Job YAML created; both hashes stable; status is DRAFT

---

## TASK 5: Schema Validation (4 hours)

**Objective**: Validate job/intent schemas

**CLI command**: `bit job validate <job_id>`

**Deliverables**:
- Pydantic models (intent, job)
- Field-level error messages (clear, actionable)
- Deterministic output (same input = same errors)
- Validation: errors are explicit, no silent coercion

**Acceptance**: Invalid jobs rejected with clear field errors; valid jobs pass

---

## TASK 6: Planner Client (5 hours)

**Objective**: HTTP client to Planner service

**CLI command**: `bit plan <job_id>`

**Deliverables**:
- HTTP client (localhost:5000 default, configurable)
- Request format: POST /plan (intent, context)
- Response handling: plan artifact + confidence
- Fallback: if Planner unreachable, show error (not silent)
- Storage: plan saved to jobs/<id>/plans/

**Acceptance**: Plan requested, displayed, saved; Planner unreachable handled gracefully

---

## TASK 7: Approval Gates (4 hours)

**Objective**: Hard approval requirement before execution

**CLI commands**: `bit approve <job_id> <plan_id>`, `bit deny`

**Deliverables**:
- Approval schema (timestamp, approver, note)
- Storage: approval stored in job.yaml (immutable)
- Audit: denials logged to event log
- Enforcement: cannot run without approval

**Acceptance**: Cannot dispatch without approval; denials logged; approvals immutable

---

## TASK 8: Job Locking & Interference Guards (5 hours)

**Objective**: Prevent interference with running jobs

**CLI commands**: `bit wait`, `bit halt`, `bit fork`

**Deliverables**:
- Job state locking (RUNNING jobs locked)
- Guardrail menu (show available actions)
- Wait semantics (block until complete)
- Halt semantics (pause, not kill)
- Fork semantics (copy running job + reapply intent)
- Validation: modification blocked, other jobs unaffected

**Acceptance**: RUNNING jobs locked; wait/halt work; other jobs usable

---

## TASK 9: Workbee Stub + Artifacts (8 hours)

**Objective**: Stub Workbee service (localhost:9001)

**CLI command**: `bit run <job_id>`

**Deliverables**:
- Workbee HTTP stub service (localhost:9001)
  - POST /jobs (submit job)
  - GET /jobs/{id}/status (poll status)
- Step execution (deterministic, same input = same output)
- Artifact generation
  ```
  artifacts/<job_id>/
  ├── manifest.json
  ├── report.md
  └── logs/
      └── execution.jsonl
  ```
- Event streaming: events sent to bit
- Validation: job submitted, completes, artifacts created

**Acceptance**: Job submitted; completes; artifacts created; logs streamed

---

## TASK 10: Minimal TUI Scaffold (10 hours)

**Objective**: TUI cockpit (Textual framework)

**Deliverables**:
- Layout: chat center, context left, job status right
- Modals: mode selector, intent drafter, approval gates
- Keyboard shortcuts: Ctrl+M (mode), Ctrl+J (job), Ctrl+A (approve), Ctrl+Q (quit)
- Real-time job status (polling from Workbee)
- No blocking operations

**Acceptance**: Launches, responsive, keyboard shortcuts work, no blocking

---

## INTEGRATION TESTING (6 hours)

**Objective**: End-to-end flow

**Test flow**:
```
1. bit init
2. bit intent synth "test intent"
3. bit job from-intent <intent_id>
4. bit plan <job_id>
5. bit approve <job_id>
6. bit run <job_id>
7. bit fg <job_id> (follow logs)
8. Verify artifacts created + verifiable
```

**Acceptance**: All commands succeed; workspace self-contained; outputs deterministic

---

## TASK SEQUENCING

```
Task 1 (Workspace) → Task 2 (Modes) → Task 3 (Intent) → Task 4 (Job)
    ↓                   ↓               ↓               ↓
Sequential path, no parallelization until Task 5

Task 5 (Validation) → Task 6 (Planner) → Task 7 (Approval)
    ↓                 ↓                 ↓
Sequential

Task 8 (Locking) → Task 9 (Workbee) → Task 10 (TUI)
    ↓              ↓                 ↓
Sequential

Integration Testing (all together)
```

**No parallelization until Tasks 1-9 complete.**

---

## DESIGN NOTES

### Determinism
- All operations use fixed seeds
- Hashes are stable (content-addressable)
- Timestamps mocked in tests
- Same input always produces same output

### Approval Gates
- Non-negotiable before execution
- Logged immutably
- Cannot be bypassed or auto-approved

### Artifact-First
- Workbee produces files/logs, not prose
- Manifest.json describes all outputs
- All outputs hashed + verifiable

### Local Workbee
- Phase 1 stub on localhost:9001
- Stateless (rehydrate context per request)
- HTTP polling (bit pulls status, no push)
- Simple mock implementation (sync execution)

### No Silent Decisions
- Every operation logged to event log
- Failures explicit (not hidden)
- Audit trail immutable

---

## ACCEPTANCE CRITERIA (PHASE 1 COMPLETE)

- [x] All 10 tasks implemented
- [x] Integration test passes (intent → execution)
- [x] Artifacts reproducible
- [x] Approval gates functional
- [x] Event log immutable
- [x] No hidden intelligence
- [x] Workspace self-contained
- [x] All outputs deterministic
- [x] CLI usable
- [x] Tests comprehensive (unit + integration)

