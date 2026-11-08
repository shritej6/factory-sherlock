# Media plan

This plan lists the screenshots and videos that will document Factory Sherlock, what each must show, and how to produce it. Fourteen screenshots were captured on 2026-11-08 with `scripts/development/capture_screenshots.py` and are on disk in `docs/media/screenshots/`. Five silent walkthrough clips (videos 2 to 6) were recorded on 2026-11-08 with `scripts/development/record_walkthroughs.py` and are in `docs/media/videos/`; video 1 (project overview) and the narrated versions are Pending.

Rules:

- Capture from the real application running against the demo scenario (`make reset-demo`, which resets the database and runs the demo seed) so that every image and video shows reproducible data.
- Do not commit large media. Screenshots are PNG at native resolution and should stay well under 1 MB each. Silent walkthrough clips produced by `scripts/development/record_walkthroughs.py` are committed when each file is under 10 MB and the committed set stays under 40 MB ([ADR-0010](../decisions/ADR-0010-commit-short-walkthrough-videos.md)). Narrated recordings and any larger file are hosted externally (course platform, shared drive, or an unlisted video host) and linked from `docs/media/videos/README.md`.
- Never include real credentials in a capture. Use the demo accounts and a throwaway `SEED_DEMO_PASSWORD`; crop or mask the password field when it is visible.
- File names are lower-case with hyphens and a two-digit sequence prefix so the order is stable.

## Screenshots

Location: `docs/media/screenshots/`. Format: PNG, 1600 x 1000 pixels (the viewport used by the capture script), page content only without browser chrome, dark colour scheme (the black industrial control panel of 2026-11-08: a status band across the top with the product name, the live machine states, a clock, the signed-in account and role, and Sign out; the soft-key row along the bottom as the primary navigation with the current screen's key lit in amber). Captures 2 to 13 show both; in 9, 10 and 11 the page is scrolled so the status band is above the viewport and only the soft-key row remains. The fourteen files total 1.36 MB (1,364,926 bytes), each under 200 KB (the largest is `06-investigation-case-board.png` at 194 KB).

The captures used the demo scenario (`make reset-demo`) plus four preparation steps through the API: one investigation opened through `POST /api/v1/investigations` (title "CNC-03 defect rate climb on 2026-11-02", machine CNC-03, window 2026-11-02 06:00 to 12:00) as `engineer`; one overdue check through `POST /api/v1/analytics/alerts/checks/overdue-orders` as `operator`, which raised the `ORDER_OVERDUE` alert for `SIM0001-CNC-02-02`; and batch `SIM0001-CNC-02-02-B04` started through `POST /api/v1/production-batches` (order `SIM0001-CNC-02-02`, 20 units, lot `L302`) so that `database/seeds/sample_inspection_import.csv` imports cleanly, as `docs/quality/inspection-import.md` describes. The CSV itself was imported by the capture script through the Quality screen (capture 10). Captures 1 to 13 are signed in as `engineer`; capture 14 uses `viewer`. The Intended content column describes what each file shows.

| # | File name | Intended content | Required state | Status |
|---|-----------|------------------|----------------|--------|
| 1 | `01-login.png` | Login form with the username field filled with `engineer`, the password field empty (the capture is taken before the password is typed), the Sign in button disabled, and no error shown. | Backend and frontend running, not yet signed in. | Captured 2026-11-08 (`scripts/development/capture_screenshots.py`) |
| 2 | `02-overview-dashboard.png` | Overview dashboard: three machine cards (CNC-01 IDLE, CNC-02 IDLE, CNC-03 WARNING); KPI tiles (720 units, 1,400 inspections, 1,349 passed, 51 failed, 3.6 percent defect rate, 1 active order; the 720 includes the 20 units of batch `SIM0001-CNC-02-02-B04`, started in preparation); the Recent alerts panel with the Check overdue orders button, three alerts (CRITICAL Order Overdue for `SIM0001-CNC-02-02`, 6 days overdue on the capture date, with a View orders link; WARNING High Defect Rate for batch 10 on CNC-03 at 25 percent; CRITICAL Machine Fault for CNC-02), Acknowledge buttons, and the alert pagination (Showing 1 to 3 of 3, Rows per page 10); and the Investigations panel with 1 open case and its title. The status band reads CNC-01 IDLE, CNC-02 IDLE, CNC-03 WARNING. | Demo scenario loaded; preparation steps done; signed in as engineer. | Captured 2026-11-08 (`scripts/development/capture_screenshots.py`) |
| 3 | `03-machines-events.png` | Machine Monitoring with CNC-03 selected: status Warning, 480 inspected, 46 failed, 9.6 percent; the event timeline with the Tool Wear WARNING event at 2026-11-02 08:00, the Running to Warning state change at 08:00, and Idle to Running at 06:00, with its own pagination (Showing 1 to 3 of 3); and the change status form (New status, Reason, Apply status). | Demo scenario loaded. | Captured 2026-11-08 (`scripts/development/capture_screenshots.py`) |
| 4 | `04-orders-and-batches.png` | Production Orders list with the nine `SIM0001-*` orders: eight COMPLETED (80/80, marked Terminal state) and `SIM0001-CNC-02-02` IN PROGRESS (60/80) with Complete and Cancel actions; the Status filter on All statuses; due dates 2026-11-02; Showing 1 to 9 of 9. Batches are a separate screen (capture 12). | Demo scenario loaded. | Captured 2026-11-08 (`scripts/development/capture_screenshots.py`) |
| 5 | `05-quality-inspections.png` | Quality Inspection screen with the Record inspection and Import inspections from CSV buttons, the defect-rate-by-machine chart (fleet rate 3.6 percent), and the inspections table filtered to Result = Fail, showing `OVERSIZE_DIAMETER` defect codes on CNC-03 units (specification 5, inspected 2026-11-02 11:46 to 12:00). | Demo scenario loaded. | Captured 2026-11-08 (`scripts/development/capture_screenshots.py`) |
| 6 | `06-investigation-case-board.png` | Investigation detail: OPEN badge, Case 1, scope CNC-03, window 2026-11-02 06:00 to 12:00, the findings paragraph (including the CUSUM onset sentence), the Evidence (7 rules) heading, evidence card R1 (machine defect-rate comparison, 3 rows) with "Hide the SQL" expanded to show the query name and text; the Case status panel with Mark in review and Close with conclusion; and the Flagged batches panel listing `SIM0001-CNC-03-03-B01` to `B04` with their defect rates (10.0, 25.0, 30.0, 47.5 percent), COMPLETED badges, and Review and quarantine links. R2 and later cards are below the fold. | Investigation opened through `POST /api/v1/investigations`. | Captured 2026-11-08 (`scripts/development/capture_screenshots.py`) |
| 7 | `07-traceability-and-quarantine.png` | Traceability screen: forward trace of lot `L203` (six CNC-03 batches with all nine columns, batch to failed units, visible at this width), backward trace of serial `SIM0001-CNC-03-03-B04-U0001` (produced 2026-11-02 11:31, inspection summary `diameter=20.164 FAIL; length=150.194 PASS`, lots `L201` and `L203` AVAILABLE), and the quarantine form, empty. No lot was quarantined in this capture. | Demo scenario loaded. | Captured 2026-11-08 (`scripts/development/capture_screenshots.py`) |
| 8 | `08-analytics-charts.png` | Top of the Analytics page: window controls (2026-11-01 to 2026-11-05), daily production trend (one day, three machines), defect rate by machine with the fleet-rate dashed line, pass and fail distribution, and defect categories (`OVERSIZE_DIAMETER`, `HOLE_POSITION_DEVIATION`, `DIMENSIONAL_DEVIATION`). The orders-by-status chart, the control chart, and the SQL Explorer are below the fold. | Demo scenario loaded. | Captured 2026-11-08 (`scripts/development/capture_screenshots.py`) |
| 9 | `09-analytics-sql-explorer.png` | Analytics page scrolled to the SQL Explorer with `batches_requiring_review` selected: its description, the window, machine, and threshold inputs, the Run query button, and the four result rows (`SIM0001-CNC-03-03-B04` to `B01`, 47.5 to 10.0 percent). The end of the control chart panel is visible above it. | Demo scenario loaded. | Captured 2026-11-08 (`scripts/development/capture_screenshots.py`) |
| 10 | `10-quality-csv-import.png` | Quality page scrolled to the open Import inspections from CSV form: the expected columns, the CSV file input, the success notice "Imported 16 inspections, 3 failed the specification.", and the Import button; below it the defect-rate chart (fleet rate 3.8 percent) and the first rows of the table, now starting with the imported inspections on units 708 and 707. The form clears the file input after a successful import, so no file name is shown. A second run of the script shows the file name and the per-row "already has an inspection" errors instead. | Batch `SIM0001-CNC-02-02-B04` started; the sample file not yet imported. | Captured 2026-11-08 (`scripts/development/capture_screenshots.py`) |
| 11 | `11-analytics-control-chart.png` | Analytics control chart panel with specification METAL-BRACKET hole_position (mm) and machine CNC-02 selected: the X-bar chart of 12 subgroups (batches `01-B01` to `03-B04` and `02-B04`), grand mean, per-subgroup control limits, specification limits at 49.800 and 50.200, and the sentence "All 12 subgroups fall inside the control limits." The last subgroup, `SIM0001-CNC-02-02-B04`, has 7 inspections inside the window instead of 20, so its limits are wider and the limit lines step at the right end. | Sample CSV imported (capture 10). | Captured 2026-11-08 (`scripts/development/capture_screenshots.py`) |
| 12 | `12-batches-status-filter.png` | Production Batches filtered to Status = Completed, on the second page: Showing 26 to 35 of 35, Rows per page 25, Previous enabled and Next disabled, ten rows with batch, order, machine, status, units, started, completed, material lots, quarantine reason, and actions columns (a Quarantine key per row), and the Start batch button. | Demo scenario loaded. | Captured 2026-11-08 (`scripts/development/capture_screenshots.py`) |
| 13 | `13-overview-overdue-check.png` | Overview after clicking Check overdue orders as engineer: the notice "Checked 1 open order, no new overdue alerts" above the alert list (the `ORDER_OVERDUE` alert had been raised by the preparation check, and the check raises one alert per order). KPI tiles read 720 units, 1,416 inspections, 1,362 passed, 54 failed, 3.8 percent after the CSV import. | Preparation steps done; CSV imported. | Captured 2026-11-08 (`scripts/development/capture_screenshots.py`) |
| 14 | `14-login-throttled.png` | Login page after five wrong passwords for `viewer` from the browser: username `viewer`, the masked wrong password, and the notice "Too many attempts. Try again in 898 seconds." with the request id. The login throttle allows 5 failures per account in 15 minutes (`login_max_failures`, `login_window_seconds` in `backend/app/core/config.py`). | Backend running; taken last, because `viewer` is unusable for 15 minutes afterwards. | Captured 2026-11-08 (`scripts/development/capture_screenshots.py`) |

Capture method: run the script from `backend/` with the `docs` dependency group.

```bash
cd backend && FRONTEND_URL=http://localhost:5173 uv run --group docs python ../scripts/development/capture_screenshots.py
```

`make screenshots` runs the same command. It needs the demo scenario loaded (`make reset-demo`), the four preparation steps above, the backend (`make backend`) and the frontend (`make frontend`, or another port given in `FRONTEND_URL`) running. It signs in as `engineer` with `SEED_DEMO_PASSWORD` from `.env` and overwrites the fourteen files; the last capture throttles the `viewer` account for 15 minutes. Manual capture remains acceptable for screens the script does not cover; save the file under `docs/media/screenshots/` using the naming rule above and add a row to the table.

## Videos

Location: `docs/media/videos/` holds `README.md`, the silent walkthrough clips recorded by `scripts/development/record_walkthroughs.py` (`make videos`; MP4, H.264, 1280 x 800, 25 fps, no audio, each under 10 MB), and links to the narrated recordings once they exist. The clips follow the demonstration sequences below as far as the browser alone can show them; each item notes what the clip covers and what is left to the narrated recording. Target format for the narrated recordings: MP4 (H.264), 1920 x 1080, 30 fps, with narration recorded live or added afterwards. Keep the cursor visible and move it slowly; zoom the browser to 110 to 125 percent so table text stays legible.

Recording tools (free):

- macOS: Shift+Command+5 opens the built-in screen recorder (QuickTime engine); choose "Record Selected Portion", enable the microphone in Options for narration, and stop from the menu bar. The result is a `.mov` that can be exported to MP4 from QuickTime Player (File, Export As, 1080p).
- Cross-platform: OBS Studio (https://obsproject.com) with a Display Capture or Window Capture source, output set to MP4 at 1080p30, and an audio input capture for the microphone.
- Trimming: QuickTime Player (Edit, Trim) or any free editor such as Shotcut or DaVinci Resolve.

Before each recording: reset the database with the demo scenario, start the backend and the frontend, log in as the account named below, close unrelated windows and notifications, and open the first screen of the sequence.

### Video 1: Project overview

- Proposed file name: `01-project-overview.mp4`
- Purpose: explain what Factory Sherlock is, the problem it addresses, and how the six modules fit together.
- Audience: course instructor and reviewers who have not seen the repository.
- Duration: 4 to 6 minutes.
- Demonstration sequence: (1) title slide or the repository README; (2) `docs/architecture/system-overview.md` architecture diagram; (3) the overview dashboard in the browser; (4) a short pass through the navigation (machines, orders, quality, investigations, traceability, simulation, analytics) without deep interaction; (5) the API documentation at `/api/docs` to show the endpoint groups; (6) closing summary of what the next videos show.
- Required application state: demo scenario loaded; logged in as `engineer`.
- Technical concepts to mention: MySQL as system of record, FastAPI modular monolith, deterministic simulation, rule-based investigation with evidence cards, batch to lot traceability.
- Recording instructions: screen recording of the browser and the editor; narration over slides for the first minute.

### Video 2: Virtual factory demonstration

- Proposed file name: `02-virtual-factory-demonstration.mp4`
- Purpose: show how production history is generated, how faults are injected, and that runs are deterministic.
- Audience: instructor; anyone evaluating the simulation design.
- Duration: 5 to 7 minutes.
- Demonstration sequence: (1) show `database/seeds/demo_scenario.json`; (2) reset the database and run `uv run python -m app.seed --demo` in a terminal, showing the JSON log line with the result counts; (3) in the simulation screen, submit a new run with a different seed and a `CALIBRATION_DRIFT` fault on CNC-01, show the `SimulationResult`; (4) open the machines screen to show CNC-01 now in `WARNING` and the event; (5) open the orders and batches screen to show the generated orders and the batch timing (30 minute batches, units 1.5 minutes apart); (6) run the same request twice on a reset database and compare a unit's measured values through the backward trace or inspections list to show determinism.
- Required application state: ability to reset the database between steps; terminal with `backend/` as working directory.
- Technical concepts: seeded random generator, fault models (`docs/simulation/fault-models.md`), shared clock, machine state machine, single-transaction persistence.
- Recording instructions: split the screen between terminal and browser, or switch windows with a short pause so the cut is clean.
- Silent clip: `02-virtual-factory-demonstration.mp4`, 2:10 (130 s), 1.5 MB, committed, recorded 2026-11-08: steps 3, 4 and 5 through the browser (a run with seed 7, start 2026-11-03 06:00, 6 batches per machine, `CALIBRATION_DRIFT` on CNC-01 from batch index 3; the result tiles; CNC-01 in WARNING with the Calibration Drift event; the generated orders, the CNC-01 batches, the failed inspections, and the Analytics charts). Steps 1, 2 and 6 (the JSON file, the terminal seed command, the repeated run) are left to the narrated recording.

### Video 3: Quality inspection demonstration

- Proposed file name: `03-quality-inspection-demonstration.mp4`
- Purpose: show measurement evaluation, defect classification, quality summaries, and alerts.
- Audience: instructor; quality engineering viewers.
- Duration: 4 to 6 minutes.
- Demonstration sequence: (1) open the quality screen filtered to an early CNC-03 batch (all PASS) and then to a late one (OVERSIZE_DIAMETER failures); (2) show the quality summary for CNC-03 and for the fleet; (3) record a manual inspection on a unit of a manually created order: first a passing value, then a failing value, showing the server-computed result and defect code; (4) attempt to record an inspection with a specification from another product and show the 422 message; (5) show the alerts list with the `HIGH_DEFECT_RATE` alert and acknowledge it.
- Required application state: demo scenario loaded plus one manually created and released order with a started batch (prepared before recording); logged in as `operator` for inspection entry and `engineer` for the rest, or `admin` throughout.
- Technical concepts: `abs(measured - target) <= tolerance`, classification by characteristic, one inspection per unit and specification, defect rate definition, alert threshold 0.15.
- Recording instructions: keep the API response visible when the error is shown (network panel or the UI's error message).
- Silent clip: `03-quality-inspection-demonstration.mp4`, 2:15 (135 s), 1.4 MB, committed, recorded 2026-11-08: steps 1, 3, 4 and 5 (the inspections of an early CNC-03 batch, the failures of `SIM0001-CNC-03-03-B04`, a passing and a failing manual inspection on units of `SIM0001-CNC-02-02-B04`, the 422 for a specification of another product, and the acknowledgement of the High Defect Rate alert). Step 2 (the quality summary) is visible in the Overview tiles at the end. Recorded as `engineer`; the manual inspections use the batch started in preparation instead of a separate manual order.

### Video 4: Defect investigation demonstration

- Proposed file name: `04-defect-investigation-demonstration.mp4`
- Purpose: walk through an investigation from opening to closing and explain the evidence cards.
- Audience: instructor; reviewers interested in the SQL and the reasoning discipline.
- Duration: 6 to 8 minutes.
- Demonstration sequence: (1) from the dashboard, note CNC-03's defect rate; (2) open an investigation for CNC-03 over 2026-11-02 06:00 to 12:00; (3) read the generated summary aloud and point out the non-causal wording; (4) expand R1 (fleet comparison), R3 (onset hour), R4 (TOOL_WEAR event before onset), R5 (batches above 10 percent), R6 (shared lots) showing the SQL and the rows for at least two cards; (5) explain why R6's shared lots are a decoy in this scenario; (6) move the investigation to IN_REVIEW, quarantine the worst batch from the traceability or batches screen, return and close the investigation with a written conclusion; (7) show that CLOSED is terminal.
- Required application state: demo scenario loaded; no prior investigation; logged in as `engineer`.
- Technical concepts: rules R1 to R6 (`docs/investigation/investigation-engine.md`), evidence cards storing SQL and rows, window functions and LAG in `defect_onset.sql`, investigation state machine.
- Recording instructions: zoom the browser so the SQL text is readable; pause briefly on each expanded card.
- Silent clip: `04-defect-investigation-demonstration.mp4`, 2:07 (127 s), 2.1 MB, committed, recorded 2026-11-08: all seven steps (a second case for CNC-03 over the same window, the SQL of R1, R3 and R4 expanded, R5 to R7 shown, Mark in review, the quarantine of `SIM0001-CNC-03-03-B04` from the flagged batches link, Close with conclusion, and the closed state). The decoy explanation for R6 is narration.

### Video 5: Material traceability demonstration

- Proposed file name: `05-material-traceability-demonstration.mp4`
- Purpose: show forward and backward traceability and the transactional lot quarantine cascade.
- Audience: instructor; reviewers interested in the many-to-many design.
- Duration: 4 to 6 minutes.
- Demonstration sequence: (1) forward trace of lot `L203` and reading the batches, machines, orders, and failed unit counts; (2) backward trace of a serial number from a late CNC-03 batch, showing lineage and the inspection summary; (3) quarantine lot `L202` with a reason and show the response listing every batch that was quarantined; (4) show those batches now `QUARANTINED` in the batches screen and the `MATERIAL_QUARANTINE` alert; (5) attempt to start a new batch using `L202` and show the rejection; (6) in the SQL explorer or `database/queries/`, show `04_material_lot_forward_trace.sql` and point at the `batch_materials` join.
- Required application state: demo scenario loaded; one released manual order for `STEEL-SHAFT` on a machine, for step 5; logged in as `engineer`.
- Technical concepts: junction table `batch_materials`, eight-table join, `GROUP_CONCAT`, one transaction for the cascade, RESTRICT and CASCADE foreign keys.
- Recording instructions: show the quarantine response body in full before switching screens.
- Silent clip: `05-material-traceability-demonstration.mp4`, 2:15 (135 s), 1.8 MB, committed, recorded 2026-11-08: steps 1 to 4 (forward trace of `L203`, backward trace of `SIM0001-CNC-03-03-B04-U0001`, quarantine of `L202` with the success notice naming the quarantined batches, the forward trace of `L202` showing them QUARANTINED, the Production Batches screen filtered to Quarantined, and the Material Quarantine alert on the Overview). Step 5 is not shown because the batch form only lists AVAILABLE lots, so `L202` cannot be chosen; step 6 (the SQL file) is narration.

### Video 6: Complete system walkthrough

- Proposed file name: `06-complete-system-walkthrough.mp4`
- Purpose: a single end-to-end story for someone who watches only one video.
- Audience: instructor; final grading.
- Duration: 10 to 12 minutes.
- Demonstration sequence: (1) setup in one minute: `local_mysql.sh start`, `alembic upgrade head`, seed with demo, start backend and frontend; (2) log in; (3) create a production order, release it, start a batch with two lots, record two inspections, complete the batch; (4) run a simulation with a fault; (5) show the dashboard reacting (alerts, defect rate chart); (6) open and close an investigation; (7) quarantine a batch and a lot; (8) show the SQL explorer with one dashboard query and its rows; (9) show `uv run pytest` output and the test matrix; (10) closing remarks on limitations and planned work.
- Required application state: fresh reset before recording; terminal and browser ready; logged in as `admin` to avoid role switching.
- Technical concepts: everything above at summary depth, plus the role model, error contract, and test isolation.
- Recording instructions: record in segments (setup, manufacturing, simulation, investigation, traceability, tests) and join them; keep each cut on a static screen.
- Silent clip: `06-complete-system-walkthrough.mp4`, 4:35 (275 s), 3.4 MB, committed, recorded 2026-11-08 as `admin`: steps 2 to 8 (order `WALK-1001` created and released, batch `WALK-1001-B01` started with lots `L201` and `L203`, a passing and a failing inspection, the batch completed, a simulation with `TOOL_WEAR` on CNC-02 from 2026-11-04, the Overview reacting, an investigation for CNC-02 opened with six evidence cards (R6 is not produced for that window), the SQL of R4 expanded, the case closed with a conclusion, lot `L402` quarantined with its batches, the control chart for STEEL-SHAFT diameter on CNC-03, and `batches_requiring_review` in the SQL explorer). Steps 1, 9 and 10 (setup commands, `uv run pytest`, closing remarks) are terminal or narration work.

## Status tracking

| Item | Status |
|------|--------|
| Screenshots 1 to 14 | Captured 2026-11-08 with `scripts/development/capture_screenshots.py` (`make screenshots`); fourteen PNG files, 1.36 MB in total, in `docs/media/screenshots/` |
| Video 1 | Pending recording; needs slides and narration |
| Videos 2 to 6, silent clips | Recorded 2026-11-08 with `scripts/development/record_walkthroughs.py`; five MP4 files totalling 10.2 MB in `docs/media/videos/`, narration pending |
| Videos 2 to 6, narrated | Pending recording; to be hosted externally and linked from `docs/media/videos/README.md` |
| Diagram sources (`docs/media/diagrams/*.mmd`) | Present: `manufacturing-workflow.mmd`, `simulation-event-flow.mmd`, `investigation-workflow.mmd`, `traceability-relationships.mmd` (this set); `system-architecture.mmd`, `backend-components.mmd`, `local-deployment.mmd`, and `er-diagram.mmd` are owned by the architecture and database documentation. `make render-diagrams` writes one `<name>.svg` per source |

Update this table and the per-item Status columns when a file is added.
