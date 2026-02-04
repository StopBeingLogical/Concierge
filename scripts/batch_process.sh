#!/bin/bash
# Batch processing script for Concierge
# Process multiple files through a workflow

set -e

# Configuration
WORKSPACE=${1:-.}
INTENT_TEMPLATE=$2
INPUT_FILES=$3
MAX_PARALLEL=${4:-2}

if [[ -z "$INTENT_TEMPLATE" ]] || [[ -z "$INPUT_FILES" ]]; then
    echo "Usage: $0 <workspace> '<intent_template>' '<input_files_pattern>' [max_parallel]"
    echo ""
    echo "Example:"
    echo "  $0 ~/workspace 'Normalize audio file {file}' '*.wav' 4"
    exit 1
fi

# Initialize
bit ws open --path "$WORKSPACE"

# Find input files
mapfile -t FILES < <(find . -name "$INPUT_FILES" -type f)

if [[ ${#FILES[@]} -eq 0 ]]; then
    echo "❌ No files matching pattern: $INPUT_FILES"
    exit 1
fi

echo "Processing ${#FILES[@]} files (max $MAX_PARALLEL parallel)"
echo ""

# Track jobs
declare -a JOB_IDS
RUNNING=0

for file in "${FILES[@]}"; do
    # Wait if at max parallelism
    while [[ $RUNNING -ge $MAX_PARALLEL ]]; do
        # Check if any jobs completed
        for i in "${!JOB_IDS[@]}"; do
            job_id=${JOB_IDS[$i]}
            status=$(bit job show --job-id "$job_id" | grep "status:" | awk '{print $2}')

            if [[ "$status" != "RUNNING" ]]; then
                echo "✓ $job_id: $status"
                unset 'JOB_IDS[$i]'
                ((RUNNING--))
            fi
        done
        sleep 1
    done

    # Create intent
    intent_text=${INTENT_TEMPLATE//\{file\}/$file}
    echo "Creating intent for: $file"
    bit intent synth --text "$intent_text"

    # Get hash from latest intent
    intent_hash=$(bit intent list | tail -1 | awk '{print $1}')

    # Create job
    bit job from-intent --intent-id "$intent_hash"
    job_id=$(bit job list | tail -1 | awk '{print $1}')

    # Generate plan and approve
    bit plan generate --job-id "$job_id"
    bit approve --job-id "$job_id" --note "Batch processing"

    # Run in background
    bit run --job-id "$job_id" &
    JOB_IDS+=("$job_id")
    ((RUNNING++))

    echo "  Started: $job_id"
done

# Wait for all remaining jobs
echo ""
echo "Waiting for remaining jobs to complete..."
wait

# Summary
echo ""
echo "=== Batch Processing Summary ==="
for job_id in "${JOB_IDS[@]}"; do
    status=$(bit job show --job-id "$job_id" 2>/dev/null | grep "status:" | awk '{print $2}' || echo "UNKNOWN")
    echo "  $job_id: $status"
done

echo "✓ Batch processing complete"
