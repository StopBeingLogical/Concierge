# Advanced Features Guide

Sophisticated usage patterns and integration techniques for power users.

## 🔄 Advanced Workflows

### Pattern 1: Conditional Workflows

Implement decision logic based on job results:

```bash
#!/bin/bash
# Audio normalization with conditional archival

bit intent synth --text "Normalize podcast episode.wav"
HASH=$(bit intent list | tail -1 | awk '{print $1}')

bit job from-intent --intent-id $HASH
JOB_ID=$(bit job list | tail -1 | awk '{print $1}')

bit plan generate --job-id $JOB_ID
bit approve --job-id $JOB_ID
bit run --job-id $JOB_ID

# Check result
STATUS=$(bit job show --job-id $JOB_ID | grep status)

if [[ $STATUS == *"COMPLETED"* ]]; then
    echo "✓ Job completed - archiving artifacts"
    cp ~/workspace/jobs/$JOB_ID/artifacts/* ~/archive/
else
    echo "✗ Job failed - investigating"
    bit tail --job-id $JOB_ID --lines 50
fi
```

---

### Pattern 2: Pipeline Chaining

Use output from one job as input to next:

```bash
#!/bin/bash
# Chain: Normalize Audio → Compress → Archive to S3

# Step 1: Normalize
bit intent synth --text "Normalize podcast audio"
NORMALIZE_HASH=$(bit intent list | tail -1 | awk '{print $1}')
bit job from-intent --intent-id $NORMALIZE_HASH
NORMALIZE_JOB=$(bit job list | tail -1 | awk '{print $1}')
bit plan generate --job-id $NORMALIZE_JOB
bit approve --job-id $NORMALIZE_JOB
bit run --job-id $NORMALIZE_JOB

# Wait for completion
while [[ $(bit status --job-id $NORMALIZE_JOB | grep status) == *"RUNNING"* ]]; do
    sleep 5
done

# Get output
NORMALIZED_FILE=$(ls ~/workspace/jobs/$NORMALIZE_JOB/artifacts/*.wav)

# Step 2: Compress output
bit intent synth --text "Compress normalized audio to MP3 format"
COMPRESS_HASH=$(bit intent list | tail -1 | awk '{print $1}')
bit job from-intent --intent-id $COMPRESS_HASH
COMPRESS_JOB=$(bit job list | tail -1 | awk '{print $1}')

# Inject previous output as input
sed -i "s|audio_file: .*|audio_file: $NORMALIZED_FILE|" \
    ~/workspace/jobs/$COMPRESS_JOB/job.yaml

bit plan generate --job-id $COMPRESS_JOB
bit approve --job-id $COMPRESS_JOB
bit run --job-id $COMPRESS_JOB

# Step 3: Archive to S3
COMPRESSED_FILE=$(ls ~/workspace/jobs/$COMPRESS_JOB/artifacts/*.mp3)
aws s3 cp $COMPRESSED_FILE s3://podcast-archive/$(date +%Y%m%d)_episode.mp3

echo "✓ Pipeline complete: Normalize → Compress → Archive"
```

---

### Pattern 3: Parallel Fan-Out

Run same operation on multiple inputs:

```bash
#!/bin/bash
# Normalize multiple podcast episodes in parallel

EPISODES=("ep001.wav" "ep002.wav" "ep003.wav" "ep004.wav" "ep005.wav")

declare -a JOB_IDS

# Create jobs for all episodes
for episode in "${EPISODES[@]}"; do
    bit intent synth --text "Normalize audio file $episode to -14 LUFS"
    HASH=$(bit intent list | tail -1 | awk '{print $1}')

    bit job from-intent --intent-id $HASH
    JOB_ID=$(bit job list | tail -1 | awk '{print $1}')
    JOB_IDS+=($JOB_ID)

    bit plan generate --job-id $JOB_ID
    bit approve --job-id $JOB_ID
done

# Run all jobs in parallel
for job_id in "${JOB_IDS[@]}"; do
    bit run --job-id $job_id &
done

# Wait for all to complete
wait

# Collect results
mkdir -p ~/normalized_episodes
for job_id in "${JOB_IDS[@]}"; do
    cp ~/workspace/jobs/$job_id/artifacts/* ~/normalized_episodes/
done

echo "✓ All episodes normalized"
```

---

### Pattern 4: Dynamic Intent Based on Input

Generate intents programmatically:

```bash
#!/bin/bash
# Analyze file and create appropriate intent

FILE=$1
FILETYPE=$(file -b $FILE | awk '{print $1}')
FILESIZE=$(du -h $FILE | awk '{print $1}')

case $FILETYPE in
    "RIFF")
        # Audio file
        bit intent synth --text "Normalize $FILE to standard loudness. \
          File size: $FILESIZE. Must preserve audio quality."
        ;;
    "ISO")
        # Video file
        bit intent synth --text "Transcode video $FILE to MP4 format. \
          File size: $FILESIZE. Target bitrate: 5 Mbps"
        ;;
    "SQLite")
        # Database
        bit intent synth --text "Backup database $FILE with \
          compression and integrity verification"
        ;;
    *)
        echo "Unknown file type: $FILETYPE"
        exit 1
        ;;
esac

HASH=$(bit intent list | tail -1 | awk '{print $1}')
bit job from-intent --intent-id $HASH
```

---

## 🔍 Advanced Monitoring

### Real-Time Metrics Dashboard

```bash
#!/bin/bash
# Monitor multiple jobs with live metrics

watch -n 1 'echo "=== Active Jobs ===" && \
  bit job list | grep RUNNING && \
  echo "" && \
  echo "=== Resource Usage ===" && \
  free -h && \
  echo "" && \
  echo "=== Disk Usage ===" && \
  df -h ~/workspace | tail -1'
```

### Parse Event Logs for Analytics

```bash
#!/bin/bash
# Extract performance metrics from logs

JOB_ID=$1

echo "=== Execution Timeline ==="
jq -r '.timestamp, .type' ~/workspace/jobs/$JOB_ID/logs/*.jsonl | \
  paste - - | sort

echo ""
echo "=== Step Durations ==="
jq -r 'select(.type == "step.completed") |
  {step: .payload.step_id, duration: .payload.duration}' \
  ~/workspace/jobs/$JOB_ID/logs/*.jsonl

echo ""
echo "=== Total Execution Time ==="
START=$(jq -r 'select(.type == "job.started") | .timestamp' \
  ~/workspace/jobs/$JOB_ID/logs/*.jsonl | head -1)
END=$(jq -r 'select(.type == "job.completed") | .timestamp' \
  ~/workspace/jobs/$JOB_ID/logs/*.jsonl | tail -1)

echo "Start: $START"
echo "End: $END"
```

### Export Metrics for Graphing

```bash
#!/bin/bash
# Export job metrics to CSV for analysis

JOB_ID=$1

echo "step_id,status,duration_seconds" > metrics.csv

jq -r 'select(.type | contains("step")) |
  [.payload.step_id, .type, .payload.duration] | @csv' \
  ~/workspace/jobs/$JOB_ID/logs/*.jsonl >> metrics.csv

# Import into spreadsheet or graphing tool
echo "✓ Metrics exported to metrics.csv"
```

---

## 🔐 Security & Audit

### Audit Trail Extraction

```bash
#!/bin/bash
# Create audit report of all approvals

echo "=== Approval Audit Trail ===" > audit.log
echo "Generated: $(date)" >> audit.log
echo "" >> audit.log

for job_dir in ~/workspace/jobs/*/; do
    JOB_ID=$(basename $job_dir)
    echo "Job: $JOB_ID" >> audit.log

    # Extract approval records
    grep -A5 "approval_log:" $job_dir/job.yaml >> audit.log || true
    echo "" >> audit.log
done

cat audit.log
```

### Validate Job Integrity

```bash
#!/bin/bash
# Verify no tampering of job specifications

JOB_ID=$1

echo "Validating job $JOB_ID..."

# Verify hash hasn't changed
bit job validate --job-id $JOB_ID

if [[ $? -eq 0 ]]; then
    echo "✓ Job integrity verified"
else
    echo "✗ WARNING: Job may have been tampered with!"
fi
```

---

## 🚀 Performance Optimization

### Batch Processing with Resource Pooling

```bash
#!/bin/bash
# Process many jobs efficiently

MAX_CONCURRENT=4
QUEUE_FILE="/tmp/job_queue.txt"

# Create queue
bit job list | grep DRAFT | awk '{print $1}' > $QUEUE_FILE

# Process with concurrency limit
parallel --jobs $MAX_CONCURRENT \
  'bit plan generate --job-id {}; \
   bit approve --job-id {}; \
   bit run --job-id {}' \
  :::: $QUEUE_FILE

echo "✓ Batch processing complete"
```

### Cache-Aware Processing

```bash
#!/bin/bash
# Skip processing if output already cached

INTENT="Normalize audio.wav"

# Check if similar job already completed
EXISTING=$(grep -l "$INTENT" ~/workspace/jobs/*/job.yaml 2>/dev/null | \
  xargs -I {} dirname {} | \
  xargs -I {} bash -c 'grep COMPLETED {}/job.yaml > /dev/null && echo {}')

if [[ -n "$EXISTING" ]]; then
    echo "✓ Using cached result from $EXISTING"
    cp $EXISTING/artifacts/* ~/output/
else
    echo "No cache hit - running job"
    bit intent synth --text "$INTENT"
    # ... run job ...
fi
```

---

## 🔌 Integration Patterns

### Webhook Notifications

```bash
#!/bin/bash
# Send notification when job completes

JOB_ID=$1
WEBHOOK_URL="https://hooks.slack.com/..."

while [[ $(bit status --job-id $JOB_ID | grep status) == *"RUNNING"* ]]; do
    sleep 10
done

# Send notification
STATUS=$(bit job show --job-id $JOB_ID | grep status)
curl -X POST $WEBHOOK_URL \
  -d "Job $JOB_ID completed with status: $STATUS"
```

### REST API Bridge

```bash
#!/bin/bash
# Expose jobs via simple HTTP server

PORT=8080

# Start simple HTTP server
cd ~/workspace
python3 -m http.server $PORT &
SERVER_PID=$!

echo "✓ Concierge API running on http://localhost:$PORT"
echo "  Jobs: http://localhost:$PORT/jobs/"
echo "  Packages: http://localhost:$PORT/packages/"

trap "kill $SERVER_PID" EXIT
wait
```

### Message Queue Integration

```bash
#!/bin/bash
# Subscribe to job queue and process

# Assuming RabbitMQ is running
python3 << 'EOF'
import pika
import subprocess
import json

connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
channel = connection.channel()

def process_job(ch, method, properties, body):
    job_spec = json.loads(body)
    cmd = f"bit run --job-id {job_spec['job_id']}"
    result = subprocess.run(cmd, shell=True)
    ch.basic_ack(delivery_tag=method.delivery_tag)

channel.basic_consume('concierge_jobs', process_job)
channel.start_consuming()
EOF
```

---

## 🎓 Advanced Configuration

### Multi-Environment Setup

```bash
# Development
export CONCIERGE_ENV=dev
bit ws open --path ~/workspace_dev

# Staging
export CONCIERGE_ENV=staging
bit ws open --path ~/workspace_staging

# Production
export CONCIERGE_ENV=prod
bit ws open --path ~/workspace_prod
```

### Dynamic Configuration Loading

```bash
#!/bin/bash
# Load config based on environment

ENV=${CONCIERGE_ENV:-dev}
CONFIG="config.$ENV.json"

if [[ -f "$CONFIG" ]]; then
    # Copy config to workspace
    cp $CONFIG ~/workspace/concierge.json
    bit ws open --path ~/workspace
fi
```

---

## 🔬 Experimental Features

### Custom Worker Development

```bash
# Framework for custom worker
python3 << 'EOF'
from abc import ABC, abstractmethod

class CustomWorker(ABC):
    def execute(self, inputs, params):
        # Your custom logic here
        pass

    def validate(self):
        # Validate inputs
        pass

class MyProcessor(CustomWorker):
    def execute(self, inputs, params):
        # Implementation
        result = self.process(inputs['data'])
        return {'output': result}

    def process(self, data):
        # Custom processing
        return data.upper()
EOF
```

### Plugin System

```bash
#!/bin/bash
# Load plugins from plugins directory

PLUGINS_DIR=~/concierge_plugins

for plugin in $PLUGINS_DIR/*.sh; do
    source $plugin
    echo "✓ Loaded plugin: $(basename $plugin)"
done
```

---

## 📊 Advanced Analytics

### Job Success Rate Analysis

```bash
#!/bin/bash
# Calculate success metrics

TOTAL=$(bit job list | wc -l)
COMPLETED=$(bit job list | grep COMPLETED | wc -l)
FAILED=$(bit job list | grep FAILED | wc -l)
RUNNING=$(bit job list | grep RUNNING | wc -l)

SUCCESS_RATE=$((COMPLETED * 100 / TOTAL))

echo "Total Jobs: $TOTAL"
echo "Completed: $COMPLETED"
echo "Failed: $FAILED"
echo "Running: $RUNNING"
echo "Success Rate: $SUCCESS_RATE%"
```

### Timeline Analysis

```bash
#!/bin/bash
# Analyze job creation over time

echo "Jobs created per day (last 7 days):"
find ~/workspace/jobs -type f -name "job.yaml" \
  -mtime -7 -exec ls -l {} \; | \
  awk '{print $6, $7}' | \
  sort | uniq -c
```
