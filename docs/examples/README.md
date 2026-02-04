# Concierge Workflow Examples

Complete, production-ready workflows demonstrating the Concierge system from initialization to completion.

## 📚 Example Index

### 1. **Audio Normalization** (Beginner-Friendly)
**File**: `workflow_audio_normalization.md`

Normalize podcast audio to standard loudness levels.

**Learning Path**:
- Intent synthesis from natural language
- Automatic package matching
- Plan approval workflow
- Real-time execution monitoring
- Artifact management

**Use Case**: Content creators, podcast producers, audio engineers

**Duration**: ~45 minutes execution

**Commands**:
```bash
bit intent synth --text "Normalize podcast audio to -14 LUFS"
bit job from-intent --intent-id <hash>
bit plan generate --job-id <job_id>
bit approve --job-id <job_id>
bit run --job-id <job_id>
```

---

### 2. **Database Backup** (Intermediate)
**File**: `workflow_database_backup.md`

Create production database backups with compression and verification.

**Learning Path**:
- Complex multi-step pipelines (5 steps)
- Approval gates for data protection
- Manifest generation and integrity checking
- Integration with external systems
- Error recovery strategies
- Scheduled execution

**Use Case**: Database administrators, DevOps engineers, backup operators

**Duration**: ~10 minutes execution (487 GB database example)

**Key Features**:
- Connection validation
- Size estimation
- Parallel export
- Compression (zstd)
- Checksum verification
- Manifest generation

**Commands**:
```bash
bit intent synth --text "Backup production database with compression and verification"
bit job from-intent --intent-id <hash>
bit plan generate --job-id <job_id>
bit approve --job-id <job_id> --note "Approved for production backup"
bit run --job-id <job_id>
bit artifacts --job-id <job_id>
```

---

### 3. **Video Transcoding** (Advanced)
**File**: `workflow_video_transcoding.md`

Convert video between formats with GPU acceleration and quality control.

**Learning Path**:
- GPU resource management
- Parallel job execution
- Quality metrics and statistics
- Progress monitoring during long operations
- Multi-format output strategies
- CDN integration patterns

**Use Case**: Video engineers, streaming platforms, content distribution

**Duration**: ~45 minutes execution (4K video example)

**Key Features**:
- Hardware acceleration (GPU)
- Format conversion (MP4, WebM, MKV)
- Bitrate optimization
- Resolution downsampling
- Quality scoring
- Performance metrics

**Commands**:
```bash
bit intent synth --text "Convert 4K video to MP4 with 8 Mbps bitrate and GPU acceleration"
bit job from-intent --intent-id <hash>
bit plan generate --job-id <job_id>
bit approve --job-id <job_id>
bit run --job-id <job_id>  # Watch GPU utilization
bit tail --job-id <job_id> --lines 20
bit artifacts --job-id <job_id>
```

---

## 🎯 Learning Paths

### Path 1: Beginner (30-60 minutes)
Perfect for learning Concierge basics:
1. Start with **Audio Normalization** - simplest workflow (2 steps)
2. Understand intent synthesis and package matching
3. Learn approval and execution flow
4. View artifacts

**Concepts**: Intent → Job → Plan → Approval → Execution

---

### Path 2: Intermediate (60-120 minutes)
Build on basics with production workflows:
1. **Audio Normalization** (review basics)
2. **Database Backup** (5-step pipeline)
3. Understand verification and checksums
4. Learn manifest generation
5. Explore error handling

**Concepts**: Multi-step pipelines, verification, manifests, integration

---

### Path 3: Advanced (120+ minutes)
Production-grade system design:
1. All previous examples
2. **Video Transcoding** (GPU, parallel execution)
3. Monitor complex, long-running jobs
4. Integrate with external systems (S3, CDN, Slack)
5. Optimize resource utilization
6. Schedule automated workflows

**Concepts**: GPU acceleration, parallelization, monitoring, integration, scheduling

---

## 🔑 Key Patterns

### Pattern 1: Simple Linear Workflow
**Example**: Audio Normalization

```
Intent → Job → Plan → Approve → Run → Artifacts
```

Used for: Single-step or sequential operations

---

### Pattern 2: Multi-Step Pipeline with Verification
**Example**: Database Backup

```
Intent → Job → Plan → Approve → Run (5 steps) → Verify → Manifest → Artifacts
```

Used for: Complex operations requiring validation and checksums

---

### Pattern 3: Parallel Execution
**Example**: Video Transcoding (MP4 + WebM simultaneously)

```
Intent 1 → Job 1 → Plan 1 → Approve 1 → Run 1
Intent 2 → Job 2 → Plan 2 → Approve 2 → Run 2
(Run simultaneously, monitor independently)
```

Used for: Multi-format output, batch processing

---

## 💡 Common Tasks

### Task: Generate Different Output Formats
Use video transcoding pattern - create separate jobs for each format, approve both, run in parallel.

### Task: Scheduled Backups
Use database backup with cron scheduling - wrapper script handles recurring execution.

### Task: Monitor Long-Running Jobs
Use `bit tail --job-id <job_id> --lines N` for real-time progress, `bit status` for summary.

### Task: Integrate with External Systems
After job completes, use artifacts directory as input for:
- S3 upload (`aws s3 cp`)
- CDN distribution
- Slack notifications
- Email alerts

### Task: Retry Failed Jobs
Use `bit deny` to return job to PLANNED state, review constraints, regenerate plan, approve again.

---

## 📋 Checklist for Each Workflow

Before running any workflow:

- [ ] Workspace initialized: `bit init <path>`
- [ ] Workspace open: `bit ws open --path <path>`
- [ ] Mode set: `bit mode set --name code`
- [ ] Input files/data prepared
- [ ] Resource availability checked (disk, CPU, GPU if needed)
- [ ] Output directory accessible

During execution:

- [ ] Monitor progress: `bit status --job-id <job_id>`
- [ ] Watch logs: `bit tail --job-id <job_id>`
- [ ] Check resource usage (top, gpu-monitor, etc.)

After completion:

- [ ] Review artifacts: `bit artifacts --job-id <job_id>`
- [ ] Verify outputs
- [ ] Check manifest/stats if generated
- [ ] Integrate with downstream systems
- [ ] Archive or clean up if needed

---

## 🚀 Next Steps After Examples

1. **Adapt to Your Use Case**: Modify intents and parameters for your actual data
2. **Create Custom Packages**: Design packages for your specific workflows
3. **Automate Scheduling**: Wrap in cron or scheduler
4. **Monitor at Scale**: Log outputs to database for analytics
5. **Integrate Deeply**: Connect to your production systems

---

## 📖 Related Documentation

- **MANUAL.md** - Command reference and syntax
- **ARCHITECTURE.md** - System design and components
- **WORKFLOW.md** - Detailed user guide
- **README.md** - Project overview

---

## ❓ FAQ

**Q: Which example should I start with?**
A: Audio Normalization - it's the simplest and fastest to complete.

**Q: Can I run multiple workflows simultaneously?**
A: Yes! Each job is independent. Run them in separate terminals or background processes.

**Q: How do I customize these examples for my data?**
A: Modify the intent text with your actual file names, paths, and parameters. The package matching and planning will adapt automatically.

**Q: What if a workflow fails?**
A: Use `bit deny` to return to PLANNED status, review constraints, and regenerate the plan with corrected parameters.

**Q: How do I integrate outputs with my systems?**
A: Artifacts are stored in `jobs/<job_id>/artifacts/`. Use standard tools (aws s3 cp, curl, etc.) to integrate.
