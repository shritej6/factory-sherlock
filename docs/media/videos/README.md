# Videos

Five silent walkthrough clips (videos 2 to 6) were recorded on 2026-11-07 by `scripts/development/record_walkthroughs.py` (`make videos`) against the demo scenario plus the preparation steps in [../media-plan.md](../media-plan.md). Each clip is a Playwright screen recording of the browser at 1280 by 800 pixels, 25 frames per second, converted to H.264 MP4 with ffmpeg, without audio or cursor. The clips are committed under the rule in [ADR-0010](../../decisions/ADR-0010-commit-short-walkthrough-videos.md): under 10 MB each and under 40 MB in total (10.4 MB for the five files). Narration is still to be recorded by the student; the narrated versions and video 1 (project overview, which needs slides) are hosted externally and linked here when they exist.

Video 1 is not recorded by the script because its sequence is slides, the architecture diagram, and narration rather than browser interaction.

| # | Title | File name | Status | Duration | Size | Link |
|---|-------|-----------|--------|----------|------|------|
| 1 | Project overview | `01-project-overview.mp4` | Pending; needs slides and narration | | | |
| 2 | Virtual factory demonstration | `02-virtual-factory-demonstration.mp4` | Recorded 2026-11-07 | 2:14 | 1.7 MB | [02-virtual-factory-demonstration.mp4](02-virtual-factory-demonstration.mp4), silent, narration pending |
| 3 | Quality inspection demonstration | `03-quality-inspection-demonstration.mp4` | Recorded 2026-11-07 | 2:15 | 1.5 MB | [03-quality-inspection-demonstration.mp4](03-quality-inspection-demonstration.mp4), silent, narration pending |
| 4 | Defect investigation demonstration | `04-defect-investigation-demonstration.mp4` | Recorded 2026-11-07 | 2:07 | 2.2 MB | [04-defect-investigation-demonstration.mp4](04-defect-investigation-demonstration.mp4), silent, narration pending |
| 5 | Material traceability demonstration | `05-material-traceability-demonstration.mp4` | Recorded 2026-11-07 | 2:14 | 1.5 MB | [05-material-traceability-demonstration.mp4](05-material-traceability-demonstration.mp4), silent, narration pending |
| 6 | Complete system walkthrough | `06-complete-system-walkthrough.mp4` | Recorded 2026-11-07 | 4:34 | 3.4 MB | [06-complete-system-walkthrough.mp4](06-complete-system-walkthrough.mp4), silent, narration pending |

The six videos are specified in the media plan with purpose, audience, duration, demonstration sequence, required application state, technical concepts, and recording instructions. Each silent clip entry there says which steps of the sequence the clip covers and which are left to the narrated recording.

## Recording again

Prerequisites: `make reset-demo`, the preparation steps from the media plan (investigation, overdue check, batch `SIM0001-CNC-02-02-B04`, sample CSV import), `make backend`, `make frontend`, and `ffmpeg` on PATH. Then run `make videos`, or:

```bash
cd backend && FRONTEND_URL=http://localhost:5173 uv run --group docs python ../scripts/development/record_walkthroughs.py
```

The sequences write to the database (a manual order and batch, inspections, two simulation runs, two investigations, three quarantines), so reset the demo scenario before recording again. `VIDEOS=4,5` records a subset. The script signs in by storing an API token in the browser's local storage, so no password is typed on camera, and deletes the WebM intermediates after conversion. A full run takes about a quarter of an hour, and the browser stops rendering while the computer sleeps, which stretches a clip by the length of the nap; on a laptop run the command under `caffeinate -i` (macOS) or keep the machine awake some other way.
