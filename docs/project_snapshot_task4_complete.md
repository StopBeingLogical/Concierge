# Concierge Project Snapshot - Task 4 Complete

**Date**: 2026-02-04
**Phase**: 1 (MVP)
**Status**: Tasks 1-4 Complete, Ready for Task 5
**Location**: `/Volumes/Shuttle/WORKING/projects/concierge`

---

## Executive Summary

The Concierge personal AI orchestration system is a structured, deterministic, auditable task execution platform. The user-facing shell (`bit`) has completed its foundational layer (Tasks 1-4), establishing:

- Workspace management
- Mode-based context
- Intent synthesis from natural language
- Job specification generation

**Next Phase**: Task Package Registry + Planner Integration (Tasks 5-10)

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ CONCIERGE SYSTEM OVERVIEW                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│ User Input (Natural Language)                                  │
│     ↓                                                           │
│ [bit CLI] - Tasks 1-4 ✅ COMPLETE                              │
│     │                                                           │
│     ├─ Intent Synthesis (Task 3)                               │
│     │   └─ Distills user text into structured intent           │
│     │                                                           │
│     └─ Job Spec Drafting (Task 4)                              │
│         └─ Converts intent → executable job.yaml               │
│                                                                 │
│     ↓ Job YAML (status: DRAFT)                                 │
│                                                                 │
│ [Planner] - Tasks 5-6 🔲 PLANNED                               │
│     │                                                           │
│     ├─ Task Package Registry (Task 5)                          │
│     │   └─ Declarative recipes for common tasks                │
│     │                                                           │
│     └─ Package Matching (Task 6)                               │
│         └─ Match job spec → best task package                  │
│                                                                 │
│     ↓ Execution Plan                                           │
│                                                                 │
│ [Approval Gate] - Task 7 🔲 PLANNED                            │
│     └─ User reviews/approves plan before execution             │
│                                                                 │
│     ↓ Job YAML (status: APPROVED)                              │
│                                                                 │
│ [Router] - Tasks 8-9 🔲 PLANNED                                │
│     └─ Executes pipeline steps with stub workers               │
│                                                                 │
│     ↓ Events + Artifacts                                       │
│                                                                 │
│ [Monitoring] - Task 10 🔲 PLANNED                              │
│     └─ Real-time status display and log streaming              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Completed Tasks (1-4)

### TASK 1: Workspace Bootstrap ✅

**Deliverables**:
- Workspace initialization: `bit init <path>`
- Directory structure: `context/`, `jobs/`, `artifacts/`, `logs/`, `cache/`, `scratch/`
- Workspace validation
- Configuration file: `workspace.json`

**Files**:
- `bit/workspace.py` (125 lines)
- `tests/test_workspace.py` (8 tests)

**Key Concepts**:
- Workspace is the authority boundary for all state
- All operations scoped to a workspace
- Deterministic structure (same init args → identical workspace)

---

### TASK 2: Modes + Session State ✅

**Deliverables**:
- Mode catalog (4 modes: chat, code, snap, xform)
- Session state file: `context/session_state.json`
- CLI commands: `bit mode list`, `bit mode set <mode>`, `bit mode show`

**Files**:
- `bit/modes.py` (120 lines)
- `tests/test_modes.py` (17 tests)

**Key Concepts**:
- Modes bias prompting only (UX hint)
- Modes do NOT affect job schema or execution
- Mode recorded in job provenance (audit only)
- Session persists across CLI invocations

---

### TASK 3: Intent Synthesis ✅

**Deliverables**:
- Rule-based intent extraction from natural language
- Intent artifact storage: `artifacts/intent_<hash>.json`
- Deterministic hashing (UUID v5 from content hash)
- CLI commands: `bit intent synth`, `bit intent list`, `bit intent show`, `bit intent verify`

**Files**:
- `bit/intent.py` (314 lines)
- `tests/test_intent.py` (31 tests)

**Intent Schema**:
```python
class Intent(BaseModel):
    intent_id: str              # UUID v5 (deterministic from hash)
    mode: str                   # Mode when created
    distilled_intent: str       # First sentence or 100 chars
    success_criteria: str       # How to measure success
    constraints: list[str]      # Limiting factors
    created_at: str             # ISO8601 timestamp
    intent_hash: str            # SHA256 of canonical content
```

**Key Features**:
- Pattern matching for success criteria extraction
- Constraint extraction (must use, cannot, within, etc.)
- Deterministic hashing (same text → same hash)
- Canonical representation (sorted fields)

---

### TASK 4: Job Spec Drafting ✅

**Deliverables**:
- Job specification models (JobSpec, Job)
- Intent → Job transformation
- Job storage: `jobs/<job_id>/job.yaml` (human-readable YAML)
- Job integrity verification (job_spec_hash, intent_hash)
- CLI commands: `bit job from-intent`, `bit job list`, `bit job show`, `bit job validate`

**Files**:
- `bit/job.py` (356 lines)
- `tests/test_job.py` (52 tests)

**Job Schema**:
```yaml
job_id: job-<uuid4>                    # Random UUID v4
created_at: "2026-02-04T10:00:00Z"
intent_ref: <intent_id>
intent_hash: <sha256>
status: draft                          # draft → planned → approved → running → completed/failed
mode_used: code                        # Audit only

job_spec:
  title: "Extract stems from /music/song.wav"
  intent: "Extract stems from /music/song.wav"
  success_criteria:
    - "Stems extracted and saved"
  constraints:
    - "Must use demucs"
  inputs: []                           # Empty, filled by planner
  outputs:
    - name: artifacts
      type: folder
      location: "artifacts/"
  approval_gates:
    required_on:
      - destructive_operations
      - large_compute_operations

job_spec_hash: <sha256>                # Hash of job_spec only
```

**Key Features**:
- Random job IDs (same intent can spawn multiple jobs)
- Deterministic job_spec hashing
- Human-readable YAML storage
- Jobs created in DRAFT status
- Intent hash verification before creation

---

## Project Statistics

### Code Metrics
- **Total Lines**: ~1,780 lines
  - `bit/workspace.py`: 125 lines
  - `bit/modes.py`: 120 lines
  - `bit/intent.py`: 314 lines
  - `bit/job.py`: 356 lines
  - `bit/cli.py`: 632 lines
  - Tests: ~1,200 lines

### Test Coverage
- **Total Tests**: 132 passing
  - Workspace: 8 tests
  - Modes: 17 tests
  - Intent: 31 tests
  - Job: 52 tests
  - CLI: 24 tests

### Dependencies
```toml
dependencies = [
    "pydantic>=2.0",      # Data validation
    "typer>=0.9",         # CLI framework
    "rich>=13.0",         # Terminal formatting
    "requests>=2.31",     # HTTP client
    "toml>=0.10",         # TOML parsing
    "textual>=0.40",      # TUI framework (future)
    "pyyaml>=6.0",        # YAML serialization
]
```

---

## Current File Structure

```
concierge/
├── bit/
│   ├── __init__.py
│   ├── workspace.py          ✅ Task 1 - Workspace management
│   ├── modes.py              ✅ Task 2 - Mode catalog + session state
│   ├── intent.py             ✅ Task 3 - Intent synthesis
│   ├── job.py                ✅ Task 4 - Job spec generation
│   └── cli.py                ✅ CLI commands for all tasks
│
├── tests/
│   ├── test_workspace.py     ✅ 8 tests
│   ├── test_modes.py         ✅ 17 tests
│   ├── test_intent.py        ✅ 31 tests
│   ├── test_job.py           ✅ 52 tests
│   └── test_cli.py           ✅ 24 tests
│
├── docs/
│   ├── sources/
│   │   └── bit_phase1_atomic_tasks.md   # Original task plan
│   └── project_snapshot_task4_complete.md  # This document
│
├── pyproject.toml            ✅ Project configuration
├── pytest.ini                ✅ Test configuration
├── README.md                 ✅ Project overview
└── .gitignore                ✅ Git ignore rules
```

### Example Workspace Structure

After initialization, a workspace contains:

```
/tmp/test_workspace/
├── workspace.json                        # Workspace metadata
├── context/
│   └── session_state.json                # Active mode, timestamps
├── jobs/
│   └── job-ec0b7609-5654-4491-8b62-e202c1e8e51e/
│       └── job.yaml                      # Job specification
├── artifacts/
│   └── intent_b8f63336765da015.json      # Intent artifacts
├── logs/                                 # Event logs (future)
├── cache/                                # Determinism cache (future)
└── scratch/                              # Temporary files
```

---

## CLI Command Reference

### Workspace Commands
```bash
bit init <path>                           # Initialize new workspace
bit ws open <path>                        # Open/validate workspace
bit ws show                               # Show active workspace info
```

### Mode Commands
```bash
bit mode list                             # List all available modes
bit mode set <mode> --path <workspace>    # Set active mode
bit mode show --path <workspace>          # Show current mode
```

### Intent Commands
```bash
bit intent synth --text "..." --path <workspace>    # Synthesize intent
bit intent list --path <workspace>                  # List all intents
bit intent show --hash <hash> --path <workspace>    # Show intent details
bit intent verify --hash <hash> --path <workspace>  # Verify intent integrity
```

### Job Commands
```bash
bit job from-intent --intent-id <id> --path <workspace>    # Create job from intent
bit job list --path <workspace>                            # List all jobs
bit job show --job-id <id> --path <workspace>              # Show job details
bit job validate --job-id <id> --path <workspace>          # Verify job integrity
```

---

## Planned Tasks (5-10)

### TASK 5: Task Package Schema + Registry Bootstrap 🔲

**Purpose**: Define task package structure and create registry system

**Deliverables**:
- Task Package Pydantic models (14 sections)
- Package Registry class (filesystem-based)
- CLI: `bit package list/show/validate`
- 1-2 seed test packages

**Complexity**: 12 hours

---

### TASK 6: Planner Integration 🔲

**Purpose**: Match job specs to task packages and generate execution plans

**Deliverables**:
- Planner engine (intent → package matching)
- Execution Plan model
- CLI: `bit plan <job_id>`
- Pattern matching + confidence scoring

**Complexity**: 10 hours

---

### TASK 7: Approval Gates + Job State Machine 🔲

**Purpose**: Implement approval workflow and job status transitions

**Deliverables**:
- Approval model (immutable records)
- Job state machine (DRAFT → PLANNED → APPROVED → RUNNING → COMPLETED)
- CLI: `bit approve/deny <job_id>`
- Approval display UI

**Complexity**: 6 hours

---

### TASK 8: Router Stub + Event System 🔲

**Purpose**: Execute plans with mock workers and emit events

**Deliverables**:
- Router engine (pipeline execution)
- Event system (JSONL logs)
- Mock workers (stub implementations)
- CLI: `bit run <job_id>`

**Complexity**: 8 hours

---

### TASK 9: Monitoring + Log Display 🔲

**Purpose**: Display job progress and logs in real-time

**Deliverables**:
- Log reader (parse JSONL events)
- CLI: `bit status/tail/artifacts <job_id>`
- Real-time log streaming

**Complexity**: 5 hours

---

### TASK 10: Integration Testing 🔲

**Purpose**: Verify complete workflow end-to-end

**Deliverables**:
- Integration tests (full workflow)
- Real example package (audio.echo)
- CLI workflow documentation

**Complexity**: 6 hours

---

## Phase 1 Total Effort Estimate

| Tasks | Status | Effort |
|-------|--------|--------|
| 1-4 | ✅ Complete | ~24 hours |
| 5-10 | 🔲 Planned | ~47 hours |
| **Total** | **Phase 1 MVP** | **~71 hours** |

---

## Key Design Principles

### 1. Determinism
- Same inputs → same outputs
- Canonical representations (sorted collections)
- Deterministic hashing (content-based IDs)
- No timestamps in hash computation

### 2. Human Authority
- User is always in control
- All goals originate with user
- Explicit approvals for destructive/large operations
- No silent actions

### 3. Separation of Concerns
```
Thinking (Planner) ≠ Routing (Router) ≠ Execution (Workers) ≠ Memory
```

### 4. Mode Neutrality
- Mode affects UX only (prompting bias)
- Mode does NOT affect execution
- Same intent → same job regardless of mode
- Mode recorded for audit

### 5. Auditability
- All state on disk (no hidden state)
- Immutable records (append-only logs)
- Hash verification at each stage
- Provenance tracking (tool versions, timestamps)

---

## Next Steps

**Immediate**: Implement Task 5 (Package Schema + Registry)

**Rationale**:
- Foundation for Planner (Task 6)
- Can be developed independently
- Defines contracts for downstream work
- Includes seed packages for testing

**Expected Deliverables**:
- Complete `TaskPackage` Pydantic model
- `PackageRegistry` class with CRUD operations
- CLI commands for package management
- 2 test packages demonstrating schema
- ~400 lines of tests

---

## References

### Design Documents
- Phase 1 Atomic Tasks: `docs/sources/bit_phase1_atomic_tasks.md`
- Consolidated Vision: `/Volumes/Shuttle/Concierge With Claude/Outputs/bit_consolidated_vision_final.md`
- Project Spec: `/Volumes/Shuttle/Concierge With Claude/Outputs/bit_project_spec_v1_0.md`

### Key Schemas
- Intent Schema: `bit/intent.py:15-50`
- Job Schema: `bit/job.py:120-165`
- Task Package Schema: Defined in Explore agent report (Task 5 planning)

### Testing
- All tests: `pytest tests/ -v`
- Single module: `pytest tests/test_job.py -v`
- Coverage: `pytest --cov=bit tests/`

---

## Glossary

**Intent**: Structured representation of user's natural language request
**Job**: Executable specification derived from an intent
**Task Package**: Declarative recipe for executing a specific type of job
**Planner**: Matches intents to task packages and generates execution plans
**Router**: Stateless executor that walks pipeline steps
**Worker**: Single-purpose executor (deterministic input → output)
**Approval Gate**: User checkpoint before execution of certain operations
**Mode**: UX bias for intent capture (chat, code, snap, xform)
**Workspace**: Authority boundary containing all project state

---

**Document Version**: 1.0
**Last Updated**: 2026-02-04
**Status**: Current as of Task 4 completion
