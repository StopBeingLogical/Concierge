# Workflow Example: Video Transcoding

Complete example of converting video between formats with GPU acceleration.

## Scenario

You have a 4K video source (50 GB) that needs to be converted to web-optimized MP4 format for streaming and also to WebM for fallback.

## Quick Start

```bash
bit init ~/video_processing
bit ws open --path ~/video_processing
bit mode set --name code

# Two workflows - one for each format

# Workflow 1: Transcode to MP4 (primary)
bit intent synth --text "Convert 4K video source_4k.mkv to MP4 format with \
  8 Mbps bitrate for streaming. Must use hardware acceleration. \
  Target quality: medium preset."

INTENT_HASH_MP4="xyz789abc123"  # Replace with actual
bit job from-intent --intent-id $INTENT_HASH_MP4
JOB_MP4="j_video_mp4_xyz"  # Replace with actual

bit plan generate --job-id $JOB_MP4
bit approve --job-id $JOB_MP4 --note "Approved for streaming MP4"
bit run --job-id $JOB_MP4

# Monitor
bit tail --job-id $JOB_MP4 --lines 15

# Check artifacts
bit artifacts --job-id $JOB_MP4

# Workflow 2: Transcode to WebM (fallback)
bit intent synth --text "Convert source_4k.mkv to WebM format with \
  6 Mbps bitrate for browser compatibility fallback. \
  Use VP9 codec with hardware acceleration."

INTENT_HASH_WEBM="qrs456def789"  # Replace with actual
bit job from-intent --intent-id $INTENT_HASH_WEBM
JOB_WEBM="j_video_webm_xyz"  # Replace with actual

bit plan generate --job-id $JOB_WEBM
bit approve --job-id $JOB_WEBM --note "Approved for WebM fallback"
bit run --job-id $JOB_WEBM
```

## Detailed Walkthrough

### Step 1: Analyze Requirements

Your intent synthesizer extracts:
- **Source**: 4K video (source_4k.mkv)
- **Target Format**: MP4 and WebM
- **Bitrates**: 8 Mbps (MP4), 6 Mbps (WebM)
- **Quality**: Medium preset (fast encoding, good quality balance)
- **Hardware**: GPU acceleration enabled

### Step 2: Plan Generation

For MP4 workflow:

```yaml
package_id: video.transcode
version: 1.0.0
matched_confidence: 0.89

Pipeline (2 steps):
  1. validate_input - Verify source video codec and format
  2. transcode_video - Convert to MP4 with GPU acceleration

Input Resolution: 3840x2160 (4K)
Output Resolution: 1920x1080 (Full HD, downscaled)
Estimated Duration: 45 minutes
Resources Required:
  CPU: 4 cores
  GPU: Required (NVIDIA RTX recommended)
  Memory: 4 GB
  Disk: 20 GB (temp space for processing)

Approval: Required (resource-intensive video operation)
```

### Step 3: Execution - MP4 Workflow

```
Running job j_video_mp4_xyz

Step 1/2: validate_input
  ✓ Source file: source_4k.mkv
  ✓ Codec: H.265 (HEVC)
  ✓ Resolution: 3840x2160 (4K)
  ✓ Frame rate: 29.97 fps
  ✓ Duration: 2h 15m 33s
  ✓ File size: 50 GB
  ✓ Audio tracks: 2 (English, Spanish)

Step 2/2: transcode_video
  ✓ Starting GPU-accelerated transcoding...
  ✓ GPU: NVIDIA RTX 3080 (10GB VRAM)
  ⏳ Processing: 0:00:00 → 0:15:30 (progress: 11%)
  ⏳ Processing: 0:15:30 → 0:31:00 (progress: 23%)
  ⏳ Processing: 0:31:00 → 0:46:30 (progress: 34%)
  ⏳ Processing: 0:46:30 → 1:02:00 (progress: 45%)
  ⏳ Processing: 1:02:00 → 1:17:30 (progress: 57%)
  ⏳ Processing: 1:17:30 → 1:33:00 (progress: 68%)
  ⏳ Processing: 1:33:00 → 1:48:30 (progress: 79%)
  ⏳ Processing: 1:48:30 → 2:00:00 (progress: 89%)
  ⏳ Finalizing output...
  ✓ Transcoding complete

  Statistics:
    Output Resolution: 1920x1080
    Output Format: MP4 (H.264)
    Output Bitrate: 8 Mbps
    Output File Size: 8.1 GB
    Processing Time: 42 minutes
    GPU Utilization: 92% average
    Quality Score: 0.92 (excellent)

Job completed successfully in 42m 15s
```

### Step 4: Monitor Progress

Real-time log streaming:

```bash
$ bit tail --job-id j_video_mp4_xyz --lines 20
```

Output:
```
2026-02-04T14:15:30Z [job.started] Starting video transcoding job
2026-02-04T14:15:35Z [step.validate_input.started] Validating source video...
2026-02-04T14:15:40Z [worker.video_validator] Source: 4K H.265, 50GB
2026-02-04T14:15:45Z [step.validate_input.completed] Validation passed
2026-02-04T14:16:00Z [step.transcode_video.started] Starting GPU transcoding...
2026-02-04T14:16:05Z [worker.gpu_transcoder] GPU ready: NVIDIA RTX 3080
2026-02-04T14:16:10Z [worker.gpu_transcoder] Queue initialized
2026-02-04T14:16:15Z [worker.gpu_transcoder] Transcoding started: 4K→Full HD
2026-02-04T14:30:45Z [worker.gpu_transcoder] Progress: 33% (0:45:00 / 2:15:33)
2026-02-04T14:45:15Z [worker.gpu_transcoder] Progress: 67% (1:31:00 / 2:15:33)
2026-02-04T14:57:30Z [worker.gpu_transcoder] Progress: 95% (2:08:00 / 2:15:33)
2026-02-04T14:58:00Z [worker.gpu_transcoder] Finalizing output file...
2026-02-04T14:58:45Z [step.transcode_video.completed] Transcoding complete
2026-02-04T14:58:50Z [job.completed] Job finished successfully
```

### Step 5: View Artifacts

```bash
$ bit artifacts --job-id j_video_mp4_xyz
```

Output:
```
Job artifacts:
  • source_4k_output.mp4                    8.1 GB     2026-02-04 14:58:45Z
  • transcoding_stats.json                  2.1 KB     2026-02-04 14:58:45Z
```

Transcoding stats:

```json
{
  "source": {
    "filename": "source_4k.mkv",
    "size_gb": 50,
    "resolution": "3840x2160",
    "codec": "hevc",
    "duration_seconds": 8133,
    "bitrate_mbps": 54
  },
  "output": {
    "filename": "source_4k_output.mp4",
    "size_gb": 8.1,
    "resolution": "1920x1080",
    "codec": "h264",
    "duration_seconds": 8133,
    "bitrate_mbps": 8
  },
  "processing": {
    "duration_seconds": 2535,
    "gpu_used": "NVIDIA RTX 3080",
    "gpu_utilization_percent": 92,
    "cpu_utilization_percent": 25,
    "memory_used_gb": 3.2
  },
  "quality": {
    "ssim_score": 0.92,
    "frame_drop_count": 0,
    "audio_preserved": true
  }
}
```

## Parallel Processing

Run both workflows simultaneously for efficiency:

```bash
# In terminal 1
bit run --job-id j_video_mp4_xyz &

# In terminal 2
bit run --job-id j_video_webm_xyz &

# Monitor both
watch "bit status --job-id j_video_mp4_xyz; echo '---'; \
       bit status --job-id j_video_webm_xyz"
```

Since each uses separate GPU resources, they can run in parallel.

## Integration with CDN

After transcoding:

```bash
# Upload both formats to CDN
for format in mp4 webm; do
    file=$(find jobs/j_video_${format}_xyz/artifacts -name "*.${format}")
    aws s3 cp "$file" s3://cdn-videos/streaming/source_4k.${format} \
        --storage-class INTELLIGENT_TIERING \
        --metadata "format=${format},quality=hd"
done

# Update video manifest
cat > video_manifest.json << EOF
{
  "title": "Video Asset",
  "sources": [
    {
      "src": "https://cdn.example.com/streaming/source_4k.mp4",
      "type": "video/mp4",
      "codecs": "avc1.42E01E",
      "size": "8.1GB"
    },
    {
      "src": "https://cdn.example.com/streaming/source_4k.webm",
      "type": "video/webm",
      "codecs": "vp9",
      "size": "6.2GB"
    }
  ],
  "thumbnail": "https://cdn.example.com/thumbnails/source_4k.jpg"
}
EOF
```

## Key Learning Points

1. **GPU Utilization**: Approval gates can verify GPU availability before starting
2. **Progress Monitoring**: Real-time event logs show percentage completion
3. **Parallel Execution**: Multiple jobs can run simultaneously for efficiency
4. **Quality Metrics**: Output statistics verify transcoding quality
5. **Artifact Management**: All outputs organized per job for easy integration

## Performance Notes

- GPU acceleration reduces 2+ hour transcoding to ~45 minutes
- Multi-format output (MP4 + WebM) ensures broad browser compatibility
- Quality downsampling (4K→1080p) reduces file size by 6x
- Processing stats help optimize future transcoding jobs
