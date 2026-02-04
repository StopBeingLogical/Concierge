# Workflow Example: Audio Normalization

Complete example of normalizing podcast audio using Concierge.

## Scenario

You have a podcast episode with inconsistent volume levels and want to normalize it to standard loudness (-14 LUFS) before publishing.

## Step-by-Step Walkthrough

### 1. Initialize Workspace

```bash
bit init ~/podcast_project
bit ws open --path ~/podcast_project
bit mode set --name code
```

**What happens:**
- Creates workspace directories: `intents/`, `jobs/`, `artifacts/`
- Initializes `concierge.json` with default settings
- Sets active mode to "code" (appropriate for technical audio operations)

### 2. Synthesize Intent

```bash
bit intent synth --text "Normalize the audio volume in episode_123.wav to standard loudness levels. \
  Must preserve audio quality and not introduce artifacts. \
  Cannot exceed -10 LUFS or go below -16 LUFS."
```

**Output:**
```
Intent synthesized: 7a2f3e5c... (hash)
Distilled: Normalize audio volume in episode_123.wav
Success Criteria: Normalize to standard loudness levels
Constraints: Must preserve audio quality, Cannot introduce artifacts, Keep loudness between -10 and -16 LUFS
```

### 3. Create Job from Intent

```bash
bit job from-intent --intent-id 7a2f3e5c
```

**Output:**
```
Job created: j_podcast_ep123_xyz (DRAFT status)
Intent reference: 7a2f3e5c...
Ready for planning
```

### 4. Generate Execution Plan

```bash
bit plan generate --job-id j_podcast_ep123_xyz
```

**Output:**
```
Matched package: audio.normalize v1.0.0 (0.92 confidence)
  Reason: Strong verb match "normalize" + audio context entities

Pipeline (2 steps):
  1. validate - Verify audio format and duration
  2. normalize - Apply loudness normalization

Resources Required:
  CPU: 2 cores
  Memory: 1 GB
  Disk: 5 GB

Approval: Required (audio processing operation)
```

### 5. Show Plan Details

```bash
bit plan show --job-id j_podcast_ep123_xyz --plan-id <plan-id>
```

**Output:**
```yaml
package_id: audio.normalize
version: 1.0.0
matched_confidence: 0.92

resolved_inputs:
  - audio_file: episode_123.wav
  - target_loudness: -14 LUFS  # From constraints

pipeline:
  - step_id: step_1_validate
    worker: audio_validator
    inputs: [audio_file]
    outputs: [validation_result]

  - step_id: step_2_normalize
    worker: audio_normalizer
    inputs: [audio_file, target_loudness, validation_result]
    outputs: [normalized_audio, metadata]
```

### 6. Approve Plan

```bash
bit approve --job-id j_podcast_ep123_xyz \
  --note "Looks good. Constraints are reasonable for our workflow."
```

**Output:**
```
Job approved
Status: PLANNED → APPROVED
Approval recorded at 2026-02-04T14:32:15Z
```

### 7. Execute Job

```bash
bit run --job-id j_podcast_ep123_xyz
```

**Output:**
```
Running job j_podcast_ep123_xyz
  Step 1/2: validate ... ✓ PASS
    Audio format: WAV, 48kHz, 2-channel
    Duration: 45 minutes 23 seconds

  Step 2/2: normalize ... ✓ PASS
    Applied loudness normalization to -14.0 LUFS
    Peak normalized: -3.1 dB

Job completed successfully
Final status: COMPLETED
```

### 8. Monitor Execution

While job is running:

```bash
bit status --job-id j_podcast_ep123_xyz
```

**Output:**
```
Job: j_podcast_ep123_xyz
Status: RUNNING
Current Step: step_2_normalize
Elapsed: 2m 34s
Latest Events:
  14:32:45 - step_1_validate: COMPLETED
  14:33:00 - step_2_normalize: STARTED
```

Stream logs in real-time:

```bash
bit tail --job-id j_podcast_ep123_xyz --lines 5
```

**Output:**
```
2026-02-04T14:33:15Z [job.step_2_normalize] Starting audio normalization...
2026-02-04T14:33:45Z [worker.audio_normalizer] Processing audio...
2026-02-04T14:34:30Z [worker.audio_normalizer] Normalization complete: -14.0 LUFS
2026-02-04T14:34:35Z [job.step_2_normalize] Step completed in 95 seconds
2026-02-04T14:34:35Z [job.completed] Job completed successfully
```

### 9. View Artifacts

```bash
bit artifacts --job-id j_podcast_ep123_xyz
```

**Output:**
```
Job artifacts:
  • episode_123_normalized.wav          145 MB    2026-02-04 14:34:35Z
  • normalization_metadata.json         2.3 KB    2026-02-04 14:34:35Z
```

### 10. Download and Use

```bash
# Artifacts are available in the jobs directory
cp jobs/j_podcast_ep123_xyz/artifacts/episode_123_normalized.wav ~/downloads/
```

## Key Learning Points

1. **Intent Synthesis** extracts the actual requirement from natural language
2. **Package Matching** automatically finds the best task for your intent
3. **Plan Review** lets you see what will happen before approval
4. **Approval Gates** ensure important operations are reviewed
5. **Execution Tracking** shows real-time progress with event logs
6. **Artifact Management** keeps outputs organized per job

## Variation: Denial and Retry

If you wanted to reject the plan and adjust parameters:

```bash
# Deny the initial plan
bit deny --job-id j_podcast_ep123_xyz \
  --reason "Need to adjust to -16 LUFS instead of -14"

# Job returns to PLANNED status - can generate new plan with updated constraints
bit intent synth --text "Normalize episode_123.wav to -16 LUFS target loudness"
bit job from-intent --intent-id <new-hash>
bit plan generate --job-id j_podcast_ep123_new
bit approve --job-id j_podcast_ep123_new
bit run --job-id j_podcast_ep123_new
```

## Actual Commands for Copy-Paste

```bash
# Quick copy-paste version of full workflow
bit init ~/podcast_project
bit ws open --path ~/podcast_project
bit mode set --name code

bit intent synth --text "Normalize the audio volume in episode_123.wav to standard loudness levels. Must preserve audio quality and not introduce artifacts. Cannot exceed -10 LUFS or go below -16 LUFS."

# Get intent hash from output, e.g., 7a2f3e5c...
INTENT_HASH="7a2f3e5c"  # Replace with actual hash

bit job from-intent --intent-id $INTENT_HASH
# Get job ID from output, e.g., j_podcast_ep123_xyz
JOB_ID="j_podcast_ep123_xyz"  # Replace with actual ID

bit plan generate --job-id $JOB_ID
bit approve --job-id $JOB_ID --note "Ready to go"
bit run --job-id $JOB_ID
bit status --job-id $JOB_ID
bit artifacts --job-id $JOB_ID
```
