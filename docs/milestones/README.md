# Milestone documents

Graded milestone documents for CS3320 (Dr. Chibuzo Ukegbu). Markdown is the source; DOCX and PDF are generated from it by build_documents.py. Edit the Markdown, rebuild, and submit the PDF.

## Index

| Milestone | Source | Generated |
|---|---|---|
| Week 8 proposal and design defense | week08-proposal.md | week08-proposal.docx, week08-proposal.pdf |
| Week 8 milestone report | week08-milestone-report.md | week08-milestone-report.docx, week08-milestone-report.pdf |
| Week 9 environment and repository check | week09-milestone-report.md | week09-milestone-report.docx, week09-milestone-report.pdf |
| Week 10 database and query defense | week10-milestone-report.md | week10-milestone-report.docx, week10-milestone-report.pdf |
| Week 12 back end, rules, and security | week12-milestone-report.md (to be written) | |
| Week 13 front end and integration | week13-milestone-report.md (to be written) | |
| Week 14 testing and readiness | week14-milestone-report.md (to be written) | |

Every report follows the seven standard sections from the assignment (completion status and blockers; technical artifacts and commit or tag; decisions, alternatives, assumptions, constraints, and rationale; AI help and verification; lessons learned; support needed; next-step plan) followed by a personal reflection and a personal-work summary. Bracketed prompts such as "[Describe ...]" must be replaced with the student's own words before submission; the build script warns when brackets remain.

## Submission checklist (every milestone)

Before the lab defense begins:

1. Replace every bracketed prompt in the Markdown, including the commit hash, repository URL, and submission date.
2. Rebuild the DOCX and PDF (see below) and check the page count printed by the script. The assignment asks for a concise 2 to 3 page Week 8 proposal; with the embedded ERD and the reflection the generated PDF runs to four pages, so trim sections 8 and 11 if the instructor wants the shorter form.
3. Upload Week##_Milestone_Report.pdf (and for Week 8 the proposal PDF) to Canvas before the scheduled lab defense. A repository commit does not replace the Canvas submission.
4. Push the repository and record the commit hash or tag in the report. Confirm that the instructor can access the repository.
5. Open the Canvas artifact and the repository during the defense; be ready to explain what, why, assumptions, AI contributions, and verification evidence.

Milestone-specific items:

| Milestone | Also required |
|---|---|
| Week 8 | Proposal PDF with draft ERD and starting-point reflection (250 to 400 words) |
| Week 9 | README setup draft, project structure, MySQL connection evidence, schema or migration draft, seed plan |
| Week 10 | Revised ERD, normalization rationale, schema and migrations, seed data, constraints and indexes, query drafts with results, initial CRUD evidence |
| Week 12 | Running API, data-access evidence, business rules, validation and security, data-flow diagram, tests |
| Week 13 | Usable interface, API contract, integration and test evidence |
| Week 14 | Release candidate, completed test matrix, defect and fix evidence, final ERD and schema, tested README, demo data, report draft, AI evidence package |

## Regenerating DOCX and PDF

Requirements: Python 3 with python-docx, pypdf, reportlab, and Pillow (pip install python-docx pypdf reportlab pillow). LibreOffice (soffice on PATH) is optional; when a working installation is found the PDF is converted from the DOCX, otherwise the PDF is rendered directly from the parsed Markdown with reportlab.

```
cd docs/milestones
python3 build_documents.py            # builds every *.md except README.md
python3 build_documents.py week08-proposal.md
python3 build_documents.py --no-pdf   # DOCX only
```

The script converts each Markdown file to DOCX with python-docx, writes the PDF, and prints the method used, the PDF page count, and the number of bracketed prompts that still need to be replaced. Generated files are overwritten on every run.

Mermaid diagrams (the draft ERD in the Week 8 proposal) are embedded as figures when a rendered PNG exists in `figures/` (named `<document>-<n>.png`, where n counts the Mermaid blocks in the file). Render them first with `make render-figures`, which runs `scripts/development/render_milestone_figures.py` through Playwright and an installed Chrome, the same way as `make render-diagrams`. Without a rendered figure the DOCX and PDF carry a note pointing to the Mermaid source in the Markdown file and to docs/database/database-design.md.
