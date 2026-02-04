# Workflow Example: Database Backup

Complete example of creating a production database backup with verification.

## Scenario

You need to backup your PostgreSQL production database daily with compression and integrity checking before archival.

## Quick Start

```bash
bit init ~/backup_system
bit ws open --path ~/backup_system
bit mode set --name code

# Synthesize backup intent
bit intent synth --text "Create a compressed backup of production database \
  prod_maindb with verification and manifest generation. \
  Must use zstd compression and compute SHA256 checksum for integrity."

# Get hash from output
INTENT_HASH="abc123def456"  # Replace with actual

# Create job
bit job from-intent --intent-id $INTENT_HASH
JOB_ID="j_backup_prod_xyz"  # Replace with actual

# Generate plan
bit plan generate --job-id $JOB_ID

# Review plan
bit plan show --job-id $JOB_ID --plan-id <plan-id>

# Approve with requirements
bit approve --job-id $JOB_ID \
  --note "Approved for production backup. \
           Ensure backup window is 2-4 AM UTC during low traffic."

# Execute
bit run --job-id $JOB_ID

# Monitor
bit tail --job-id $JOB_ID --lines 10

# Verify artifacts
bit artifacts --job-id $JOB_ID
```

## Detailed Walkthrough

### Plan Details

When you run `bit plan show`, you'll see:

```yaml
package_id: db.backup
version: 1.0.0
matched_confidence: 0.88

Pipeline (5 steps):
  1. validate_connection - Verify database connectivity
  2. prepare_backup - Plan backup strategy and estimate size
  3. execute_backup - Perform actual database export
  4. compress_backup - Apply zstd compression
  5. verify_backup - Compute checksums and generate manifest

Estimated Duration: 10 minutes
Resources: 2 CPU, 2GB RAM, 50GB disk

Approval: Required (data protection operation)
```

### Execution Output

```
Running job j_backup_prod_xyz

Step 1/5: validate_connection
  ✓ Connected to prod_maindb
  ✓ User has BACKUP privilege
  ✓ Network latency: 2ms

Step 2/5: prepare_backup
  ✓ Database size: 487 GB
  ✓ Table count: 245
  ✓ Estimated output: 89 GB (compressed)
  ✓ Disk space available: 800 GB

Step 3/5: execute_backup
  ✓ Starting export...
  ⏳ Processing tables 1-50 of 245
  ⏳ Processing tables 51-100 of 245
  ⏳ Processing tables 101-150 of 245
  ⏳ Processing tables 151-200 of 245
  ⏳ Processing tables 201-245 of 245
  ✓ Export complete: 487 GB raw data

Step 4/5: compress_backup
  ✓ Starting compression (zstd level 6)...
  ⏳ Compressed: 25 GB / 487 GB (5%)
  ⏳ Compressed: 50 GB / 487 GB (10%)
  ...
  ⏳ Compressed: 475 GB / 487 GB (98%)
  ✓ Compression complete: 89 GB final size
  ✓ Compression ratio: 5.5x

Step 5/5: verify_backup
  ✓ Computing checksums (SHA256)...
  ✓ Checksum: a7f3e9c2d1b8f4a6...
  ✓ Validating backup structure
  ✓ Tables verified: 245/245
  ✓ Rows verified: 1.2B
  ✓ Manifest generated

Job completed successfully in 9m 45s
```

### Artifacts

```bash
$ bit artifacts --job-id j_backup_prod_xyz
```

Output:
```
Job artifacts:
  • prod_maindb_backup_2026_02_04.sql.zstd   89 GB    2026-02-04 14:45:30Z
  • backup_manifest.json                     4.2 KB   2026-02-04 14:45:30Z
```

### Manifest Contents

The `backup_manifest.json` contains:

```json
{
  "backup_id": "backup_2026_02_04_prod_maindb",
  "timestamp": "2026-02-04T14:45:30Z",
  "database": "prod_maindb",
  "backup_format": "sql",
  "compression": "zstd",
  "statistics": {
    "original_size_gb": 487,
    "compressed_size_gb": 89,
    "compression_ratio": 5.5,
    "table_count": 245,
    "row_count": 1200000000,
    "duration_seconds": 585
  },
  "integrity": {
    "checksum_algorithm": "SHA256",
    "checksum": "a7f3e9c2d1b8f4a6e5c3b1f9d7a2e4c6",
    "verified": true
  },
  "tables": {
    "users": {"rows": 5000000, "size_mb": 512},
    "transactions": {"rows": 800000000, "size_mb": 312000},
    ...
  }
}
```

## Integration with Other Systems

After backup completes, you could:

1. **Archive to S3**:
   ```bash
   aws s3 cp jobs/j_backup_prod_xyz/artifacts/*.zstd \
     s3://backups/postgres/2026-02-04/
   ```

2. **Send Notification**:
   ```bash
   curl -X POST https://slack.webhook.io/backup \
     -d "Database backup completed: 89 GB in 9m 45s"
   ```

3. **Store Manifest**:
   ```bash
   cp jobs/j_backup_prod_xyz/artifacts/backup_manifest.json \
     /var/backups/manifests/2026_02_04.json
   ```

## Error Scenarios

If backup fails, you'll see detailed error info:

```bash
bit status --job-id j_backup_prod_xyz
```

Common failures:

- **Connection Failed**: Database unreachable - check network/credentials
- **Insufficient Disk Space**: Not enough space for backup file
- **Permission Denied**: User lacks necessary database privileges
- **Timeout**: Backup took longer than expected - increase timeout in config

All failures include:
- Exact error message
- Step where failure occurred
- Suggestions for recovery
- Event log showing what succeeded before failure

## Scheduling

For daily backups, add to crontab:

```bash
# Daily backup at 2 AM
0 2 * * * /usr/local/bin/backup_daily.sh

# Script contents:
#!/bin/bash
cd ~/backup_system
bit ws open --path ~/backup_system
bit intent synth --text "Create daily PostgreSQL backup with compression"
# ... run workflow ...
```

## Key Points

1. **Backup Gate**: Approval required ensures backup strategy is reviewed
2. **Verification**: Checksums guarantee backup integrity
3. **Manifest**: JSON provides machine-readable backup metadata
4. **Monitoring**: Real-time progress tracking during long operations
5. **Artifacts**: All outputs organized in job-specific directory
