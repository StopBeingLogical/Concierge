# Configuration Guide

Customize Concierge behavior for your specific environment and use cases.

## 📋 Configuration File

Configuration is stored in `concierge.json` in your workspace root.

```bash
cat ~/workspace/concierge.json
```

Default location after workspace creation:
```
~/workspace/
└── concierge.json
```

## 🔧 Main Settings

### Planner Configuration

Controls intent-to-package matching behavior.

```bash
bit config set planner confidence_threshold 0.75
bit config set planner max_candidates 5
bit config set planner enable_ambiguity_detection true
```

**Parameters**:

| Parameter | Default | Range | Effect |
|-----------|---------|-------|--------|
| `confidence_threshold` | 0.7 | 0.0-1.0 | Minimum match score for plan generation |
| `max_candidates` | 5 | 1-100 | Maximum packages to evaluate |
| `enable_ambiguity_detection` | true | true/false | Warn if multiple packages match equally |

**Examples**:

```bash
# Strict matching (high confidence required)
bit config set planner confidence_threshold 0.9

# Loose matching (accept marginal matches)
bit config set planner confidence_threshold 0.5

# Evaluate many packages
bit config set planner max_candidates 20

# Disable ambiguity warnings
bit config set planner enable_ambiguity_detection false
```

---

### Router Configuration

Controls pipeline execution behavior.

```bash
bit config set router max_parallel_steps 1
bit config set router enable_event_logging true
bit config set router event_log_format jsonl
```

**Parameters**:

| Parameter | Default | Effect |
|-----------|---------|--------|
| `max_parallel_steps` | 1 | Maximum concurrent pipeline steps |
| `enable_event_logging` | true | Record execution events |
| `event_log_format` | jsonl | Event output format (jsonl only currently) |

**Examples**:

```bash
# Sequential execution only (default, stable)
bit config set router max_parallel_steps 1

# Enable parallelization (experimental)
bit config set router max_parallel_steps 4

# Disable event logging (not recommended)
bit config set router enable_event_logging false
```

---

### Approval Configuration

Controls approval gate behavior.

```bash
bit config set approval require_approval_by_default false
bit config set approval auto_approve_threshold 0.95
bit config set approval approval_timeout_hours 24
```

**Parameters**:

| Parameter | Default | Effect |
|-----------|---------|--------|
| `require_approval_by_default` | false | Require approval for all jobs |
| `auto_approve_threshold` | 0.95 | Auto-approve if confidence > threshold |
| `approval_timeout_hours` | 24 | How long approval request remains valid |

**Examples**:

```bash
# Require approval for everything (safe for production)
bit config set approval require_approval_by_default true

# Auto-approve high-confidence matches
bit config set approval auto_approve_threshold 0.85

# Shorter approval timeout (6 hours)
bit config set approval approval_timeout_hours 6
```

---

### Caching Configuration

Controls output caching behavior.

```bash
bit config set cache enable_caching true
bit config set cache cache_ttl_seconds 3600
bit config set cache max_cache_size_mb 1000
```

**Parameters**:

| Parameter | Default | Effect |
|-----------|---------|--------|
| `enable_caching` | true | Cache task outputs |
| `cache_ttl_seconds` | 3600 | Cache validity duration (1 hour) |
| `max_cache_size_mb` | 1000 | Maximum cache size before cleanup |

**Examples**:

```bash
# Disable caching (slower, but always fresh)
bit config set cache enable_caching false

# Longer cache lifetime (6 hours)
bit config set cache cache_ttl_seconds 21600

# Larger cache allowance
bit config set cache max_cache_size_mb 5000
```

---

## 👷 Worker Configuration

Configure individual workers for specific environments.

### Enable/Disable Workers

```bash
# Disable a worker
bit config worker disable audio_normalizer

# Re-enable a worker
bit config worker enable audio_normalizer

# Check status
bit config get
```

### Customize Worker Settings

```bash
# Set worker timeout (seconds)
bit config set worker audio_normalizer timeout_seconds 600

# Set retry attempts
bit config set worker audio_normalizer retry_count 3

# Set resource limits
bit config set worker gpu_worker resource_limits '{"memory_mb": 4096, "gpu_memory_mb": 8192}'
```

**Worker Parameters**:

| Parameter | Type | Default | Effect |
|-----------|------|---------|--------|
| `enabled` | bool | true | Whether worker is available |
| `timeout_seconds` | int | 300 | Maximum execution time |
| `retry_count` | int | 3 | Retries on failure |
| `resource_limits` | dict | {} | Memory, GPU, etc. constraints |

**Examples**:

```bash
# Fast timeout for quick operations
bit config set worker echo_worker timeout_seconds 30

# Long timeout for heavy processing
bit config set worker video_transcoder timeout_seconds 3600

# No retries for deterministic operations
bit config set worker file_copier retry_count 0

# Multiple retries for flaky network operations
bit config set worker s3_uploader retry_count 5
```

---

## 📊 Configuration Profiles

### Development Profile

Loose validation, fast feedback:

```bash
bit config set planner confidence_threshold 0.5
bit config set planner enable_ambiguity_detection false
bit config set approval require_approval_by_default false
bit config set router enable_event_logging true
```

### Testing Profile

Moderate settings:

```bash
bit config set planner confidence_threshold 0.7
bit config set planner max_candidates 10
bit config set approval require_approval_by_default false
```

### Production Profile

Strict validation, safety-first:

```bash
bit config set planner confidence_threshold 0.85
bit config set approval require_approval_by_default true
bit config set approval auto_approve_threshold 0.98
bit config set cache enable_caching true
```

### High-Throughput Profile

For batch processing:

```bash
bit config set router max_parallel_steps 4
bit config set planner max_candidates 3
bit config set cache enable_caching true
bit config set cache cache_ttl_seconds 7200
```

---

## 📝 Manual Configuration

Edit `concierge.json` directly for complex configurations:

```bash
vim ~/workspace/concierge.json
```

**JSON Structure**:

```json
{
  "version": "1.0.0",
  "workspace_path": "/home/user/workspace",
  "planner": {
    "confidence_threshold": 0.7,
    "max_candidates": 5,
    "enable_ambiguity_detection": true
  },
  "router": {
    "max_parallel_steps": 1,
    "enable_event_logging": true,
    "event_log_format": "jsonl"
  },
  "approval": {
    "require_approval_by_default": false,
    "auto_approve_threshold": 0.95,
    "approval_timeout_hours": 24
  },
  "cache": {
    "enable_caching": true,
    "cache_ttl_seconds": 3600,
    "max_cache_size_mb": 1000
  },
  "workers": {
    "audio_normalizer": {
      "worker_id": "audio_normalizer",
      "enabled": true,
      "timeout_seconds": 600,
      "retry_count": 3,
      "resource_limits": {}
    },
    "video_transcoder": {
      "worker_id": "video_transcoder",
      "enabled": true,
      "timeout_seconds": 3600,
      "retry_count": 2,
      "resource_limits": {
        "gpu_memory_mb": 4096
      }
    }
  }
}
```

---

## 🎯 Use Cases

### Case 1: CI/CD Integration

Strict, no human approval:

```bash
bit config set approval require_approval_by_default false
bit config set approval auto_approve_threshold 0.99
bit config set planner confidence_threshold 0.85
```

### Case 2: Interactive Exploration

Loose, fast feedback:

```bash
bit config set planner confidence_threshold 0.5
bit config set approval require_approval_by_default false
```

### Case 3: Production Automation

Safety-critical:

```bash
bit config set approval require_approval_by_default true
bit config set planner confidence_threshold 0.9
bit config set router enable_event_logging true
```

### Case 4: Batch Processing

High throughput:

```bash
bit config set router max_parallel_steps 8
bit config set cache enable_caching true
bit config set cache cache_ttl_seconds 14400
bit config set planner max_candidates 3
```

### Case 5: GPU-Heavy Processing

GPU optimization:

```bash
# Disable parallel steps to avoid GPU contention
bit config set router max_parallel_steps 1

# Increase timeouts for long GPU jobs
bit config set worker video_transcoder timeout_seconds 7200
bit config set worker ml_inferencer timeout_seconds 3600

# Set GPU resource limits
bit config set worker gpu_worker \
  resource_limits '{"gpu_memory_mb": 8192}'
```

---

## 🔍 Viewing Configuration

### View full configuration

```bash
bit config get
```

Output:
```json
{
  "workspace_path": "/home/user/workspace",
  "planner_threshold": 0.7,
  "router_max_parallel": 1,
  "approval_required_by_default": false,
  "caching_enabled": true,
  "enabled_workers": 3,
  "total_workers_configured": 5
}
```

### View specific component

```bash
bit config get --component planner
bit config get --component router
bit config get --component approval
bit config get --component cache
```

### View raw JSON

```bash
cat ~/workspace/concierge.json | jq .
```

---

## ⚙️ Reset to Defaults

Remove config file to reset:

```bash
rm ~/workspace/concierge.json
bit ws open --path ~/workspace  # Reloads with defaults
```

---

## 🚀 Performance Tuning

### For Speed

```bash
# Faster matching
bit config set planner confidence_threshold 0.5
bit config set planner max_candidates 3

# Enable caching
bit config set cache enable_caching true
bit config set cache cache_ttl_seconds 7200

# Parallel execution
bit config set router max_parallel_steps 4
```

### For Accuracy

```bash
# Stricter matching
bit config set planner confidence_threshold 0.85
bit config set planner max_candidates 20

# Require approval
bit config set approval require_approval_by_default true
```

### For Reliability

```bash
# Longer timeouts
bit config set worker audio_normalizer timeout_seconds 1200
bit config set worker video_transcoder timeout_seconds 7200

# More retries
bit config set worker api_caller retry_count 5

# Event logging
bit config set router enable_event_logging true
```

---

## 📊 Configuration Examples by Domain

### Audio Processing

```json
{
  "planner": {"confidence_threshold": 0.8},
  "workers": {
    "audio_normalizer": {"timeout_seconds": 1200},
    "audio_validator": {"timeout_seconds": 300}
  }
}
```

### Video Processing

```json
{
  "router": {"max_parallel_steps": 1},
  "workers": {
    "video_transcoder": {
      "timeout_seconds": 7200,
      "resource_limits": {"gpu_memory_mb": 8192}
    }
  }
}
```

### Database Operations

```json
{
  "approval": {"require_approval_by_default": true},
  "workers": {
    "db_backup": {"timeout_seconds": 3600},
    "db_restore": {"timeout_seconds": 7200}
  }
}
```

### ML/AI Workloads

```json
{
  "router": {"max_parallel_steps": 2},
  "workers": {
    "ml_inferencer": {
      "timeout_seconds": 1800,
      "retry_count": 1,
      "resource_limits": {"gpu_memory_mb": 4096}
    }
  }
}
```

---

## ✅ Validation

After configuration changes:

```bash
# Verify workspace still valid
bit ws validate

# Test with sample job
bit intent synth --text "test"
bit job from-intent --intent-id <hash>
bit plan generate --job-id <job_id>
bit job show --job-id <job_id>
```
