# Concierge Scripts

Collection of utility scripts for common Concierge operations.

## Available Scripts

### 1. batch_process.sh

Process multiple files through a workflow with concurrency control.

**Usage:**
```bash
scripts/batch_process.sh <workspace> '<intent_template>' '<file_pattern>' [max_parallel]
```

**Example:**
```bash
# Normalize all WAV files, max 2 parallel jobs
scripts/batch_process.sh ~/workspace \
  'Normalize audio file {file}' \
  '*.wav' \
  2

# Compress all videos, max 1 parallel (resource intensive)
scripts/batch_process.sh ~/workspace \
  'Transcode video {file} to MP4 format' \
  '*.mkv' \
  1
```

**Features:**
- Processes files matching a pattern
- Creates intents with file name substitution
- Generates plans and approves automatically
- Runs jobs in parallel (respects max_parallel limit)
- Shows progress in real-time
- Tracks all job IDs and final statuses

**When to use:**
- Batch processing similar files
- Converting multiple files to same format
- Normalizing entire directories
- Running same workflow on many inputs

---

### 2. monitor_jobs.sh

Real-time dashboard for monitoring job execution.

**Usage:**
```bash
scripts/monitor_jobs.sh <workspace> [refresh_interval]
```

**Example:**
```bash
# Start monitor with default 2-second refresh
scripts/monitor_jobs.sh ~/workspace

# Start monitor with 5-second refresh
scripts/monitor_jobs.sh ~/workspace 5
```

**Features:**
- Real-time job status summary
- System resource monitoring (memory, disk)
- Lists all running jobs with current steps
- Shows recent completions and failures
- Interactive mode (press keys to interact)
- Auto-refreshing display

**Commands in monitor:**
- `q` - Quit
- `r` - Refresh immediately
- `j <job_id>` - Show detailed job info
- (auto-refreshes every N seconds)

**When to use:**
- Watch long-running jobs
- Monitor resource usage during execution
- Quickly check job status without commands
- Identify bottlenecks or failures

---

### 3. generate_report.sh

Generate execution report from job logs.

**Usage:**
```bash
scripts/generate_report.sh <workspace> <job_id> [output_file]
```

**Example:**
```bash
# Generate report for specific job
scripts/generate_report.sh ~/workspace j_abc123

# Generate report with custom name
scripts/generate_report.sh ~/workspace j_abc123 job_report.md

# Generate and view
scripts/generate_report.sh ~/workspace j_abc123 && cat job_report.md
```

**Report Contents:**
- Job summary (ID, status, creation time)
- Timeline of all events
- Detailed step execution info
- Artifacts generated (with sizes)
- Execution statistics
- Raw event log (last 20 events)

**Output Format:**
- Markdown (.md file)
- Easy to share
- Can be viewed in any text editor
- Can be published to wiki/documentation

**When to use:**
- Document completed jobs
- Create audit trail for compliance
- Analyze performance
- Share results with team
- Troubleshoot failures

---

## 🚀 Installation

Scripts are included in the repository:

```bash
cd /path/to/concierge
ls scripts/
```

All scripts are executable. You can also symlink them:

```bash
ln -s $(pwd)/scripts/* ~/bin/
```

---

## 📋 Script Templates

### Template 1: Custom Batch Script

Adapt `batch_process.sh` for your workflow:

```bash
#!/bin/bash

WORKSPACE=~/workspace
bit ws open --path "$WORKSPACE"

# Custom processing
for file in *.wav; do
    bit intent synth --text "Your intent with $file"
    # ... continue workflow
done
```

### Template 2: Scheduled Execution

Run scripts on schedule with cron:

```bash
# Add to crontab -e
# Run batch processing daily at 2 AM
0 2 * * * ~/concierge/scripts/batch_process.sh ~/workspace 'Your intent' '*.wav' 2

# Monitor jobs every 5 minutes
*/5 * * * * ~/concierge/scripts/monitor_jobs.sh ~/workspace 1 &
```

### Template 3: Pipeline Integration

Call scripts from your workflow:

```bash
#!/bin/bash

# Run batch processing
~/concierge/scripts/batch_process.sh ~/workspace \
  'Process file {file}' \
  '*.input'

# Wait for completion (30 minutes max)
timeout 1800 bash -c 'while ! ~/concierge/scripts/monitor_jobs.sh ~/workspace 1 | grep -q "Running: 0"; do sleep 5; done'

# Generate reports
for job_id in $(bit job list | grep COMPLETED | awk '{print $1}'); do
    ~/concierge/scripts/generate_report.sh ~/workspace "$job_id" "report_${job_id}.md"
done
```

---

## 🔧 Customization

### Modify batch_process.sh

Change parallelism strategy:

```bash
# Edit this section
while [[ $RUNNING -ge $MAX_PARALLEL ]]; do
    # Add logic for priority queuing
    # or adaptive parallelism
done
```

### Modify monitor_jobs.sh

Add custom metrics:

```bash
# Add this to report section
GPU_USAGE=$(nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader | head -1)
echo "GPU: $GPU_USAGE"
```

### Modify generate_report.sh

Add custom sections:

```bash
# Add after Statistics section
cat >> "$OUTPUT_FILE" << EOF

## Custom Analysis

Your analysis here...
EOF
```

---

## 🐛 Troubleshooting

### Script not executable
```bash
chmod +x scripts/*.sh
```

### Script can't find workspace
```bash
# Always pass explicit path
scripts/batch_process.sh ~/workspace 'intent' 'pattern'

# Or set WORKSPACE env var
export WORKSPACE=~/workspace
scripts/batch_process.sh $WORKSPACE 'intent' 'pattern'
```

### Monitor shows no jobs
```bash
# Verify workspace is correct
bit ws show

# Verify jobs exist
bit job list
```

### Report not generated
```bash
# Check job exists
bit job show --job-id <job_id>

# Check logs directory
ls ~/workspace/jobs/<job_id>/logs/
```

---

## 📊 Common Recipes

### Recipe 1: Normalize Podcasts

```bash
scripts/batch_process.sh ~/podcast \
  'Normalize audio volume in {file} to -14 LUFS' \
  'episodes/*.wav' \
  2

# Then monitor
scripts/monitor_jobs.sh ~/podcast
```

### Recipe 2: Generate Reports for All Jobs

```bash
bit job list | grep COMPLETED | awk '{print $1}' | while read job_id; do
    scripts/generate_report.sh ~/workspace "$job_id" "reports/${job_id}.md"
done
```

### Recipe 3: Batch with Error Handling

```bash
scripts/batch_process.sh ~/workspace \
  'Process file {file}' \
  '*.input' \
  4

# Check for failures
bit job list | grep FAILED | while read job_id; do
    echo "Failed: $job_id"
    scripts/generate_report.sh ~/workspace "$job_id" "failure_${job_id}.md"
done
```

---

## 🤝 Contributing Scripts

Have a useful script? Share it!

**Script Guidelines:**
- Use bash (for compatibility)
- Add usage information
- Handle errors gracefully
- Support customization
- Document examples

---

## 📞 Support

**Issues with scripts?**
- Check troubleshooting section above
- Review script comments
- Run with `-x` flag for debugging: `bash -x scripts/script.sh`
- Check workspace configuration

**Bugs or improvements?**
- Report to project GitHub
- Suggest improvements
- Share your custom scripts
