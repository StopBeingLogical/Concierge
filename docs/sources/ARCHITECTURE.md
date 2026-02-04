# Concierge Architecture & Implementation Guide

Complete technical reference for Concierge system design, data flow, and extensibility.

## Table of Contents

1. [System Architecture](#system-architecture)
2. [Data Models](#data-models)
3. [Component Details](#component-details)
4. [Data Flow](#data-flow)
5. [Extension Points](#extension-points)
6. [Performance Considerations](#performance-considerations)

## System Architecture

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Concierge System                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐ │
│  │   CLI Interface  │  │   Intent Manager │  │  Session Manager │ │
│  │                  │  │                  │  │                  │ │
│  │ Commands:        │  │ - Synthesize     │  │ - Load State     │ │
│  │ - intent         │  │ - Store          │  │ - Save State     │ │
│  │ - job            │  │ - Verify         │  │ - Get Mode       │ │
│  │ - package        │  │                  │  │                  │ │
│  │ - plan           │  │                  │  │                  │ │
│  │ - approve/deny   │  │                  │  │                  │ │
│  │ - run            │  │                  │  │                  │ │
│  │ - status/tail    │  │                  │  │                  │ │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘ │
│           │                      │                      │            │
├───────────┼──────────────────────┼──────────────────────┼───────────┤
│           ▼                      ▼                      ▼            │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐ │
│  │  Job Manager     │  │ Package Registry │  │ Plan Manager     │ │
│  │                  │  │                  │  │                  │ │
│  │ - Create Job     │  │ - Store Package  │  │ - Save Plan      │ │
│  │ - State Machine  │  │ - List Packages  │  │ - Load Plan      │ │
│  │ - Approval Logs  │  │ - Validate       │  │ - List Plans     │ │
│  │ - Persistence    │  │ - Search         │  │ - Get Latest     │ │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘ │
│           │                      │                      │            │
├───────────┼──────────────────────┼──────────────────────┼───────────┤
│           ▼                      ▼                      ▼            │
│  ┌──────────────────────────┐          ┌──────────────────────────┐ │
│  │     Planner Engine       │          │    Router Engine         │ │
│  │                          │          │                          │ │
│  │ - Match Intent → Package │          │ - Execute Pipeline      │ │
│  │ - Confidence Scoring     │          │ - Manage Context        │ │
│  │ - Ambiguity Detection    │          │ - Invoke Workers        │ │
│  │ - Input Resolution       │          │ - Event Emission        │ │
│  │ - Resource Aggregation   │          │ - Failure Handling      │ │
│  └──────────┬───────────────┘          └──────────┬───────────────┘ │
│             │                                      │                  │
├─────────────┼──────────────────────────────────────┼──────────────────┤
│             ▼                                      ▼                  │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │            Event System & Log Reader                         │   │
│  │                                                              │   │
│  │ - Event Emission (job, step, worker events)                │   │
│  │ - JSONL Log Storage                                        │   │
│  │ - Event Filtering & Querying                              │   │
│  │ - Status Display & Monitoring                             │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │            Worker Registry & Stub Implementations            │   │
│  │                                                              │   │
│  │ - EchoWorker (test/demonstration)                          │   │
│  │ - FileWorker (file operations)                             │   │
│  │ - CounterWorker (data counting)                            │   │
│  │ - SleepWorker (timing/delays)                              │   │
│  │ - Extensible WorkerStub base class                         │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │            Storage & Persistence                             │   │
│  │                                                              │   │
│  │ - Workspace (structured directories)                       │   │
│  │ - YAML/JSON serialization                                  │   │
│  │ - Git-friendly format                                      │   │
│  │ - Deterministic hashing                                    │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### Execution Flow Diagram

```
User Intent (Natural Language)
    │
    ▼
┌─────────────────────┐
│ Intent Synthesis    │  Extract: distilled_intent, success_criteria, constraints
│ (IntentSynthesizer) │  Generate: intent_hash, intent_id
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Create Job          │  Create: job_id, job_spec, status=DRAFT
│ (JobManager)        │  Persist: jobs/<job_id>/job.yaml
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Transition to PLAN  │  Update: status → PLANNED
│ (State Machine)     │
└──────────┬──────────┘
           │
           ▼
┌──────────────────────────────────┐
│ Package Matching & Planning       │  Extract keywords from intent
│ (Planner + PlanManager)           │  Filter packages by category
│                                  │  Score packages (0.0-1.0)
│ 1. Extract keywords              │  Select best match
│ 2. Filter packages               │  Resolve inputs
│ 3. Score matches                 │  Aggregate resources
│ 4. Select winner                 │  Create plan
│ 5. Resolve inputs                │  Persist: jobs/<job_id>/plans/<plan_id>.yaml
│ 6. Create plan                   │
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│ Approval Gate                    │  Display plan summary
│ (Approval System)                │  Wait for approval
│                                  │  Record approval decision
│ ◄─ Approve  / Deny ─►            │  Update: status → APPROVED or stay PLANNED
│                                  │
└──────────┬───────────────────────┘
           │ (Approved)
           ▼
┌──────────────────────────────────┐
│ Transition to RUNNING            │  Update: status → RUNNING
│ (State Machine)                  │
└──────────┬───────────────────────┘
           │
           ▼
┌──────────────────────────────────┐
│ Pipeline Execution               │  Initialize context with resolved inputs
│ (Router)                         │  For each step:
│                                  │    - Emit: step.started event
│ For step in pipeline:            │    - Collect inputs from context
│   - Load inputs from context     │    - Invoke worker with inputs+params
│   - Invoke worker                │    - Write outputs to context
│   - Write outputs to context     │    - Emit: step.completed event
│   - Emit events                  │  Emit: job.completed event
│                                  │  Persist: jobs/<job_id>/logs/run-<run_id>.jsonl
└──────────┬───────────────────────┘
           │
    ┌──────┴──────┐
    │             │
    ▼ (Success)   ▼ (Failure)
┌─────────────┐ ┌─────────────┐
│ Completed   │ │   Failed    │
│ status→OK   │ │ status→ERR  │
└─────────────┘ └─────────────┘
    │             │
    └─────┬───────┘
          ▼
┌──────────────────────────────────┐
│ Monitoring & Artifact Access     │  Query logs (tail, filter)
│ (LogReader)                      │  Get job status
│                                  │  List artifacts
│ - View logs                      │  Display execution summary
│ - Check status                   │
│ - Access artifacts               │
└──────────────────────────────────┘
```

## Data Models

### Intent Model

```
Intent
├── intent_id: str (UUID v5, deterministic)
├── intent_hash: str (SHA256 of canonical content)
├── mode: str (chat, code, snap, xform)
├── distilled_intent: str (concise summary, <100 chars)
├── success_criteria: str (measurement of success)
├── constraints: list[str] (limiting factors)
├── created_at: str (ISO 8601 timestamp)
└── to_canonical_dict(): dict (for hashing)
```

Storage: `artifacts/intent_<hash[:16]>.json`

### Job Model

```
Job
├── job_id: str (UUID v4)
├── status: JobStatus (DRAFT → PLANNED → APPROVED → RUNNING → COMPLETED/FAILED/HALTED)
├── created_at: str (ISO 8601)
├── intent_ref: str (reference to intent ID)
├── intent_hash: str (hash of referenced intent)
├── mode_used: str (audit trail)
├── job_spec: JobSpec
│   ├── title: str
│   ├── intent: str
│   ├── success_criteria: list[str]
│   ├── constraints: list[str]
│   ├── inputs: list[JobInput]
│   ├── outputs: list[JobOutput]
│   └── approval_gates: ApprovalGates
├── job_spec_hash: str (SHA256)
└── approvals: list[Approval] (append-only log)
```

Storage: `jobs/<job_id>/job.yaml`

### Package Model

```
TaskPackage (14 sections)
├── 1. Identity & Versioning
│   ├── package_id: str (category.name format)
│   ├── version: str (semver)
│   ├── title: str
│   └── description: str
├── 2. Intent Matching
│   └── intent: IntentSpec
│       ├── category: str
│       ├── verbs: list[str]
│       ├── entities: list[str]
│       ├── confidence_threshold: float
│       └── match_rules: list[str]
├── 3. Input Contract
│   └── input_contract: Contract
│       └── fields: list[ContractField]
├── 4. Output Contract
│   └── output_contract: Contract
├── 5. Pipeline
│   └── pipeline: Pipeline
│       └── steps: list[PipelineStep]
│           ├── step_id: str
│           ├── worker: Worker
│           ├── inputs: list[str]
│           ├── outputs: list[str]
│           └── params: dict
├── 6. Approval
│   └── approval: ApprovalPolicy
├── 7. Verification
│   └── verification: Verification
├── 8. Failure Handling
│   └── failure_handling: FailureHandling
├── 9. Resources
│   └── resources: ResourceProfile
├── 10. Metadata
│   └── metadata: dict
└── (11-14 reserved for future)
```

Storage: `packages/<category>/<name>/v<version>/package.yaml`

### Plan Model

```
ExecutionPlan
├── plan_id: str (UUID v4)
├── created_at: str (ISO 8601)
├── job_id: str (reference)
├── package_id: str (matched package)
├── package_version: str
├── matched_confidence: float (0.0-1.0)
├── resolved_inputs: ResolvedInputs
│   └── inputs: list[ResolvedInput]
│       ├── name: str
│       ├── type: str
│       └── value: any
├── pipeline: Pipeline (from matched package)
├── resources: ResourceRequirements
│   ├── total_cpu_cores: int
│   ├── gpu_required: bool
│   ├── total_memory_mb: int
│   └── total_disk_mb: int
└── compute_hash(): str
```

Storage: `jobs/<job_id>/plans/<plan_id>.yaml`

### Event Model

```
Event
├── type: EventType (job.started/completed/failed, step.started/completed/failed, etc.)
├── timestamp: str (ISO 8601)
├── run_id: str
├── job_id: str
├── step_id: str (optional)
├── worker_id: str (optional)
├── payload: dict (event-specific data)
└── to_jsonl(): str (single-line JSON)
```

Storage: `jobs/<job_id>/logs/run-<run_id>.jsonl` (one event per line)

## Component Details

### Intent Synthesis

**File**: `bit/intent.py`

Converts natural language to structured intent using pattern matching:

```python
class IntentSynthesizer:
    - Extract distilled intent (first sentence or truncate to 100 chars)
    - Extract success criteria (patterns: "success is", "should", "must")
    - Extract constraints (patterns: "must use", "cannot", "within")
    - Generate canonical hash (SHA256 of sorted JSON)
    - Generate deterministic UUID v5
```

**Confidence**: 100% deterministic (same input always produces same hash/UUID)

### Package Registry

**File**: `bit/registry.py`

Manages task package storage and discovery:

```python
class PackageRegistry:
    - add_package(package) → Path
    - get_package(id, version) → Package
    - list_packages(category) → list[Package]
    - search_packages(category, verbs, entities) → list[Package]
    - validate_package(package) → list[str] (errors)
```

**Storage Structure**:
```
packages/
├── audio/
│   ├── normalize/v1.0.0/package.yaml
│   └── extract/v1.0.0/package.yaml
├── file/
│   └── compress/v1.0.0/package.yaml
└── data/
    └── validate/v1.0.0/package.yaml
```

### Planner Engine

**File**: `bit/planner.py`

Matches jobs to packages using confidence scoring:

```python
class Planner:
    - match_package(job_spec) → (Package, float)
    - match_packages_with_ambiguity(job_spec) → (list[(Package, float)], bool)
    - generate_plan(job, package, confidence) → ExecutionPlan

    Matching Algorithm:
    1. Extract keywords from intent (remove stop words, min length 2)
    2. Filter packages by category (optional)
    3. For each package:
        - Check verb matches (bonus +0.2 per match)
        - Check entity matches
        - Check category matches
        - Compute score: matches/keywords + verb_bonus
    4. Filter above confidence threshold
    5. Return best match or detect ambiguity
```

**Scoring**: 0.0 (no match) to 1.0+ (multiple matches)

### Router Engine

**File**: `bit/router.py`

Executes plans sequentially with worker invocation:

```python
class Router:
    - execute_plan(plan) → (bool, RunRecord)

    Execution:
    1. Create run record
    2. Initialize context with resolved inputs
    3. For each step:
        a. Emit step.started event
        b. Collect inputs from context
        c. Invoke worker (mock stub)
        d. Write outputs to context
        e. Emit step.completed event
    4. Emit job.completed event
    5. Return success/failure
```

**Worker Registry**:
- Echo: echoes input with timestamp
- File: simulates file operations
- Sleep: delays for timing
- Counter: counts items

### Event System

**File**: `bit/events.py`

Tracks execution events in JSONL format:

```python
class EventLog:
    - emit(event) → write to JSONL file
    - read() → list[Event]
    - filter_by_type(EventType) → list[Event]
    - filter_by_step(step_id) → list[Event]
    - get_latest() → Event
    - tail(n) → list[Event] (last n)
```

**JSONL Format**: One JSON object per line, no multi-line events

## Extension Points

### Add Custom Worker

```python
# in bit/workers_stub.py
from bit.workers_stub import WorkerStub

class CustomWorker(WorkerStub):
    def execute(self, inputs: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
        """Custom worker implementation."""
        # Process inputs
        result = do_something(inputs['input_name'])
        return {'output_name': result}

# Register in Router
Router.WORKERS['custom_worker'] = CustomWorker()
```

### Create Task Package

```yaml
# packages/category/name/v1.0.0/package.yaml
package_id: category.name
version: 1.0.0
title: Package Title
description: What this package does
intent:
  category: category
  verbs: [verb1, verb2]
  entities: [entity1, entity2]
  confidence_threshold: 0.75
input_contract:
  fields:
    - name: input_name
      type: file/string/integer/etc
      description: Input description
      required: true
output_contract:
  fields:
    - name: output_name
      type: file/string/etc
      description: Output description
      required: true
pipeline:
  steps:
    - step_id: step_1
      worker:
        worker_id: worker_name
        version: 1.0.0
      inputs: [input_name]
      outputs: [output_name]
      params: {}
approval:
  required: false
  conditions: []
verification:
  required: false
  rules: []
failure_handling:
  modes: []
resources:
  cpu_cores: 1
  gpu_required: false
  memory_mb: 512
  disk_mb: 1000
metadata:
  created_at: "2026-02-04T00:00:00Z"
  author: user
  tags: [tag1, tag2]
```

### Custom Intent Synthesis

Override patterns in `IntentSynthesizer`:

```python
# Extend patterns for specialized domains
SUCCESS_PATTERNS = [
    r"(?:should|must|needs to|will)\s+([^.!?]+[.!?])",
    # Add custom patterns
    r"goal is\s+([^.!?]+[.!?])",
]

CONSTRAINT_PATTERNS = [
    # Add domain-specific patterns
    r"within\s+([^,]+)",
]
```

## Performance Considerations

### Scaling

| Component | Current Capacity | Notes |
|-----------|-----------------|-------|
| Packages | <1000 | Filesystem-based search |
| Jobs | <10000 | YAML file per job |
| Plans | <100K | One file per plan |
| Events | Unlimited | JSONL append-only |
| History | Unlimited | Versioned by run_id |

### Optimization Opportunities

1. **Caching**
   - Cache package list (cache_ttl_seconds)
   - Cache intent hashes
   - Cache plan generation results

2. **Parallel Execution**
   - Router currently sequential
   - Could parallelize independent steps
   - Resource limits would prevent contention

3. **Indexing**
   - Add database for package search
   - Index intent keywords
   - Cache confidence scores

4. **Compression**
   - Compress old log files
   - Archive completed jobs
   - Deduplicate artifacts

### Memory Profile

Typical job execution:
- Intent: ~500 bytes
- Job: ~2 KB
- Plan: ~5 KB
- Per-event: ~200 bytes
- Total for 100-step job: ~30 KB

Multi-step pipeline (1000 steps):
- Runtime context: ~1 MB (depends on data)
- Event log: ~200 KB
- Total: ~300 KB

## Configuration Management

**File**: `bit/config.py`

```python
class ConfigManager:
    - load() → ConciergeConfig
    - save(config) → Path
    - get_planner_config() → PlannerConfig
    - get_router_config() → RouterConfig
    - get_approval_config() → ApprovalConfig
    - update_planner_config(updates) → None
    - enable_worker(id) → None
    - disable_worker(id) → None
```

Configuration stored in: `concierge.json`

Default values are used if file doesn't exist.
