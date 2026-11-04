# Media plan

This plan lists the screenshots and videos that will document Factory Sherlock, what each must show, and how to produce it. Nine screenshots were captured on 2026-11-03 with `scripts/development/capture_screenshots.py` and are on disk in `docs/media/screenshots/`. No video file exists yet; the video items below are Pending.

Rules:

- Capture from the real application running against the demo scenario (`make reset-demo`, which resets the database and runs the demo seed) so that every image and video shows reproducible data.
- Do not commit large media. Screenshots are PNG at native resolution and should stay well under 1 MB each. Video files are not committed to the repository; they are hosted externally (course platform, shared drive, or an unlisted video host) and linked from `docs/media/videos/README.md`. If Git LFS is adopted later, that decision is recorded in `docs/decisions/`.
- Never include real credentials in a capture. Use the demo accounts and a throwaway `SEED_DEMO_PASSWORD`; crop or mask the password field when it is visible.
- File names are lower-case with hyphens and a two-digit sequence prefix so the order is stable.

## Screenshots

Location: `docs/media/screenshots/`. Format: PNG, 1600 x 1000 pixels (the viewport used by the capture script), page content only without browser chrome, light colour scheme. The nine files total about 1.2 MB, each under 300 KB.

The captures used the demo scenario (`make reset-demo`) plus one investigation opened through `POST /api/v1/investigations` (title "CNC-03 defect rate climb on 2026-11-02", machine CNC-03, window 2026-11-02 06:00 to 12:00), signed in as `engineer`. The Intended content column describes what each file shows.

| # | File name | Intended content | Required state | Status |
|---|-----------|------------------|----------------|--------|
| 1 | `01-login.png` | Login form with the username field filled with `engineer`, the password field empty (the capture is taken before the password is typed), and no error shown. | Backend and frontend running, not yet signed in. | Captured 2026-11-03 (`scripts/development/capture_screenshots.py`); commit hash to be recorded after the first push |
| 2 | `02-overview-dashboard.png` | Overview dashboard: three machine cards (CNC-01 IDLE, CNC-02 IDLE, CNC-03 WARNING); KPI tiles (700 units, 1,400 inspections, 1,349 passed, 51 failed, 3.6 percent defect rate, 1 active order); recent alerts (WARNING High Defect Rate for batch 10 on CNC-03 at 25 percent failed inspections, CRITICAL Machine Fault for CNC-02 entering FAULT during simulated downtime) with Acknowledge buttons; and the investigations panel listing the open case. | Demo scenario loaded; one investigation open; signed in as engineer. | Captured 2026-11-03 (`scripts/development/capture_screenshots.py`); commit hash to be recorded after the first push |
| 3 | `03-machines-events.png` | Machine Monitoring with CNC-03 selected: status WARNING, 480 inspected, 46 failed, 9.6 percent; the event timeline with the Tool Wear WARNING event at 2026-11-02 08:00, the Running to Warning state change at 08:00, and Idle to Running at 06:00; and the change status form. | Demo scenario loaded. | Captured 2026-11-03 (`scripts/development/capture_screenshots.py`); commit hash to be recorded after the first push |
| 4 | `04-orders-and-batches.png` | Production Orders list with the nine `SIM0001-*` orders: eight COMPLETED (80/80) and `SIM0001-CNC-02-02` IN PROGRESS (60/80) with Complete and Cancel actions. Batches are not expanded on this screen; the batch list is a separate screen. | Demo scenario loaded. | Captured 2026-11-03 (`scripts/development/capture_screenshots.py`); commit hash to be recorded after the first push |
| 5 | `05-quality-inspections.png` | Quality Inspection screen with the defect-rate-by-machine chart and the inspections table filtered to Result = Fail, showing `OVERSIZE_DIAMETER` defect codes on CNC-03 units. | Demo scenario loaded. | Captured 2026-11-03 (`scripts/development/capture_screenshots.py`); commit hash to be recorded after the first push |
| 6 | `06-investigation-case-board.png` | Investigation detail: OPEN badge, scope CNC-03, window 2026-11-02 06:00 to 12:00, the findings paragraph, evidence card R1 (machine defect-rate comparison, 3 rows) with "Hide the SQL" expanded to show the query text, evidence card R2 (dominant defect category), and the flagged batches panel listing `SIM0001-CNC-03-03-B01` to `B04` with Review and quarantine links. | Investigation opened through `POST /api/v1/investigations`. | Captured 2026-11-03 (`scripts/development/capture_screenshots.py`); commit hash to be recorded after the first push |
| 7 | `07-traceability-and-quarantine.png` | Traceability screen: forward trace of lot `L203` (six CNC-03 batches), backward trace of serial `SIM0001-CNC-03-03-B04-U0001`, and the quarantine form, empty. No batch was quarantined in this capture. | Demo scenario loaded. | Captured 2026-11-03 (`scripts/development/capture_screenshots.py`); commit hash to be recorded after the first push |
| 8 | `08-analytics-charts.png` | Top of the Analytics page: window controls, daily production trend, defect rate by machine with the fleet-rate dashed line, pass and fail distribution, and defect categories. | Demo scenario loaded. | Captured 2026-11-03 (`scripts/development/capture_screenshots.py`); commit hash to be recorded after the first push |
| 9 | `09-analytics-sql-explorer.png` | Analytics page scrolled to the SQL Explorer with `batches_requiring_review` selected: its description, the window, machine, and threshold inputs, the Run query button, and the four result rows. | Demo scenario loaded. | Captured 2026-11-03 (`scripts/development/capture_screenshots.py`); commit hash to be recorded after the first push |

Capture method: run the script from `backend/` with the `docs` dependency group.

```bash
cd backend && uv run --group docs python ../scripts/development/capture_screenshots.py
```

It needs the demo scenario loaded (`make reset-demo`), the backend (`make backend`) and the frontend (`make frontend`) running, and at least one investigation. It signs in as `engineer` with `SEED_DEMO_PASSWORD` from `.env` and overwrites the nine files. Manual capture remains acceptable for screens the script does not cover; save the file under `docs/media/screenshots/` using the naming rule above and add a row to the table.

## Videos

Location: `docs/media/videos/` holds only `README.md` and, later, links. Video files are not committed. Target format: MP4 (H.264), 1920 x 1080, 30 fps, with narration recorded live or added afterwards. Keep the cursor visible and move it slowly; zoom the browser to 110 to 125 percent so table text stays legible.

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

### Video 3: Quality inspection demonstration

- Proposed file name: `03-quality-inspection-demonstration.mp4`
- Purpose: show measurement evaluation, defect classification, quality summaries, and alerts.
- Audience: instructor; quality engineering viewers.
- Duration: 4 to 6 minutes.
- Demonstration sequence: (1) open the quality screen filtered to an early CNC-03 batch (all PASS) and then to a late one (OVERSIZE_DIAMETER failures); (2) show the quality summary for CNC-03 and for the fleet; (3) record a manual inspection on a unit of a manually created order: first a passing value, then a failing value, showing the server-computed result and defect code; (4) attempt to record an inspection with a specification from another product and show the 422 message; (5) show the alerts list with the `HIGH_DEFECT_RATE` alert and acknowledge it.
- Required application state: demo scenario loaded plus one manually created and released order with a started batch (prepared before recording); logged in as `operator` for inspection entry and `engineer` for the rest, or `admin` throughout.
- Technical concepts: `abs(measured - target) <= tolerance`, classification by characteristic, one inspection per unit and specification, defect rate definition, alert threshold 0.15.
- Recording instructions: keep the API response visible when the error is shown (network panel or the UI's error message).

### Video 4: Defect investigation demonstration

- Proposed file name: `04-defect-investigation-demonstration.mp4`
- Purpose: walk through an investigation from opening to closing and explain the evidence cards.
- Audience: instructor; reviewers interested in the SQL and the reasoning discipline.
- Duration: 6 to 8 minutes.
- Demonstration sequence: (1) from the dashboard, note CNC-03's defect rate; (2) open an investigation for CNC-03 over 2026-11-02 06:00 to 12:00; (3) read the generated summary aloud and point out the non-causal wording; (4) expand R1 (fleet comparison), R3 (onset hour), R4 (TOOL_WEAR event before onset), R5 (batches above 10 percent), R6 (shared lots) showing the SQL and the rows for at least two cards; (5) explain why R6's shared lots are a decoy in this scenario; (6) move the investigation to IN_REVIEW, quarantine the worst batch from the traceability or batches screen, return and close the investigation with a written conclusion; (7) show that CLOSED is terminal.
- Required application state: demo scenario loaded; no prior investigation; logged in as `engineer`.
- Technical concepts: rules R1 to R6 (`docs/investigation/investigation-engine.md`), evidence cards storing SQL and rows, window functions and LAG in `defect_onset.sql`, investigation state machine.
- Recording instructions: zoom the browser so the SQL text is readable; pause briefly on each expanded card.

### Video 5: Material traceability demonstration

- Proposed file name: `05-material-traceability-demonstration.mp4`
- Purpose: show forward and backward traceability and the transactional lot quarantine cascade.
- Audience: instructor; reviewers interested in the many-to-many design.
- Duration: 4 to 6 minutes.
- Demonstration sequence: (1) forward trace of lot `L203` and reading the batches, machines, orders, and failed unit counts; (2) backward trace of a serial number from a late CNC-03 batch, showing lineage and the inspection summary; (3) quarantine lot `L202` with a reason and show the response listing every batch that was quarantined; (4) show those batches now `QUARANTINED` in the batches screen and the `MATERIAL_QUARANTINE` alert; (5) attempt to start a new batch using `L202` and show the rejection; (6) in the SQL explorer or `database/queries/`, show `04_material_lot_forward_trace.sql` and point at the `batch_materials` join.
- Required application state: demo scenario loaded; one released manual order for `STEEL-SHAFT` on a machine, for step 5; logged in as `engineer`.
- Technical concepts: junction table `batch_materials`, eight-table join, `GROUP_CONCAT`, one transaction for the cascade, RESTRICT and CASCADE foreign keys.
- Recording instructions: show the quarantine response body in full before switching screens.

### Video 6: Complete system walkthrough

- Proposed file name: `06-complete-system-walkthrough.mp4`
- Purpose: a single end-to-end story for someone who watches only one video.
- Audience: instructor; final grading.
- Duration: 10 to 12 minutes.
- Demonstration sequence: (1) setup in one minute: `local_mysql.sh start`, `alembic upgrade head`, seed with demo, start backend and frontend; (2) log in; (3) create a production order, release it, start a batch with two lots, record two inspections, complete the batch; (4) run a simulation with a fault; (5) show the dashboard reacting (alerts, defect rate chart); (6) open and close an investigation; (7) quarantine a batch and a lot; (8) show the SQL explorer with one dashboard query and its rows; (9) show `uv run pytest` output and the test matrix; (10) closing remarks on limitations and planned work.
- Required application state: fresh reset before recording; terminal and browser ready; logged in as `admin` to avoid role switching.
- Technical concepts: everything above at summary depth, plus the role model, error contract, and test isolation.
- Recording instructions: record in segments (setup, manufacturing, simulation, investigation, traceability, tests) and join them; keep each cut on a static screen.

## Status tracking

| Item | Status |
|------|--------|
| Screenshots 1 to 9 | Captured 2026-11-03 with `scripts/development/capture_screenshots.py`; commit hash to be recorded after the first push |
| Videos 1 to 6 | Pending recording; no files exist |
| Diagram sources (`docs/media/diagrams/*.mmd`) | Present: `manufacturing-workflow.mmd`, `simulation-event-flow.mmd`, `investigation-workflow.mmd`, `traceability-relationships.mmd` (this set); `system-architecture.mmd`, `backend-components.mmd`, `local-deployment.mmd`, and `er-diagram.mmd` are owned by the architecture and database documentation. `make render-diagrams` writes one `<name>.svg` per source |

Update this table and the per-item Status columns when a file is added.
