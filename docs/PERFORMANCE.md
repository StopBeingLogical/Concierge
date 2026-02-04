# Performance Tuning Guide

Optimize Concierge for your specific use cases and hardware.

## 🎯 Quick Wins

### 1. Enable Caching
```bash
bit config set cache enable_caching true
bit config set cache cache_ttl_seconds 7200  # 2 hours
```

**Impact**: Skip redundant operations, 10-50% speedup for repeated workflows

---

### 2. Increase Confidence Threshold
```bash
bit config set planner confidence_threshold 0.85
```

**Impact**: Faster plan generation, fewer false matches
**Trade-off**: May miss marginal matches (usually good)

---

### 3. Reduce Max Candidates
```bash
bit config set planner max_candidates 3
```

**Impact**: Faster package evaluation
**When**: 100+ packages in registry

---

### 4. Parallel Execution (Careful)
```bash
bit config set router max_parallel_steps 2
```

**Impact**: Faster pipeline for independent steps
**Warning**: Only works if steps don't depend on each other

---

## 📊 Profiling Your Workflows

### Measure Execution Time
```bash
#!/bin/bash
JOB_ID=$1
START=$(jq -r 'select(.type == "job.started") | .timestamp' \
  ~/workspace/jobs/$JOB_ID/logs/*.jsonl | head -1)
END=$(jq -r 'select(.type == "job.completed") | .timestamp' \
  ~/workspace/jobs/$JOB_ID/logs/*.jsonl | tail -1)

echo "Start: $START"
echo "End: $END"
```

### Find Slow Steps
```bash
JOB_ID=$1
echo "Step durations:"
jq -r 'select(.type == "step.completed") |
  "\(.payload.step_id): \(.payload.duration)s"' \
  ~/workspace/jobs/$JOB_ID/logs/*.jsonl | sort -t: -k2 -rn
```

### Monitor Resource Usage
```bash
# During job execution
watch -n 1 'ps aux | grep bit | head -5'
```

---

## 🔧 Configuration Profiles

### Profile: Development (Speed)
```bash
bit config set planner confidence_threshold 0.5
bit config set planner max_candidates 3
bit config set approval require_approval_by_default false
bit config set cache enable_caching true
bit config set cache cache_ttl_seconds 3600
```

**For**: Quick iterations, testing
**Trade-off**: Less validation

---

### Profile: Production (Safety)
```bash
bit config set planner confidence_threshold 0.9
bit config set approval require_approval_by_default true
bit config set cache enable_caching true
bit config set cache cache_ttl_seconds 7200
bit config set router enable_event_logging true
```

**For**: Critical operations
**Trade-off**: Slower (safer)

---

### Profile: Batch (Throughput)
```bash
bit config set planner max_candidates 3
bit config set cache enable_caching true
bit config set cache cache_ttl_seconds 14400  # 4 hours
bit config set router max_parallel_steps 4
bit config set approval require_approval_by_default false
```

**For**: Processing many files
**Trade-off**: Less safety

---

### Profile: GPU-Heavy (Resource Aware)
```bash
bit config set router max_parallel_steps 1  # Prevent GPU contention
bit config set worker video_transcoder timeout_seconds 7200
bit config set worker ml_inferencer timeout_seconds 3600
```

**For**: GPU operations (video, ML)
**Trade-off**: Sequential only

---

## 💾 Memory Optimization

### Monitor Memory Usage
```bash
# Before large batch
free -h

# During execution
watch -n 1 free -h
```

### Reduce Memory Footprint
```bash
# Disable event logging (if not needed)
bit config set router enable_event_logging false

# Shorter cache lifetime
bit config set cache cache_ttl_seconds 1800  # 30 min

# Limit cache size
bit config set cache max_cache_size_mb 500
```

---

## ⚡ I/O Optimization

### Disk Performance
```bash
# Check disk usage
df -h ~/workspace

# Find large artifacts
du -sh ~/workspace/jobs/*/artifacts/*

# Archive old jobs (free space)
tar -czf archive_$(date +%Y%m%d).tar.gz ~/workspace/jobs/j_*_old/
rm -rf ~/workspace/jobs/j_*_old/
```

### Batch Operations
```bash
# Process many files efficiently
scripts/batch_process.sh ~/workspace \
  'Your intent {file}' \
  '*.input' \
  4  # Parallel limit
```

---

## 🎯 Benchmarking

### Simple Benchmark Script
```bash
#!/bin/bash
INTENT="Normalize audio file test.wav"

echo "Benchmarking: $INTENT"
START=$(date +%s%N)

bit intent synth --text "$INTENT"
HASH=$(bit intent list | tail -1 | awk '{print $1}')
bit job from-intent --intent-id $HASH
JOB_ID=$(bit job list | tail -1 | awk '{print $1}')
bit plan generate --job-id $JOB_ID
bit approve --job-id $JOB_ID
bit run --job-id $JOB_ID

END=$(date +%s%N)
DURATION=$((($END - $START) / 1000000))

echo "Total time: ${DURATION}ms"
```

---

## 📈 Scaling Considerations

### <100 Jobs
- Default configuration works fine
- Focus on workflow optimization
- No special tuning needed

### 100-1000 Jobs
- Enable caching
- Reduce max_candidates
- Monitor disk space
- Archive old jobs periodically

### 1000+ Jobs
- Consider database backend (Phase 2)
- Implement job archival
- Monitor memory usage carefully
- Use batch_process.sh for large operations

---

## 🔍 Debugging Performance Issues

### Slow Plan Generation
```bash
# Check planner settings
bit config get --component planner

# Reduce candidates
bit config set planner max_candidates 3

# Increase threshold
bit config set planner confidence_threshold 0.8
```

### Slow Execution
```bash
# Check step durations
jq -r 'select(.type == "step.completed") |
  "\(.payload.step_id): \(.payload.duration)s"' \
  logs/*.jsonl

# Identify bottleneck step
# Profile that specific worker
```

### High Memory Usage
```bash
# Check what's using memory
ps aux | grep bit | sort -k6 -rn

# Check cache size
du -sh ~/workspace/cache/

# Reduce cache
bit config set cache max_cache_size_mb 250
```

### Slow I/O
```bash
# Check disk performance
iostat -x 1 5

# Check disk space
df -h ~/workspace

# Move to faster disk if possible
```

---

## 📋 Performance Checklist

Before large batch operations:

- [ ] Check available disk space: `df -h ~/workspace`
- [ ] Check available memory: `free -h`
- [ ] Check GPU if needed: `nvidia-smi`
- [ ] Enable caching: `bit config set cache enable_caching true`
- [ ] Set appropriate parallelism: `bit config set router max_parallel_steps N`
- [ ] Review log retention: Clean old logs if needed
- [ ] Test with small sample first
- [ ] Monitor during execution: `scripts/monitor_jobs.sh`

---

## 🚀 Advanced Optimization

### Custom Worker Optimization
```python
class OptimizedWorker(WorkerStub):
    def __init__(self):
        self.cache = {}  # In-memory cache

    def execute(self, inputs, params):
        # Check cache first
        cache_key = str(inputs)
        if cache_key in self.cache:
            return self.cache[cache_key]

        # Expensive operation
        result = self.process(inputs)

        # Cache result
        self.cache[cache_key] = result
        return result
```

### Batch Processing Optimization
```bash
# Process in parallel with resource limits
parallel --jobs 4 --load 80% \
  'bit run --job-id {}' \
  :::: job_ids.txt
```

---

## 📊 Performance Metrics to Track

| Metric | Good | Fair | Poor |
|--------|------|------|------|
| Intent Synthesis | <100ms | 100-500ms | >500ms |
| Plan Generation | <500ms | 500-2000ms | >2000ms |
| Job Execution | Depends | - | Timeouts |
| Memory Usage | <1GB | 1-4GB | >4GB |
| Disk Space | 10% used | 50% used | 90% used |

---

## 🎯 Optimization Strategy

1. **Measure** - Profile your actual workflows
2. **Identify** - Find bottlenecks (plan? execution? I/O?)
3. **Optimize** - Apply targeted improvements
4. **Verify** - Measure again to confirm
5. **Iterate** - Repeat for each bottleneck

---

## 📞 Getting More Help

- Check logs: `~/workspace/jobs/<job_id>/logs/*.jsonl`
- Monitor in real-time: `scripts/monitor_jobs.sh`
- Generate report: `scripts/generate_report.sh`
- See TROUBLESHOOTING.md for common issues
