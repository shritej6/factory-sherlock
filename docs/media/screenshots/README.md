# Screenshots

Fourteen screenshots of the running application, captured on 2026-11-07 at a 1600 by 1000 viewport, light colour scheme, against the demo scenario plus the preparation steps listed in [../media-plan.md](../media-plan.md) (one open investigation, one overdue check, batch `SIM0001-CNC-02-02-B04` started, the sample CSV imported). Captures 1 to 13 are signed in as `engineer`; capture 14 uses `viewer`. The per-item intended content and status are in the media plan.

| File | Screen | What it shows |
|------|--------|---------------|
| `01-login.png` | Login | Login form with the username `engineer` filled, the password empty, and the Sign in button disabled |
| `02-overview-dashboard.png` | Overview | Machine cards, KPI tiles, the Check overdue orders button, three alerts (order overdue, high defect rate, machine fault), and the investigations panel |
| `03-machines-events.png` | Machine Monitoring | CNC-03 selected, with its status, counts, event timeline, and change status form |
| `04-orders-and-batches.png` | Production Orders | The nine `SIM0001-*` orders with their progress and actions |
| `05-quality-inspections.png` | Quality Inspection | Defect rate by machine and the inspections table filtered to failures |
| `06-investigation-case-board.png` | Investigation detail | Findings, evidence card R1 with the SQL shown, case status actions, and flagged batches |
| `07-traceability-and-quarantine.png` | Material Traceability | Forward trace of lot `L203`, backward trace of a serial number, and the empty quarantine form |
| `08-analytics-charts.png` | Analytics | Window controls and the first four charts |
| `09-analytics-sql-explorer.png` | Analytics, SQL Explorer | `batches_requiring_review` with its inputs and four result rows |
| `10-quality-csv-import.png` | Quality Inspection, CSV import | The import form after a successful import of `database/seeds/sample_inspection_import.csv` (16 rows, 3 failures) |
| `11-analytics-control-chart.png` | Analytics, control chart | X-bar chart for METAL-BRACKET hole_position on CNC-02 with per-subgroup control limits |
| `12-batches-status-filter.png` | Production Batches | Status filter set to Completed, second page of results with the pagination controls |
| `13-overview-overdue-check.png` | Overview | The result notice after clicking Check overdue orders |
| `14-login-throttled.png` | Login | The 429 notice after five wrong passwords for `viewer` |

## Capturing again

Prerequisites: `make reset-demo`, the preparation steps from the media plan, `make backend`, and `make frontend`. Then run `make screenshots`, or:

```bash
cd backend && FRONTEND_URL=http://localhost:5173 uv run --group docs python ../scripts/development/capture_screenshots.py
```

The script writes all fourteen files with a 1600 by 1000 viewport and overwrites the existing ones, so re-capturing replaces them. Capture 10 imports the sample CSV through the screen; on a second run against the same database it shows the per-row duplicate errors instead of the success notice. Capture 14 is taken last and leaves the `viewer` account throttled for 15 minutes.

Rules:

- Commit only genuine captures of the running application; do not edit or synthesise images.
- Keep each file under 1 MB, and never show a typed password.
- If a screen changes, re-capture and update the matching row in `docs/media/media-plan.md`.
