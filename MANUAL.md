# Concierge Manual (Development)

Quick reference for Concierge components and commands. For detailed architecture, see ARCHITECTURE.md.

## SYSTEM OVERVIEW

Concierge converts natural language intents into executable task workflows with approval gates and event tracking.

**Flow**: Intent → Job → Plan → Approval → Execution → Monitoring

## CORE COMPONENTS

### Workspace
Root directory containing all project state. Initialize with `bit init`.
- `intents/` - Synthesized user intents
- `jobs/` - Job specifications and execution state
- `packages/` - Task package registry (declarative recipes)
- `concierge.json` - System configuration

### Intent
Structured representation of user intent extracted from natural language.
- Synthesized from free-form text
- Includes distilled description, success criteria, constraints
- Deterministically hashed for identity
- Stored as JSON in `intents/` directory

### Job
Executable task specification derived from an intent.
- Status: DRAFT → PLANNED → APPROVED → RUNNING → COMPLETED/FAILED/HALTED
- Contains job spec, approval log, references intent
- Stored as YAML in `jobs/<job_id>/job.yaml`
- Includes inputs, outputs, approval gates

### Task Package
Declarative recipe for a specific type of task.
- 14-section specification: identity, intent, contracts, pipeline, approval, verification, failure-handling, resources, metadata + 6 reserved
- YAML-based, filesystem stored: `packages/<category>/<name>/v<version>/package.yaml`
- Defines: pipeline steps, input/output contracts, resource requirements, approval policies
- Examples: `test.echo`, `audio.normalize`, `file.compress`, `data.validate`

### Execution Plan
Concrete execution strategy derived from job + matched package.
- Resolves inputs from job spec to package inputs
- Aggregates resource requirements from pipeline
- Lists steps with workers and parameters
- Stored in `jobs/<job_id>/plans/<plan_id>.yaml`

### Router
Executes approved plans sequentially on local machine.
- Walks pipeline steps in order
- Invokes workers with context-based input/output
- Emits events for monitoring
- Creates immutable JSONL event logs

### Event Log
Immutable append-only record of job execution.
- JSONL format: one JSON event per line
- Event types: job.*, step.*, worker.*, approval.*
- Stored in `jobs/<job_id>/logs/run-<run_id>.jsonl`
- Used for monitoring, debugging, audit trails

### Configuration
Centralized settings for planner, router, approval, workers, caching.
- Stored in `concierge.json` in workspace
- Includes: confidence thresholds, timeouts, resource limits, worker enable/disable
- Managed via `bit config` commands

---

## COMMANDS

### Workspace Management

**`bit init <PATH>`**
Initialize a new workspace at PATH.
- Creates directory structure
- Initializes concierge.json with defaults
- Example: `bit init ~/myworkspace`

**`bit ws open --path <PATH>`**
Set active workspace for current session.
- Persists in session state
- Required before other commands
- Example: `bit ws open --path ~/myworkspace`

**`bit ws show`**
Display current workspace path and structure.

**`bit ws validate`**
Check workspace integrity (all required directories/files exist).

### Mode Management

**`bit mode list`**
List available modes: chat, code, snap, xform.
- Modes represent context/use case for intents

**`bit mode set --name <MODE>`**
Set active mode for current session.
- Requires workspace to be open
- Affects intent synthesis
- Example: `bit mode set --name code`

**`bit mode show`**
Display current mode.

### Intent Synthesis

**`bit intent synth --text "<TEXT>"`**
Synthesize intent from natural language text.
- Extracts: distilled description, success criteria, constraints
- Generates deterministic hash for identity
- Creates intent JSON file in `intents/` directory
- Example: `bit intent synth --text "Normalize audio volume in my podcast"`

**`bit intent list`**
List all synthesized intents.
- Shows intent hash, text, timestamp
- Sorted by creation date

**`bit intent show --hash <HASH>`**
Display intent details by hash (full or partial).
- Shows all synthesized fields
- Example: `bit intent show --hash 2a3f`

**`bit intent verify --hash <HASH>`**
Verify intent hash integrity (data hasn't changed).

### Job Management

**`bit job from-intent --intent-id <HASH>`**
Create job specification from synthesized intent.
- Transitions intent → job
- Job created in DRAFT status
- Example: `bit job from-intent --intent-id 2a3f`

**`bit job list`**
List all jobs with status and timestamps.
- Shows: job_id, status, intent hash, created_at

**`bit job show --job-id <JOB_ID>`**
Display job details including spec, approvals, status.
- Shows full job YAML content
- Example: `bit job show --job-id j_abc123`

**`bit job validate --job-id <JOB_ID>`**
Verify job integrity (hashes match, structure valid).

### Package Management

**`bit package list`**
List all task packages in registry.
- Shows: package_id, version, category, approval_required
- Example output: `audio.normalize v1.0.0 (approval required)`

**`bit package show --package-id <PKG_ID>`**
Display package specification details.
- Shows full 14-section schema
- Example: `bit package show --package-id audio.normalize`

**`bit package search --query <QUERY>`**
Search packages by name, verbs, or entities.
- Uses keyword matching
- Example: `bit package search --query "compress"`

**`bit package validate --package-id <PKG_ID>`**
Verify package schema and integrity.
- Checks: all required sections, valid pipeline, input/output contracts

### Plan Generation

**`bit plan generate --job-id <JOB_ID>`**
Match job to task package and generate execution plan.
- Transitions job: DRAFT → PLANNED
- Uses Planner to find best-matching package
- Creates ExecutionPlan with resolved inputs/resources
- Shows matched package, confidence score
- Example: `bit plan generate --job-id j_abc123`

**`bit plan list --job-id <JOB_ID>`**
List all plans generated for a job.
- Shows plan_id, created_at, matched_package

**`bit plan show --job-id <JOB_ID> --plan-id <PLAN_ID>`**
Display plan details: matched package, pipeline, resources.

### Approval Gates

**`bit approve --job-id <JOB_ID> [--note "<NOTE>"]`**
Approve a planned job.
- Transitions job: PLANNED → APPROVED
- Adds approval record with timestamp, approver, note
- Example: `bit approve --job-id j_abc123 --note "Looks good"`

**`bit deny --job-id <JOB_ID> [--reason "<REASON>"]`**
Deny a planned job.
- Job stays in PLANNED status (can re-plan)
- Adds denial record
- Example: `bit deny --job-id j_abc123 --reason "Need to adjust parameters"`

### Execution

**`bit run --job-id <JOB_ID>`**
Execute an approved job.
- Requires job in APPROVED status
- Transitions: APPROVED → RUNNING → COMPLETED/FAILED
- Invokes router to execute pipeline
- Creates run record and event log
- Example: `bit run --job-id j_abc123`

### Monitoring

**`bit status --job-id <JOB_ID>`**
Show current job status and execution progress.
- Displays: current status, current step, elapsed time
- Shows latest events
- Example: `bit status --job-id j_abc123`

**`bit tail --job-id <JOB_ID> [--lines N] [--run-id <RUN_ID>]`**
Stream job execution logs in real-time.
- Default: 10 most recent lines
- Shows formatted events with timestamps
- Example: `bit tail --job-id j_abc123 --lines 20`

**`bit artifacts --job-id <JOB_ID>`**
List job artifacts (outputs, intermediate results).
- Shows: artifact name, size, modification time
- Example: `bit artifacts --job-id j_abc123`

### Configuration

**`bit config get [--component <NAME>]`**
Show current configuration.
- Without --component: show full config
- With --component: show planner, router, approval, cache, workers
- Example: `bit config get --component planner`

**`bit config set <COMPONENT> <KEY> <VALUE>`**
Update configuration setting.
- Example: `bit config set planner confidence_threshold 0.85`
- Example: `bit config set router max_parallel_steps 4`

**`bit config worker enable|disable <WORKER_ID>`**
Enable or disable specific worker.
- Example: `bit config worker enable audio_normalizer`

---

## WORKFLOW EXAMPLE

```bash
# Initialize and open workspace
bit init ~/myworkspace
bit ws open --path ~/myworkspace

# Set mode
bit mode set --name code

# Synthesize intent from natural language
bit intent synth --text "Normalize the audio volume in my podcast"
# Output: Intent hash e2a3f...

# Create job from intent
bit job from-intent --intent-id e2a3f
# Output: Job ID j_xyz789

# Generate execution plan (matches to package)
bit plan generate --job-id j_xyz789
# Output: Matched audio.normalize v1.0.0 with 0.92 confidence

# Review and approve
bit job show --job-id j_xyz789
bit approve --job-id j_xyz789 --note "Looks good to go"

# Execute
bit run --job-id j_xyz789

# Monitor execution
bit status --job-id j_xyz789
bit tail --job-id j_xyz789 --lines 20

# View results
bit artifacts --job-id j_xyz789
```

---

## JOB LIFECYCLE

```
DRAFT
  ↓ (bit plan generate)
PLANNED
  ↓ (bit approve)
APPROVED
  ↓ (bit run)
RUNNING
  ↓ (execution succeeds)
COMPLETED

  OR (execution fails)
FAILED

  OR (user halt)
HALTED
```

Can return to PLANNED from APPROVED via `bit deny` for re-planning.

---

## FILE STRUCTURE

```
workspace/
├── intents/
│   └── <hash>.json          # Synthesized intents
├── jobs/
│   └── <job_id>/
│       ├── job.yaml         # Job specification + state
│       ├── plans/
│       │   └── <plan_id>.yaml
│       └── logs/
│           └── run-<run_id>.jsonl
├── packages/
│   ├── test/
│   │   └── echo/v1.0.0/package.yaml
│   ├── audio/
│   │   └── normalize/v1.0.0/package.yaml
│   ├── file/
│   │   └── compress/v1.0.0/package.yaml
│   └── data/
│       └── validate/v1.0.0/package.yaml
├── concierge.json           # Configuration
└── .concierge/
    └── session.json         # Session state (mode, timestamps)
```

---

## KEY CONCEPTS

**Deterministic Hashing**: Intents, jobs, packages, plans have deterministic hashes. Same inputs always produce same hash. Used for identity and verification.

**Event Log (JSONL)**: Immutable append-only log. Each line is a JSON event. Supports filtering, tailing, parsing for monitoring.

**Confidence Scoring**: Planner matches intents to packages using keyword extraction + verb/entity scoring (0.0-1.0). Ambiguity detected if multiple matches above threshold.

**State Machine**: Jobs progress through strict state transitions with guard conditions. Invalid transitions rejected (e.g., can't run unapproved job).

**Context-based Execution**: Router maintains runtime context (key-value dict) across pipeline steps. Worker outputs become inputs for downstream steps.

---

## NOTES

- All timestamps are ISO 8601 with Z suffix (UTC)
- YAML files are human-readable and version-control friendly
- JSONL logs are streamable and parseable
- Configuration persists across sessions in workspace
- Session state (mode, timestamps) in `.concierge/session.json`
- Approval logs are immutable (append-only)
