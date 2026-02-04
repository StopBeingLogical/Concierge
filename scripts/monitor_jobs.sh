#!/bin/bash
# Real-time job monitoring dashboard

WORKSPACE=${1:-~/workspace}
REFRESH_INTERVAL=${2:-2}

bit ws open --path "$WORKSPACE"

clear

while true; do
    clear

    # Header
    echo "╔════════════════════════════════════════════════════════════════════╗"
    echo "║                    CONCIERGE JOB MONITOR                           ║"
    echo "║                  $(date '+%Y-%m-%d %H:%M:%S')                             ║"
    echo "╚════════════════════════════════════════════════════════════════════╝"
    echo ""

    # Stats
    TOTAL=$(bit job list 2>/dev/null | wc -l)
    RUNNING=$(bit job list 2>/dev/null | grep -c RUNNING || echo 0)
    COMPLETED=$(bit job list 2>/dev/null | grep -c COMPLETED || echo 0)
    FAILED=$(bit job list 2>/dev/null | grep -c FAILED || echo 0)
    DRAFT=$(bit job list 2>/dev/null | grep -c DRAFT || echo 0)
    PLANNED=$(bit job list 2>/dev/null | grep -c PLANNED || echo 0)

    echo "📊 Summary:"
    echo "   Total: $TOTAL  |  Running: $RUNNING  |  Completed: $COMPLETED  |  Failed: $FAILED"
    echo "   Draft: $DRAFT  |  Planned: $PLANNED"
    echo ""

    # Resource Usage
    echo "💾 System Resources:"
    FREE_MEM=$(free -h | awk 'NR==2 {print $7}')
    DISK_USAGE=$(df -h "$WORKSPACE" | awk 'NR==2 {print $5}')
    DISK_FREE=$(df -h "$WORKSPACE" | awk 'NR==2 {print $4}')
    echo "   Memory: $FREE_MEM free  |  Disk: $DISK_USAGE used ($DISK_FREE free)"
    echo ""

    # Running Jobs
    if [[ $RUNNING -gt 0 ]]; then
        echo "⏳ Running Jobs:"
        bit job list 2>/dev/null | grep RUNNING | while read -r line; do
            job_id=$(echo "$line" | awk '{print $1}')
            status=$(bit status --job-id "$job_id" 2>/dev/null | grep "Current Step" | cut -d: -f2 | xargs)
            echo "   • $job_id - $status"
        done
        echo ""
    fi

    # Recent Completed
    if [[ $COMPLETED -gt 0 ]]; then
        echo "✓ Recent Completions (last 5):"
        bit job list 2>/dev/null | grep COMPLETED | tail -5 | while read -r line; do
            job_id=$(echo "$line" | awk '{print $1}')
            echo "   • $job_id"
        done
        echo ""
    fi

    # Recent Failures
    if [[ $FAILED -gt 0 ]]; then
        echo "✗ Recent Failures (last 5):"
        bit job list 2>/dev/null | grep FAILED | tail -5 | while read -r line; do
            job_id=$(echo "$line" | awk '{print $1}')
            echo "   • $job_id"
        done
        echo ""
    fi

    # Controls
    echo "╔════════════════════════════════════════════════════════════════════╗"
    echo "║  q: quit  | r: refresh now  | j <id>: show job details           ║"
    echo "╚════════════════════════════════════════════════════════════════════╝"

    # Interactive mode
    read -t "$REFRESH_INTERVAL" -n 1 -s input

    case "$input" in
        q|Q) echo "Exiting..."; exit 0 ;;
        r|R) continue ;;
        j|J)
            read -p "Enter job ID: " job_id
            bit job show --job-id "$job_id"
            read -p "Press Enter to continue..."
            ;;
    esac
done
