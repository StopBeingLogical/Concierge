# Concierge Workflow Guide

Complete guide to using Concierge for task automation and orchestration.

## Table of Contents

1. [Overview](#overview)
2. [Getting Started](#getting-started)
3. [Core Concepts](#core-concepts)
4. [Complete Workflow](#complete-workflow)
5. [CLI Reference](#cli-reference)
6. [Advanced Usage](#advanced-usage)
7. [Troubleshooting](#troubleshooting)

## Overview

Concierge is a personal AI orchestration system that converts natural language intents into executable task workflows. The system manages the entire lifecycle: intent capture → job specification → plan generation → approval → execution → monitoring.

### Key Components

- **Intent**: Natural language description of what you want to do
- **Job**: Structured specification derived from intent
- **Package**: Declarative recipe defining how to execute tasks
- **Plan**: Execution plan matched from job to package
- **Run**: Single execution instance of a plan

## Getting Started

### 1. Initialize a Workspace

```bash
bit init /path/to/workspace
```

Creates directory structure:
```
workspace/
├── context/       # Session state
├── jobs/          # Job specifications
├── artifacts/     # Output artifacts
├── logs/          # Event logs
├── cache/         # Determinism cache
└── scratch/       # Temporary files
```

### 2. Open the Workspace

```bash
bit ws open --path /path/to/workspace
```

This makes the workspace active for subsequent commands.

### 3. Set a Mode

```bash
bit mode set --path /path/to/workspace --name code
```

Modes: `chat`, `code`, `snap`, `xform`. Affects intent synthesis reasoning.

## Core Concepts

### Intent

Raw natural language description of a task:

```bash
bit intent synth --text "Normalize the audio volume in my podcast episodes"
```

Output:
- `intent_hash`: SHA256 hash of intent content
- `intent_id`: Deterministic UUID v5
- `distilled_intent`: Concise summary
- `success_criteria`: How to measure success
- `constraints`: Limiting factors

### Job

Structured specification derived from intent:

```bash
bit job from-intent --intent-id abc123def456...
```

Output:
- `job_id`: Unique identifier
- `job_spec`: Detailed specification
- `status`: DRAFT → PLANNED → APPROVED → RUNNING → COMPLETED

### Package

Declarative recipe defining how to execute a task type:

```bash
bit package list
bit package show --package-id audio.normalize
bit package validate --package-id audio.normalize
```

Package anatomy (14 sections):
1. **Identity**: package_id, version, title, description
2. **Intent Matching**: category, verbs, entities, confidence rules
3. **Input Contract**: required/optional inputs and types
4. **Output Contract**: expected outputs and formats
5. **Pipeline**: ordered execution steps
6. **Approval**: policies requiring user approval
7. **Verification**: post-execution validation rules
8. **Failure Handling**: error recovery strategies
9. **Resources**: CPU, memory, disk requirements
10. **Metadata**: creation date, tags, dependencies
11-14: Reserved for future expansion

### Plan

Execution plan matched from job to package:

```bash
bit plan generate --job-id job-xxx
```

Plan includes:
- Matched package and confidence score
- Resolved inputs from job spec
- Complete pipeline with worker definitions
- Aggregated resource requirements

## Complete Workflow

### Step-by-Step Example: Audio Normalization

#### 1. Create Intent

```bash
bit intent synth --text "I need to normalize the volume levels in my podcast audio files to -14 LUFS loudness. The output should preserve the dynamic range."
```

Output:
```
✓ Intent synthesized
Hash: a1b2c3d4e5f6g7h8...
ID: 550e8400-e29b-41d4-a716-446655440000
Mode: code
Distilled: Normalize the volume levels in podcast audio files...
Success: Audio normalized to -14 LUFS with dynamic range preserved
```

#### 2. Create Job

```bash
bit job from-intent --intent-id a1b2c3d4e5f6g7h8...
```

Output:
```
✓ Job created
Job ID: job-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
Status: draft
Intent Ref: 550e8400-e29b-41d4-a716-446655440000
Mode: code
```

#### 3. List and Review Packages

```bash
bit package list --category audio
```

Output:
```
Package ID          Version  Title                  Category
─────────────────────────────────────────────────────────
audio.normalize     1.0.0    Audio Normalization    audio
audio.extract       1.0.0    Audio Stem Extraction  audio
```

#### 4. Generate Execution Plan

```bash
bit plan generate --job-id job-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

Output:
```
✓ Plan generated
Plan ID: plan-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
Package: audio.normalize v1.0.0
Confidence: 95%
Pipeline Steps: 2
File: jobs/job-xxx/plans/plan-xxx.yaml
```

#### 5. Review Plan Details

```bash
bit plan show --job-id job-xxx --plan-id plan-xxx
```

Output:
```
Plan: plan-xxx
Job ID: job-xxx
Package: audio.normalize v1.0.0
Confidence: 95%
Created: 2026-02-04T12:00:00Z
Pipeline Steps: 2
CPU Cores: 2
Memory (MB): 1024
```

#### 6. Approve the Plan

```bash
bit approve job-xxx --note "Audio looks good, proceed with normalization"
```

Output:
```
✓ Job approved
Job ID: job-xxx
Plan ID: plan-xxx
Status: approved
Note: Audio looks good, proceed with normalization
```

#### 7. Execute the Job

```bash
bit run job-xxx
```

Output:
```
Executing job job-xxx
Plan: plan-xxx
Pipeline Steps: 2
✓ Job completed successfully
Run ID: run-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
Duration: 2026-02-04T12:05:30Z
```

#### 8. Monitor Execution

```bash
bit status job-xxx
```

Output:
```
Status: completed
Title: Normalize the audio volume...
Intent: Normalize the audio volume in my podcast episodes
Created: 2026-02-04T12:00:00Z
Current Step: step_2_normalize
Total Events: 8
Latest Event: job.completed
```

#### 9. View Logs

```bash
bit tail job-xxx --lines 10
```

Output:
```
Last 10 events
[2026-02-04T12:00:01Z] | job.started | plan_id=plan-xxx
[2026-02-04T12:00:02Z] | step.started | step=step_1_validate | worker=audio_validator
[2026-02-04T12:00:05Z] | step.completed | step=step_1_validate | worker=audio_validator
[2026-02-04T12:00:06Z] | step.started | step=step_2_normalize | worker=audio_normalizer
[2026-02-04T12:05:30Z] | step.completed | step=step_2_normalize | worker=audio_normalizer
[2026-02-04T12:05:31Z] | job.completed | run_id=run-xxx
```

#### 10. Check Artifacts

```bash
bit artifacts job-xxx
```

Output:
```
Artifacts for Job job-xxx
Name                Path                           Size      Modified
──────────────────────────────────────────────────────────────────
normalized_audio    /workspace/artifacts/...       5234567   2026-02-04T12:05:30Z
metadata.json       /workspace/artifacts/...       1234      2026-02-04T12:05:30Z
```

## CLI Reference

### Workspace Commands

| Command | Purpose |
|---------|---------|
| `bit init <path>` | Initialize new workspace |
| `bit ws open --path <path>` | Open/activate workspace |
| `bit ws validate --path <path>` | Verify workspace structure |
| `bit ws show` | Display active workspace info |

### Mode Commands

| Command | Purpose |
|---------|---------|
| `bit mode list` | List available modes |
| `bit mode set --name <mode>` | Set active mode |
| `bit mode show` | Display current mode |

### Intent Commands

| Command | Purpose |
|---------|---------|
| `bit intent synth --text <text>` | Create intent from text |
| `bit intent show --hash <hash>` | Display intent details |
| `bit intent list` | List all intents |
| `bit intent verify --hash <hash>` | Verify intent integrity |

### Job Commands

| Command | Purpose |
|---------|---------|
| `bit job from-intent --intent-id <id>` | Create job from intent |
| `bit job show --job-id <id>` | Display job details |
| `bit job list` | List all jobs |
| `bit job validate --job-id <id>` | Verify job integrity |

### Package Commands

| Command | Purpose |
|---------|---------|
| `bit package list [--category <cat>]` | List packages |
| `bit package show --package-id <id>` | Display package details |
| `bit package validate --package-id <id>` | Verify package validity |

### Plan Commands

| Command | Purpose |
|---------|---------|
| `bit plan generate --job-id <id>` | Generate execution plan |
| `bit plan show --job-id <id> --plan-id <id>` | Display plan details |
| `bit plan list --job-id <id>` | List all plans for job |

### Approval Commands

| Command | Purpose |
|---------|---------|
| `bit approve <job-id> [--note <note>]` | Approve plan for execution |
| `bit deny <job-id> [--reason <reason>]` | Reject plan (can retry) |

### Execution Commands

| Command | Purpose |
|---------|---------|
| `bit run <job-id> [--plan-id <id>]` | Execute approved job |
| `bit status <job-id>` | Show job status |
| `bit tail <job-id> [--lines <n>]` | Stream execution logs |
| `bit artifacts <job-id>` | List job artifacts |

## Advanced Usage

### Batch Operations

Process multiple jobs sequentially:

```bash
for intent in "normalize audio" "compress files" "validate data"; do
  bit intent synth --text "$intent"
  # Extract intent hash from output
  HASH=$(bit intent list | grep "$intent" | awk '{print $1}')
  bit job from-intent --intent-id $HASH
  # Extract job ID
  JOB_ID=$(bit job list | head -1 | awk '{print $1}')
  bit plan generate --job-id $JOB_ID
  bit approve $JOB_ID
  bit run $JOB_ID
done
```

### Custom Packages

Create reusable task packages:

```yaml
# packages/custom/my_processor/v1.0.0/package.yaml
package_id: custom.my_processor
version: 1.0.0
title: My Custom Processor
description: Custom task implementation
intent:
  category: custom
  verbs: [process, run]
  entities: [data]
  confidence_threshold: 0.6
input_contract:
  fields:
    - name: input_data
      type: file
      description: Input file
      required: true
output_contract:
  fields:
    - name: output_data
      type: file
      description: Output file
      required: true
pipeline:
  steps:
    - step_id: step_1
      worker:
        worker_id: custom_worker
        version: 1.0.0
      inputs: [input_data]
      outputs: [output_data]
      params: {}
approval:
  required: false
verification:
  required: false
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
  tags: [custom]
```

### Approval Denial and Retry

If plan is rejected, generate alternative and resubmit:

```bash
# Deny first plan
bit deny job-xxx --reason "Need to adjust loudness target"

# Job remains in PLANNED status
bit status job-xxx  # Status: planned

# Generate new plan with different parameters
bit plan generate --job-id job-xxx

# Approve new plan
bit approve job-xxx

# Execute
bit run job-xxx
```

## Troubleshooting

### Problem: Intent not matching any packages

**Cause**: Intent keywords don't match package verbs/entities

**Solution**:
```bash
# Check available packages
bit package list

# Review package details
bit package show --package-id audio.normalize

# Try more specific intent language
bit intent synth --text "Normalize audio loudness to -14 LUFS using standard algorithms"
```

### Problem: Job validation fails

**Cause**: Intent reference or hash mismatch

**Solution**:
```bash
# Verify intent exists
bit intent verify --hash <hash>

# Check job details
bit job show --job-id <job-id>

# Recreate job if needed
bit job from-intent --intent-id <intent-id>
```

### Problem: Execution fails with missing worker

**Cause**: Worker not registered in router

**Solution**:
```bash
# Check plan details
bit plan show --job-id <id> --plan-id <id>

# Verify package references valid workers
bit package validate --package-id <id>
```

### Problem: No artifacts found after execution

**Cause**: Job completed but workers didn't produce artifacts

**Solution**:
```bash
# Check execution logs
bit tail <job-id> --lines 20

# Review step outputs
bit tail <job-id> --lines 100 | grep "step.completed"

# Check artifacts directory
ls -la /workspace/artifacts/<job-id>/
```

## Best Practices

1. **Use descriptive intents**: Include expected outputs and constraints
2. **Review plans before approval**: Check package confidence and pipeline
3. **Monitor first run**: Watch logs closely for new package types
4. **Version control packages**: Use semantic versioning
5. **Document custom workers**: Include capabilities and requirements
6. **Archive old jobs**: Clean up workspace periodically
7. **Test with small datasets**: Validate with limited input first
8. **Track job history**: Use intent hashes for deduplication

## Additional Resources

- Architecture overview: See design documents in `docs/sources/`
- Package specifications: See `packages/` directory
- API reference: See inline code documentation
- Examples: See `tests/test_integration.py`
