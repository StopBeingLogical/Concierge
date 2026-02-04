# Troubleshooting Guide

Common issues and solutions for Concierge workflows.

## 🔴 Critical Errors

### "Read-only file system"
**Error**: `[Errno 30] Read-only file system: '/workspace'`

**Cause**: Workspace directory is on read-only filesystem or lacks permissions

**Solution**:
1. Check filesystem: `mount | grep workspace`
2. Verify permissions: `ls -ld /workspace`
3. Use writable path: `bit init ~/workspace` instead of `/workspace`
4. Check disk space: `df -h /workspace`

---

### "Connection refused" / "Network unreachable"
**Error**: When accessing packages or jobs directory

**Cause**: Path not accessible, permissions denied, or network issue

**Solution**:
```bash
# Verify path exists
ls -la ~/workspace/

# Check permissions
chmod 755 ~/workspace
chmod -R 755 ~/workspace/jobs

# Test accessibility
cd ~/workspace && pwd
```

---

### Job disappears after creation
**Error**: Job created but cannot be found

**Cause**: Job saved to wrong workspace or incorrect ID

**Solution**:
```bash
# Check active workspace
bit ws show

# List all jobs
bit job list

# Verify workspace has jobs directory
ls -la ~/workspace/jobs/
```

---

## ⚠️ Common Issues

### Intent synthesis produces unexpected results
**Issue**: Extracted intent doesn't match your description

**Cause**: Text lacks keywords or has ambiguous phrasing

**Solution**:
```bash
# Try explicit phrasing
# ❌ Bad: "Do the thing with the file"
# ✅ Good: "Normalize audio volume in podcast_episode.wav"

# Check extracted intent
bit intent show --hash <hash>

# If unsatisfactory, create new intent with clearer language
bit intent synth --text "Normalize the audio file episode.wav to -14 LUFS loudness"
```

---

### Package matching has low confidence
**Issue**: Plan shows `matched_confidence: 0.45` (below threshold)

**Cause**: Intent keywords don't match package verbs/entities

**Solution**:
```bash
# Check available packages
bit package list

# View package verbs
bit package show --package-id audio.normalize

# Rephrase intent with package verbs
# Before: "make the audio louder"
# After: "normalize audio volume"

# Or adjust threshold
bit config set planner confidence_threshold 0.6

# Regenerate plan
bit plan generate --job-id <job_id>
```

---

### Job approval fails
**Error**: "Cannot approve job in DRAFT status"

**Cause**: Job must be PLANNED before approval

**Solution**:
```bash
# Check job status
bit job show --job-id <job_id>

# If DRAFT, generate plan first
bit plan generate --job-id <job_id>

# Now approve
bit approve --job-id <job_id>
```

---

### Execution fails immediately
**Error**: Step fails with "Missing input" or "Worker not found"

**Cause**: Pipeline inputs not available or worker not configured

**Solution**:
```bash
# Check plan details
bit plan show --job-id <job_id> --plan-id <plan_id>

# Verify resolved inputs match actual files
ls -la <input_file>

# Check worker configuration
bit config worker enable <worker_id>

# Review job spec for input values
bit job show --job-id <job_id>

# Retry
bit run --job-id <job_id>
```

---

### Job runs but produces no artifacts
**Error**: Job shows COMPLETED but `bit artifacts` is empty

**Cause**: Worker didn't generate output files or path wrong

**Solution**:
```bash
# Check logs for errors
bit tail --job-id <job_id> --lines 50

# Verify output directory
ls -la ~/workspace/jobs/<job_id>/artifacts/

# Check final step in pipeline
bit plan show --job-id <job_id> --plan-id <plan_id>

# Look for stderr in logs
grep -i "error" ~/workspace/jobs/<job_id>/logs/*.jsonl
```

---

### Workspace won't initialize
**Error**: `FileExistsError: Workspace already exists at /path`

**Cause**: Workspace already initialized at that path

**Solution**:
```bash
# Check for workspace.json
ls -la ~/workspace/workspace.json

# Use different path
bit init ~/workspace_v2

# Or remove and reinitialize
rm ~/workspace/workspace.json
bit init ~/workspace
```

---

### Configuration changes not taking effect
**Error**: Changed setting but behavior unchanged

**Cause**: Cached config or stale session

**Solution**:
```bash
# Verify config was saved
cat ~/workspace/concierge.json | grep confidence

# Reload config
bit ws open --path ~/workspace  # Forces session reload

# Or directly edit JSON
vim ~/workspace/concierge.json

# Verify change
bit config get --component planner
```

---

## 🔧 Debugging Workflows

### Enable verbose logging
```bash
# Show all events, including debug messages
bit tail --job-id <job_id> --lines 100

# Or check raw log file
cat ~/workspace/jobs/<job_id>/logs/*.jsonl | jq .
```

### Examine job state
```bash
# Full job specification
cat ~/workspace/jobs/<job_id>/job.yaml

# Check approval log
grep -A5 "approval" ~/workspace/jobs/<job_id>/job.yaml

# View plan details
cat ~/workspace/jobs/<job_id>/plans/*.yaml
```

### Trace execution step-by-step
```bash
# Get step IDs
bit plan show --job-id <job_id> --plan-id <plan_id>

# Filter logs for specific step
grep "step_2_normalize" ~/workspace/jobs/<job_id>/logs/*.jsonl

# Or search for errors
grep -i "error\|fail\|exception" ~/workspace/jobs/<job_id>/logs/*.jsonl
```

---

## 🚀 Performance Issues

### Job execution is very slow
**Cause**: Single-threaded execution, I/O bottleneck, or inadequate resources

**Solution**:
```bash
# Check resource utilization
top -p $(pgrep -f concierge)

# Review resource requirements
bit package show --package-id <pkg_id>

# For parallel processing:
# Run multiple independent jobs
bit run --job-id j_task1 &
bit run --job-id j_task2 &
wait

# Monitor resource usage
watch -n 1 'top -bn1 | head -20'
```

### High memory usage
**Cause**: Large input files, buffering in workers

**Solution**:
```bash
# Check available memory
free -h

# Check job resource limits
bit package show --package-id <pkg_id> | grep memory

# Reduce batch size (if applicable)
bit config set router max_parallel_steps 1

# Monitor during execution
watch -n 1 'ps aux | grep concierge'
```

### Disk space running out
**Error**: `OSError: [Errno 28] No space left on device`

**Solution**:
```bash
# Check disk usage
df -h ~/workspace

# Find large files
du -sh ~/workspace/jobs/*/artifacts/*

# Clean old artifacts
find ~/workspace/jobs -name "*.log" -mtime +7 -delete

# Archive old jobs
tar -czf ~/archive/jobs_2026_01.tar.gz ~/workspace/jobs/j_*_2026_01_*

# Remove archive source
rm -rf ~/workspace/jobs/j_*_2026_01_*
```

---

## 📊 Monitoring & Analysis

### View execution statistics
```bash
# Count completed jobs
ls ~/workspace/jobs/ | wc -l

# Find failed jobs
grep "FAILED\|ERROR" ~/workspace/jobs/*/job.yaml

# Get average execution time
for f in ~/workspace/jobs/*/logs/*.jsonl; do
  echo "$f:"
  grep "job.completed\|job.started" "$f" | head -2
done
```

### Export logs for analysis
```bash
# Export all events as JSON
cat ~/workspace/jobs/<job_id>/logs/*.jsonl | jq -s '.' > job_events.json

# Filter by event type
grep '"type":"job.completed"' ~/workspace/jobs/*/logs/*.jsonl

# Create summary
grep '"type":"step' ~/workspace/jobs/<job_id>/logs/*.jsonl | jq -r '.payload.step_id, .payload.duration'
```

---

## 🆘 Getting Help

### Collect debug information
```bash
#!/bin/bash
JOB_ID=$1
echo "=== Workspace Info ==="
bit ws show
echo "=== Job Status ==="
bit job show --job-id $JOB_ID
echo "=== Plan Details ==="
bit plan show --job-id $JOB_ID --plan-id $(ls ~/workspace/jobs/$JOB_ID/plans/ | head -1)
echo "=== Execution Logs ==="
tail -50 ~/workspace/jobs/$JOB_ID/logs/*.jsonl
echo "=== Configuration ==="
cat ~/workspace/concierge.json | jq .
```

### Report issues with
```bash
# Collect system info
uname -a
python3 --version
bit --version  # If available

# Relevant logs
cat ~/workspace/jobs/<job_id>/logs/*.jsonl

# Job specification
cat ~/workspace/jobs/<job_id>/job.yaml

# Configuration
cat ~/workspace/concierge.json
```

---

## ✅ Validation Checklist

Before running jobs:

```bash
# 1. Workspace valid
bit ws validate

# 2. Job spec valid
bit job validate --job-id <job_id>

# 3. Plan valid
bit plan show --job-id <job_id> --plan-id <plan_id>

# 4. Inputs available
ls -la <input_file>

# 5. Output directory exists
ls -la ~/workspace/jobs/<job_id>/artifacts/

# 6. Package available
bit package validate --package-id <pkg_id>

# 7. Resources available
df -h ~/workspace

# 8. Config reasonable
bit config get
```

---

## 🎯 Quick Fixes

| Problem | Quick Fix |
|---------|-----------|
| Job stuck | `bit deny --job-id <id>` → modify → regenerate plan |
| Low confidence match | `bit config set planner confidence_threshold 0.6` |
| Missing input | `ls -la <file>` → fix path → regenerate plan |
| No artifacts | `bit tail --job-id <id>` → check for errors |
| Slow execution | Run parallel jobs with `&` |
| Config not working | `bit ws open --path ~/workspace` → reload |
| Disk full | Clean old artifacts: `rm -rf ~/workspace/jobs/j_*_old/` |

---

## 📞 Further Help

- **MANUAL.md** - Command syntax and options
- **ARCHITECTURE.md** - System design and concepts
- **docs/examples/README.md** - Workflow patterns
- Log files: `~/workspace/jobs/<job_id>/logs/*.jsonl`
- Config file: `~/workspace/concierge.json`
