# Concierge Quick Reference

One-page command reference for common workflows.

## 🔧 Setup

```bash
bit init ~/workspace                    # Create workspace
bit ws open --path ~/workspace          # Open workspace
bit mode set --name code                # Set mode (chat|code|snap|xform)
```

## 💭 Intent & Jobs

```bash
bit intent synth --text "Your intent"   # Create intent from text
bit intent list                         # List all intents
bit intent show --hash ABC123           # Show intent details
bit intent verify --hash ABC123         # Verify intent hash

bit job from-intent --intent-id ABC123  # Create job from intent
bit job list                            # List all jobs
bit job show --job-id j_xyz             # Show job details
bit job validate --job-id j_xyz         # Validate job integrity
```

## 📦 Packages

```bash
bit package list                        # List all packages
bit package show --package-id audio.normalize  # Show package
bit package search --query compress     # Search packages
bit package validate --package-id audio.normalize  # Validate package
```

## 📋 Planning & Approval

```bash
bit plan generate --job-id j_xyz        # Generate execution plan
bit plan list --job-id j_xyz            # List all plans for job
bit plan show --job-id j_xyz --plan-id p_abc  # Show plan details

bit approve --job-id j_xyz              # Approve job
bit approve --job-id j_xyz --note "Ready"  # Approve with note
bit deny --job-id j_xyz                 # Deny job (return to PLANNED)
bit deny --job-id j_xyz --reason "Need adjustment"  # Deny with reason
```

## ▶️ Execution & Monitoring

```bash
bit run --job-id j_xyz                  # Execute approved job

bit status --job-id j_xyz               # Show job status
bit tail --job-id j_xyz                 # Stream logs (last 10 lines)
bit tail --job-id j_xyz --lines 20      # Stream with custom limit
bit tail --job-id j_xyz --run-id r_abc  # Stream specific run

bit artifacts --job-id j_xyz            # List job outputs
```

## ⚙️ Configuration

```bash
bit config get                          # Show full config
bit config get --component planner      # Show planner settings
bit config set planner confidence_threshold 0.85  # Update setting
bit config worker enable audio_normalizer  # Enable worker
bit config worker disable audio_normalizer  # Disable worker
```

## 📊 Status & Info

```bash
bit mode list                           # List available modes
bit mode show                           # Show current mode
bit ws show                             # Show workspace info
bit ws validate                         # Validate workspace
```

---

## 🎯 Common Workflows

### Workflow: Single Task (Quickest)
```bash
bit intent synth --text "Your task"
bit job from-intent --intent-id <hash>
bit plan generate --job-id <job_id>
bit approve --job-id <job_id>
bit run --job-id <job_id>
bit artifacts --job-id <job_id>
```

### Workflow: Review Before Approval
```bash
bit plan generate --job-id <job_id>
bit plan show --job-id <job_id> --plan-id <plan_id>
# Review output
bit approve --job-id <job_id> --note "Looks good"
bit run --job-id <job_id>
```

### Workflow: Monitor Execution
```bash
bit run --job-id <job_id> &           # Background execution
bit tail --job-id <job_id> --lines 20 # Watch logs
bit status --job-id <job_id>          # Check status
wait                                   # Wait for background job
```

### Workflow: Retry After Denial
```bash
bit deny --job-id <job_id> --reason "Need parameter change"
# Job returns to PLANNED
bit plan generate --job-id <job_id>   # Regenerate with new constraints
bit approve --job-id <job_id>
bit run --job-id <job_id>
```

### Workflow: Batch Multiple Jobs
```bash
for intent in "task1" "task2" "task3"; do
  bit intent synth --text "$intent"
done
# Get hashes...
for hash in <hash1> <hash2> <hash3>; do
  bit job from-intent --intent-id $hash
done
# Get job IDs...
for job in <job1> <job2> <job3>; do
  bit plan generate --job-id $job
  bit approve --job-id $job
  bit run --job-id $job &
done
wait
```

---

## 📁 File Structure

```
~/workspace/
├── intents/           # Synthesized intents (JSON)
├── jobs/              # Job specs and execution state
│   └── <job_id>/
│       ├── job.yaml   # Job specification
│       ├── plans/     # Execution plans
│       ├── logs/      # Event logs (JSONL)
│       └── artifacts/ # Job outputs
├── packages/          # Task package registry
│   └── <category>/<name>/v<version>/package.yaml
├── concierge.json     # Configuration
└── .concierge/
    └── session.json   # Session state
```

---

## 🔑 Key Concepts (30-Second Versions)

**Intent**: What you want to do (natural language → structured)

**Job**: Executable specification derived from intent (DRAFT status)

**Package**: Declarative recipe defining how to do something (14-section spec)

**Plan**: Concrete execution strategy matching job to package (resolves inputs/resources)

**Approval**: Human/system validation before execution (safety gate)

**Execution**: Router walks pipeline steps, emits events, creates artifacts

**Artifacts**: Job outputs stored in jobs/<job_id>/artifacts/

---

## 💾 Data Locations

| Item | Location |
|------|----------|
| Intents | `workspace/intents/*.json` |
| Jobs | `workspace/jobs/<job_id>/job.yaml` |
| Plans | `workspace/jobs/<job_id>/plans/*.yaml` |
| Logs | `workspace/jobs/<job_id>/logs/*.jsonl` |
| Outputs | `workspace/jobs/<job_id>/artifacts/*` |
| Packages | `workspace/packages/<cat>/<name>/v<ver>/` |
| Config | `workspace/concierge.json` |

---

## 🚀 Pro Tips

1. **Parallel Jobs**: Run multiple jobs with `&` suffix
2. **Watch Progress**: Use `watch bit status --job-id <id>`
3. **Grep Logs**: `cat workspace/jobs/<id>/logs/*.jsonl | grep error`
4. **Export Artifacts**: `cp workspace/jobs/<id>/artifacts/* ~/output/`
5. **Check Disk**: Packages stored in `workspace/packages/` for reference
6. **Batch Mode**: Write shell loops for multiple intents
7. **Integration**: Mount artifacts to CDN/S3 after completion
8. **Debugging**: View full logs with `tail -f workspace/jobs/<id>/logs/*`

---

## ⚡ Speed Hacks

**Create alias**:
```bash
alias bj='bit job from-intent --intent-id'
alias bp='bit plan generate --job-id'
alias ba='bit approve --job-id'
alias br='bit run --job-id'
```

**One-liner workflow**:
```bash
HASH=$(bit intent synth --text "task" | grep -oP '\b[a-f0-9]{16}\b'); \
JOB=$(bit job from-intent --intent-id $HASH | grep -oP 'j_\S+'); \
bit plan generate --job-id $JOB && bit approve --job-id $JOB && bit run --job-id $JOB
```

**Monitor in tmux**:
```bash
tmux new-session -d -s work
tmux send-keys -t work "bit run --job-id $JOB" Enter
tmux send-keys -t work "bit tail --job-id $JOB" Enter
tmux attach -t work
```

---

## 📞 Help & Resources

```bash
bit --help                              # General help
bit <command> --help                    # Command-specific help
```

**Documentation**:
- `MANUAL.md` - Full command reference
- `ARCHITECTURE.md` - System design
- `WORKFLOW.md` - Detailed user guide
- `docs/examples/` - Real workflow examples
- `README.md` - Project overview

**Troubleshooting**:
- Check `workspace/jobs/<id>/logs/` for error details
- Verify `workspace/concierge.json` configuration
- Validate workspace: `bit ws validate`
- Check package availability: `bit package list`
