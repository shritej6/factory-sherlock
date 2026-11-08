# ADR-0010: Commit short silent walkthrough videos

## Status

Accepted. Recorded 2026-11-07. Implemented by `scripts/development/record_walkthroughs.py`, the `make videos` target, and the files in `docs/media/videos/`. Amends the rule in `docs/media/media-plan.md` that no video file is committed.

## Context

`docs/media/media-plan.md` (2026-11-03) specified six narrated videos and ruled that video files are hosted externally and only linked from `docs/media/videos/README.md`, to keep the repository small. On 2026-11-07 the five demonstration sequences (videos 2 to 6) were recorded as silent screen captures by a Playwright script: 1280 by 800 pixels, 25 frames per second, H.264, 1.5 to 3.4 MB each. Narration is still to be recorded by the student. Graders and reviewers clone the repository; an external link can expire, needs an account, or is simply skipped, while a file in the clone opens in any player.

## Decision

- Silent walkthrough clips produced by `scripts/development/record_walkthroughs.py` are committed to `docs/media/videos/` when each file is under 10 MB and the set of committed clips totals under 40 MB. The script re-encodes with a higher CRF or a lower frame rate when a clip exceeds 10 MB.
- Narrated recordings, slide-based videos (video 1), and any file over the limits stay external and are linked from `docs/media/videos/README.md`, as before.
- If the total would exceed 40 MB, the complete system walkthrough (video 6) is committed first, then the smallest remaining clips that fit; the rest are listed in the README as not committed.
- Clips are replaced, not accumulated: a new recording overwrites the file with the same name, so the repository holds one version of each clip plus its history.

## Consequences

Positive:

- Anyone with a clone can watch the five demonstrations without network access or an external account.
- The clips are reproducible from the demo scenario with one command (`make videos`), so a reviewer can check that the recording matches the code.

Negative or accepted costs:

- Each re-recording adds the clip size to the repository history (10.4 MB for the five clips at the first recording on 2026-11-07, 10.2 MB at the re-recording on 2026-11-08 after the interface redesign). The limits above bound the growth; re-record only when the screens change.
- Binary files do not diff. The README table (duration, size, date) is the only reviewable description of what changed.
- The silent clips are not the final deliverable; the narrated versions still have to be produced and hosted outside the repository.

## Alternatives considered

- Keep every video external (the 2026-11-03 rule). Rejected for the silent clips: the clips are small and the risk of a dead link outweighs the repository growth.
- Git LFS. Rejected: it adds a tool to the setup for a few megabytes, and the course grading environment is a plain clone.
- Animated GIFs or image sequences. Rejected: larger than H.264 at the same length and resolution, and not seekable.
