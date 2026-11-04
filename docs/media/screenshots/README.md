# Screenshots

Nine screenshots of the running application, captured on 2026-11-03 at a 1600 by 1000 viewport, signed in as `engineer`, against the demo scenario plus one open investigation. The per-item intended content and status are in [../media-plan.md](../media-plan.md).

| File | Screen | What it shows |
|------|--------|---------------|
| `01-login.png` | Login | Login form with the username `engineer` filled and the password empty |
| `02-overview-dashboard.png` | Overview | Machine cards, KPI tiles, recent alerts, and the investigations panel |
| `03-machines-events.png` | Machine Monitoring | CNC-03 selected, with its status, counts, event timeline, and change status form |
| `04-orders-and-batches.png` | Production Orders | The nine `SIM0001-*` orders with their progress and actions |
| `05-quality-inspections.png` | Quality Inspection | Defect rate by machine and the inspections table filtered to failures |
| `06-investigation-case-board.png` | Investigation detail | Findings, evidence cards R1 and R2 with the SQL shown, and flagged batches |
| `07-traceability-and-quarantine.png` | Traceability | Forward trace of lot `L203`, backward trace of a serial number, and the empty quarantine form |
| `08-analytics-charts.png` | Analytics | Window controls and the four charts |
| `09-analytics-sql-explorer.png` | Analytics, SQL Explorer | `batches_requiring_review` with its inputs and four result rows |

## Capturing again

Prerequisites: `make reset-demo`, `make backend`, `make frontend`, and at least one investigation opened (through the Investigations screen or `POST /api/v1/investigations`). Then run:

```bash
cd backend && uv run --group docs python ../scripts/development/capture_screenshots.py
```

The script writes all nine files with a 1600 by 1000 viewport and overwrites the existing ones, so re-capturing replaces them.

Rules:

- Commit only genuine captures of the running application; do not edit or synthesise images.
- Keep each file under 1 MB, and never show a typed password.
- If a screen changes, re-capture and update the matching row in `docs/media/media-plan.md`.
