# BIT PHASE 1 ATOMIC TASK BREAKDOWN

**Methodology**: v1.4 contract-first task design  
**Total Tasks**: 10 sequential tasks + testing  
**Estimated Effort**: ~80–120 hours (depends on team size/parallelization)  
**Target Completion**: 2–3 weeks (solo), 1 week (pair)  

---

## TASK SEQUENCING LOGIC

```
Task 1  (Workspace) → Task 2  (Modes) → Task 3  (Intent)
                                               ↓
Task 4  (Job Spec) → Task 5  (Validation) → Task 6  (Planner Client)
                                               ↓
Task 7  (Approval) → Task 8  (Locking) → Task 9  (Workbee Stub)
                                               ↓
Task 10 (Minimal TUI Scaffold)
                                               ↓
INTEGRATION TESTING & ACCEPTANCE
```

**Dependency graph**: Each task depends on all previous tasks. No parallelization until all Tasks 1–9 complete.

---

## TASK 01: WORKSPACE BOOTSTRAP

### PURPOSE
Establish the foundational directory structure and lifecycle. Workspace is the authority boundary for all state.

### DELIVERABLES
- `bit init <path>` command (creates workspace)
- `bit ws open <path>` command (loads workspace)
- Workspace validation & error handling
- Unit + integration tests

### ACCEPTANCE CRITERIA
✅ `bit init /tmp/test_workspace` creates:
```
/tmp/test_workspace/
  bit.toml (with defaults)
  context/
    intent/        (empty, for intent artifacts)
  jobs/            (empty, for job specs)
  artifacts/       (empty, for Workbee outputs)
  logs/            (empty, for execution logs)
  cache/           (empty, for scratch data)
  scratch/
    session_state.json  (initial mode, empty job/intent refs)
```

✅ `bit ws open /tmp/test_workspace` validates structure and loads config

✅ Missing workspace: `bit ws open /nonexistent` → exit code 2 with message "Workspace not found at /nonexistent. Create with: bit init /nonexistent"

✅ Invalid workspace (missing required dir): error with clear recovery message

✅ Repeated `bit init` on same path: error "Workspace already exists. Open with: bit ws open <path>"

✅ Workspace survives exit/restart (all state on disk)

### KEY CONSTRAINTS
- Must create directories atomically (all succeed or fail together)
- bit.toml is required; defaults for all fields
- No external state (no /tmp usage, all within workspace)
- Deterministic output (same init args → identical workspace)

### IMPLEMENTATION HINTS
- Use `pathlib.Path` for path handling
- Create `bit.toml` with TOML library (tomli_w for writing)
- Directory creation uses `mkdir(parents=True, exist_ok=False)` (fail if exists)
- Validate directory structure after creation

### TEST MATRIX
| Input | Expected | Exit Code |
|-------|----------|-----------|
| `bit init /tmp/new` | Creates workspace | 0 |
| `bit init /tmp/new` (second run) | Error: exists | 2 |
| `bit init /nonexistent/path` | Error: parent missing | 2 |
| `bit ws open /tmp/new` | Opens workspace | 0 |
| `bit ws open /nonexistent` | Error: not found | 2 |
| `bit ws open /tmp/new` (with corrupted bit.toml) | Error: parse failed | 2 |

### COMPLEXITY ESTIMATE
**E: 6 hours** (includes basic error handling, tests)

---

## TASK 02: MODES + SESSION STATE

### PURPOSE
Implement mode management as a lightweight session concept. Modes bias prompting only; do not affect job schema or execution.

### DELIVERABLES
- Mode catalog (4 modes: chat, code, snap, xform)
- Session state file (`scratch/session_state.json`)
- `bit mode list` command
- `bit mode set <mode>` command
- `bit mode show` command
- Unit + integration tests

### ACCEPTANCE CRITERIA
✅ `bit mode list` shows:
```
Available modes:
  chat    - Conversational, exploratory
  code    - Code generation/review
  snap    - Markdown bullet summaries
  xform   - Pure transformation (no interpretation)
```

✅ `bit mode set code` updates session_state.json and prints "Mode set to: code"

✅ Mode persists across `bit` invocations (verified by re-running `bit mode show`)

✅ Mode changes do NOT affect job schema (verify by creating job in one mode, switching modes, re-opening job → schema identical)

✅ Invalid mode: `bit mode set invalid` → exit code 2 with message "Invalid mode. Available: chat, code, snap, xform"

✅ Session state file is valid JSON at all times (atomically written)

### KEY CONSTRAINTS
- Modes are configuration only (no code branching based on mode)
- Mode seed files live in `prompts/modes/<mode>.md`
- Session state is transient (does not affect reproducibility)
- Mode affects prompting only, not data model

### IMPLEMENTATION HINTS
- Load mode definitions from `prompts/modes/` directory
- Session state is small JSON file (mode_name, created_at, etc.)
- Use atomic file writes (temp file + rename)
- Mode defaults to "chat" on first init

### TEST MATRIX
| Command | Expected | Exit Code |
|---------|----------|-----------|
| `bit mode list` | Lists 4 modes | 0 |
| `bit mode set code` | Sets mode, updates state | 0 |
| `bit mode show` | Shows "code" | 0 |
| `bit mode set invalid` | Error: invalid | 2 |
| (restart bit) `bit mode show` | Still "code" | 0 |

### COMPLEXITY ESTIMATE
**E: 4 hours** (straightforward config + persistence)

---

## TASK 03: INTENT SYNTHESIS

### PURPOSE
Convert user input (chat/text) into mode-neutral intent.json artifact. Intent is the seed for job creation.

### DELIVERABLES
- Intent data model (Pydantic)
- Intent synthesis function
- `bit intent synth <text>` command
- Intent file I/O
- Unit + integration tests

### ACCEPTANCE CRITERIA
✅ `bit intent synth "Extract stems from /music/song.wav"` creates:
```json
{
  "intent_id": "intent-<uuid>",
  "created_at": "2026-02-03T10:00:00Z",
  "distilled_intent": "Extract audio stems from file /music/song.wav",
  "success_criteria": ["Stems extracted", "Saved in requested format"],
  "constraints": [],
  "candidate_inputs": [
    {"name": "input_file", "type": "file", "value": "/music/song.wav", "resolved": true}
  ],
  "candidate_outputs": [
    {"name": "stems_folder", "type": "folder", "expected_location": "artifacts/"}
  ],
  "provenance": {
    "mode_used": "chat",
    "session_refs": [],
    "created_by": "bit/v1.0"
  },
  "intent_hash": "<stable_hash>"
}
```

✅ File created at: `context/intent/intent-<uuid>.json`

✅ intent_hash is stable: same input → same hash

✅ Mode-neutral: intent structure and content do NOT depend on mode (mode_used recorded in provenance only)

✅ Empty input: `bit intent synth ""` → exit code 3 with message "Intent cannot be empty. Provide: bit intent synth <text>"

✅ Repeated synthesis with same text: Different intent_id (new UUID), same intent_hash

### KEY CONSTRAINTS
- Intent is mode-neutral (content does not change if mode changes)
- Mode is audit-only (recorded in provenance, not in intent body)
- intent_hash is computed from stable content (for reproducibility)
- All fields required (no null/missing values)

### IMPLEMENTATION HINTS
- Use Pydantic for intent validation
- UUID generation: `uuid.uuid4()`
- Hash: SHA256 of JSON-serialized intent (excluding intent_hash field itself)
- Timestamp: ISO8601 UTC
- Candidate inputs/outputs are inferred from text (basic pattern matching OK for Phase 1)

### TEST MATRIX
| Input | Expected | Exit Code |
|-------|----------|-----------|
| `bit intent synth "Extract stems"` | Creates intent.json | 0 |
| `bit intent synth ""` | Error: empty | 3 |
| Same text twice | Different IDs, same hash | 0 |
| Different text | Different hash | 0 |

### COMPLEXITY ESTIMATE
**E: 6 hours** (includes parsing, validation, file I/O, tests)

---

## TASK 04: JOB SPEC DRAFTING

### PURPOSE
Convert intent into executable job specification (job.yaml). Job spec is the contract with Planner and Workbee.

### DELIVERABLES
- Job data model (Pydantic, matching job_schema_v0.2)
- Job spec generation from intent
- `bit job from-intent <intent_id>` command
- Job file I/O (YAML)
- Unit + integration tests

### ACCEPTANCE CRITERIA
✅ `bit job from-intent intent-123` creates:
```yaml
# jobs/<job_id>/job.yaml
job_id: job-<uuid>
created_at: 2026-02-03T10:00:00Z
intent_ref: intent-123
intent_hash: abc123def456
status: DRAFT
mode_used: chat  # audit only
job_spec:
  title: "Extract stems from /music/song.wav"
  intent: "Extract audio stems from file /music/song.wav"
  success_criteria:
    - "Stems extracted"
  constraints: []
  inputs:
    - name: input_file
      type: file
      value: /music/song.wav
      required: true
  outputs:
    - name: stems_folder
      type: folder
      location: artifacts/
  approval_gates:
    required_on:
      - destructive_operations
      - large_compute_operations
job_spec_hash: <stable_hash>
```

✅ File created at: `jobs/<job_id>/job.yaml`

✅ job_spec_hash is stable: same job spec → same hash

✅ intent_hash is verified (must match stored intent)

✅ job_spec_hash embedded in YAML (for integrity checking)

✅ Intent not found: `bit job from-intent nonexistent` → exit code 3 with message "Intent not found: nonexistent. List intents: bit intent list"

✅ Job created in DRAFT state (not yet planned/approved)

### KEY CONSTRAINTS
- job_spec is derived from intent (deterministic mapping)
- mode_used is recorded but does not affect execution
- job_spec_hash enables integrity checking
- YAML is human-readable and editable (but changes would invalidate hash)

### IMPLEMENTATION HINTS
- Use Pydantic for job model
- YAML serialization: `toml` or YAML library (but spec uses YAML, not TOML)
- Actually use `yaml` library for YAML output
- Hash: SHA256 of normalized job_spec JSON
- job_id: UUID (different each time; intent_id is stable)

### TEST MATRIX
| Input | Expected | Exit Code |
|-------|----------|-----------|
| `bit job from-intent intent-123` | Creates job.yaml | 0 |
| `bit job from-intent nonexistent` | Error: not found | 3 |
| Job creation from same intent twice | Different job_ids | 0 |
| Hash verification | Matches stored | 0 |

### COMPLEXITY ESTIMATE
**E: 6 hours** (YAML parsing, validation, hashing, tests)

---

## TASK 05: SCHEMA VALIDATION & NORMALIZATION

### PURPOSE
Validate job.yaml against schema and normalize for deterministic processing.

### DELIVERABLES
- JSON normalization function
- Schema validation (Pydantic or JSON Schema)
- `bit job validate <job_id>` command (for debugging)
- Clear error messages (field-level)
- Unit + integration tests

### ACCEPTANCE CRITERIA
✅ Valid job.yaml passes validation silently (exit 0)

✅ Missing required field: Clear error listing field name and type
```
Error: Job spec validation failed
  - Field 'intent_ref' is required (type: uuid)
  - Field 'inputs[0].name' is required (type: string)
```

✅ Invalid value type: Clear error with expected type
```
Error: Job spec validation failed
  - Field 'status' must be one of: DRAFT, PLANNED, RUNNING, BLOCKED, SUCCEEDED, FAILED, CANCELLED
```

✅ Normalization: Multiple runs with identical input produce identical output (deterministic)

✅ Whitespace/ordering: Normalized (sorted dict keys in JSON representation)

### KEY CONSTRAINTS
- Validation is strict (no auto-correction)
- Normalization is deterministic (sorted output)
- Error messages are actionable (show the field and what's wrong)

### IMPLEMENTATION HINTS
- Use Pydantic for validation (raises ValidationError with field details)
- Normalization: convert YAML → JSON, sort keys, convert back (if needed)
- Error messages extract field path from Pydantic errors

### TEST MATRIX
| Input | Expected | Exit Code |
|-------|----------|-----------|
| Valid job.yaml | Pass | 0 |
| Missing intent_ref | Error: required | 2 |
| Invalid status | Error: enum | 2 |
| Malformed YAML | Error: parse | 2 |

### COMPLEXITY ESTIMATE
**E: 4 hours** (Pydantic validation is straightforward, error formatting takes time)

---

## TASK 06: PLANNER CLIENT

### PURPOSE
Communicate with Planner service (local for Phase 1). Request plan generation for approved jobs.

### DELIVERABLES
- Planner API client (HTTP/IPC)
- `bit plan <job_id>` command (request + display plan)
- Plan artifact storage
- Error handling (Planner unreachable, bad response)
- Unit + integration tests

### ACCEPTANCE CRITERIA
✅ `bit plan job-123` calls Planner and displays plan:
```json
{
  "job_id": "job-123",
  "plan_id": "plan-<uuid>",
  "plan_hash": "plan_hash_123",
  "steps": [
    {
      "step_id": "step-1",
      "description": "Validate audio file format",
      "worker": "audio_validator",
      "inputs": ["input_file"],
      "outputs": ["validation_result"],
      "gate": "none",
      "on_error": "fail"
    },
    {
      "step_id": "step-2",
      "description": "Extract stems using demucs",
      "worker": "stem_separator",
      "inputs": ["input_file"],
      "outputs": ["stems_folder"],
      "gate": "approval_required",
      "on_error": "fail"
    }
  ]
}
```

✅ Plan saved to: `jobs/<job_id>/plans/<plan_id>.json`

✅ Planner unreachable: exit code 4 with message "Planner at localhost:9000 is unreachable. Check: BIT_PLANNER_HOST, BIT_PLANNER_PORT"

✅ Job not found: exit code 3 with message "Job not found: <id>"

✅ Plan returned read-only (user cannot edit plan in bit; plan is authoritative from Planner)

### KEY CONSTRAINTS
- Plan is read-only in bit (just display)
- Planner is single source of truth for plan generation
- Plan format is defined by Planner (bit is a pass-through display)

### IMPLEMENTATION HINTS
- Use `requests` library for HTTP
- Planner endpoint: `POST /jobs/{job_id}/plan` with job_spec_hash
- Timeout: 30 seconds (configurable)
- Retry: None (user controls via re-run)
- Mock Planner for tests (return fixed plan JSON)

### TEST MATRIX
| Input | Expected | Exit Code |
|-------|----------|-----------|
| Valid job_id | Returns plan | 0 |
| Invalid job_id | Error: not found | 3 |
| Planner unreachable | Error: unreachable | 4 |
| Mock Planner returns bad JSON | Error: parse | 4 |

### COMPLEXITY ESTIMATE
**E: 5 hours** (HTTP client, error handling, mocking for tests)

---

## TASK 07: PLAN APPROVAL GATES

### PURPOSE
Enforce explicit user approval before plan dispatch. Approval is immutable and audited.

### DELIVERABLES
- Approval data model (approval_status object)
- `bit approve <job_id> <plan_id>` command
- `bit deny <job_id> <plan_id> --reason <reason>` command (optional)
- Approval audit logging
- Unit + integration tests

### ACCEPTANCE CRITERIA
✅ `bit plan <job_id>` shows plan (read-only)

✅ `bit approve job-123 plan-abc` approves plan:
```
Job job-123 approved for plan plan-abc at 2026-02-03T10:05:00Z
Run with: bit run job-123
```

✅ Approval stored in job.yaml: `approval_status: {approved_at, approved_by, approval_note}`

✅ Cannot dispatch without approval: `bit run job-123` (if not approved) → exit code 5 with message "Plan requires approval. Run: bit approve <job_id> <plan_id>"

✅ Multiple approvals: New approval overwrites old (immutable append, but latest wins)

✅ Deny plan: `bit deny job-123 plan-abc --reason "Unsafe outputs"` → updates status, logged, prevents dispatch

### KEY CONSTRAINTS
- Approval is explicit (no silent approval)
- Approval is immutable (logged, not revoked; can be overwritten)
- Approval gates prevent dispatch (hard boundary)

### IMPLEMENTATION HINTS
- approval_status: {approved_at: ISO8601, approved_by: string, approval_note: string}
- Update job.yaml atomically (temp file + rename)
- Log all approvals/denials to logs/

### TEST MATRIX
| Command | Expected | Exit Code |
|---------|----------|-----------|
| `bit approve <job> <plan>` | Approval stored | 0 |
| `bit run <job>` (unapproved) | Error: needs approval | 5 |
| `bit run <job>` (approved) | Proceeds to next step | 0 |
| `bit deny <job> <plan>` | Denial stored | 0 |

### COMPLEXITY ESTIMATE
**E: 4 hours** (simple YAML updates, audit logging)

---

## TASK 08: JOB LOCKING & INTERFERENCE GUARDRAILS

### PURPOSE
Prevent accidental operations on running jobs. Provide safe options (wait/status/halt/fork).

### DELIVERABLES
- Job lock mechanism (status-based)
- Guardrail prompt (if user tries to modify RUNNING job)
- `bit wait <job_id>` command (block until completion)
- `bit halt <job_id>` command (signal job to stop)
- Unit + integration tests

### ACCEPTANCE CRITERIA
✅ Job in RUNNING state: Job is "locked" (cannot be modified)

✅ `bit approve <job_id> <plan_id>` on RUNNING job → guardrail:
```
Error: Job job-123 is RUNNING.
Options:
  bit wait job-123          - Block until completion
  bit status job-123        - Check current state
  bit halt job-123          - Signal job to stop
  bit fork job-123          - Create new job from same intent
```

✅ Other jobs remain usable (no global lock; only on same job)

✅ `bit wait job-123` blocks until job completes (polls status)

✅ `bit halt job-123` sends halt signal to Workbee (job transitions to HALTED/CANCELLED)

✅ Status during RUNNING: Shows current step, progress, estimated time (if available)

### KEY CONSTRAINTS
- Lock is status-based (no separate lock file)
- Guardrails are helpful, not punitive
- Halting is graceful (gives workers time to clean up)

### IMPLEMENTATION HINTS
- Lock logic: Check job.status == RUNNING
- Wait loop: Poll status every 2 seconds, timeout 1 hour
- Halt: Call Workbee API (same as dispatch)
- Fork: Create new job from original intent (new job_id, same intent_ref)

### TEST MATRIX
| Action | Status | Expected | Exit Code |
|--------|--------|----------|-----------|
| Modify RUNNING job | RUNNING | Guardrail shown | 5 |
| Wait on job | RUNNING→SUCCEEDED | Unblock | 0 |
| Halt job | RUNNING | Halted | 0 |
| Other jobs during wait | RUNNING | Usable | 0 |

### COMPLEXITY ESTIMATE
**E: 5 hours** (status polling, guardrails, API integration)

---

## TASK 09: WORKBEE STUB RUNNER + ARTIFACTS

### PURPOSE
Stub implementation of Workbee for local testing. Executes dummy steps, generates artifacts.

### DELIVERABLES
- Workbee stub service (HTTP API)
- Stub job execution (walks steps)
- Artifact generation (manifest.json, report.md)
- Logging (jobs/<job_id>/logs/)
- Unit + integration tests

### ACCEPTANCE CRITERIA
✅ `bit run job-123` submits to stub Workbee:
```
POST /jobs
{
  "job_spec": "<full job.yaml content>",
  "job_spec_hash": "...",
  "intent_ref": "...",
  "intent_hash": "..."
}
```

✅ Workbee returns: `{status: "accepted", job_id: "job-123", run_id: "run-xyz"}`

✅ Job transitions: RUNNING → (steps complete) → SUCCEEDED

✅ Artifacts generated:
```
artifacts/job-123/
  manifest.json        (includes job_id, plan_hash, step_results)
  report.md            (execution summary)
logs/job-123/
  run-xyz.jsonl        (line-delimited JSON log entries)
```

✅ Log streaming: `bit tail job-123` follows logs in real-time

✅ Stub step execution: Each step takes <1 second (dummy work)

✅ Error simulation: Intentional failures work (step marked FAILED, logged)

### KEY CONSTRAINTS
- Stub is deterministic (no randomness, fixed outputs)
- Log entries are JSON (one per line)
- Manifest is valid JSON
- Report is markdown

### IMPLEMENTATION HINTS
- Workbee stub: simple FastAPI or Flask service (localhost:9001)
- Step execution: for loop over steps, sleep(0.5), mark complete
- Artifact templates: use f-strings for manifest/report
- Logging: JSON serialization of step results

### TEST MATRIX
| Action | Expected | Exit Code |
|--------|----------|-----------|
| Submit job | Returns run_id | 0 |
| Job completes | SUCCEEDED | 0 |
| Tail logs | Streams entries | 0 |
| List artifacts | Shows files | 0 |
| Open artifact | Displays content | 0 |

### COMPLEXITY ESTIMATE
**E: 8 hours** (stub service, artifact generation, logging, tests)

---

## TASK 10: MINIMAL TUI COCKPIT SCAFFOLD

### PURPOSE
Basic TUI layout showing key information. CLI is primary; TUI is minimal for Phase 1.

### DELIVERABLES
- TUI cockpit layout (Textual framework)
- Chat viewport (input + transcript)
- Context panel (mode, workspace, shortcuts)
- Job status panel (running jobs, progress)
- Action bar (quick buttons)
- Modal overlays (mode selection, approval)
- Unit + integration tests (TUI is hard to test; focus on data flow)

### ACCEPTANCE CRITERIA
✅ `bit` (no args) launches TUI cockpit

✅ Layout:
```
┌─────────────────────────────────────┬──────────────────┐
│ Chat Viewport (center)              │ Job Status (right)│
│                                     │ - Running jobs   │
│ > Send intent                       │ - Active step    │
│                                     │ - Progress       │
├─────────────────────────────────────┤──────────────────┤
│ Context (left)                      │ Actions (bottom) │
│ Mode: chat                          │ [Approve][Halt]  │
│ Workspace: /path/to/ws              │ [Open][Tail]     │
│ Last Intent: intent-123             │                  │
│ Last Job: job-456                   │                  │
└─────────────────────────────────────┴──────────────────┘
```

✅ Modal overlays:
- Mode selection: list + arrow keys to select
- Intent selection: list + search
- Job selection: list + search
- Approval: show plan summary + [Approve] [Deny]

✅ Chat viewport: Type intent, press Enter, creates intent artifact

✅ Input validation: Non-blocking (shows errors inline)

✅ Keyboard shortcuts:
- Ctrl+M: Mode selection modal
- Ctrl+J: Job selection modal
- Ctrl+A: Approval modal
- Ctrl+Q: Quit

✅ TUI remains responsive during background job (no blocking)

### KEY CONSTRAINTS
- TUI is optional (CLI works without it)
- TUI does not add business logic (all logic is in CLI commands)
- TUI is async/responsive (no freezing)
- TUI can be disabled via config (`tui_enabled = false`)

### IMPLEMENTATION HINTS
- Use `textual` library
- Separate components: Header, ChatViewport, ContextPanel, JobStatus, ActionBar
- Modal dialogs: inherited from Container
- Keyboard handling: bind keys to methods
- Data flow: TUI calls CLI functions (does not duplicate logic)

### TEST MATRIX
| Action | Expected |
|--------|----------|
| Launch TUI | Display cockpit |
| Type intent | Creates artifact |
| Ctrl+M | Mode modal shown |
| Select job | Highlighted |
| Ctrl+A | Approval modal |

### COMPLEXITY ESTIMATE
**E: 10 hours** (TUI is complex; use Textual docs heavily)

---

## INTEGRATION & ACCEPTANCE TESTING

### PURPOSE
Verify end-to-end flow: intent → job → approval → run → artifacts.

### ACCEPTANCE FLOW
```
1. bit init /tmp/test
2. bit intent synth "Extract stems from /test/audio.wav"
3. bit job from-intent <intent_id>
4. bit plan <job_id>
5. bit approve <job_id> <plan_id>
6. bit run <job_id>
7. bit ps  (shows RUNNING)
8. bit tail <job_id>  (shows logs streaming)
9. (wait for completion)
10. bit artifacts <job_id>  (lists artifacts)
11. bit open <job_id> manifest.json  (displays manifest)
```

### EXPECTED OUTCOMES
- All commands succeed with exit code 0
- Workspace is self-contained (all state in /tmp/test)
- Logs are deterministic (reproducible on re-run)
- Artifacts are valid (manifest is JSON, report is markdown)

### COMPLEXITY ESTIMATE
**E: 6 hours** (end-to-end scripting, edge case discovery)

---

## SUMMARY

| Task | Hours | Dependencies |
|------|-------|--------------|
| 1. Workspace | 6 | None |
| 2. Modes | 4 | Task 1 |
| 3. Intent | 6 | Task 1 |
| 4. Job Spec | 6 | Task 3 |
| 5. Validation | 4 | Task 4 |
| 6. Planner Client | 5 | Task 5 |
| 7. Approval | 4 | Task 6 |
| 8. Locking | 5 | Task 7 |
| 9. Workbee Stub | 8 | Task 8 |
| 10. TUI | 10 | Task 9 |
| Integration | 6 | Task 10 |
| **Total** | **64** | — |

**Estimate**: 64–80 hours (solo developer at 80% efficiency with testing)

---

## END ATOMIC TASK BREAKDOWN

Ready for Qwen3-coder-next. Each task is self-contained, testable, and sequenced to enable incremental progress.

