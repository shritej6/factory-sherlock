# AI evidence

This directory is the responsible AI use record required by the CS3320 project
brief. It documents how AI assistance was used, what was accepted, revised, or
rejected, and how each outcome was verified. Nothing here is a transcript
export; each entry is an annotated record that the student can explain and
defend.

## Tools used

| Tool | Provider | Use |
|------|----------|-----|
| Claude Code (Claude Fable 5.1) | Anthropic | Repository scaffolding, schema design proposals, backend and query implementation, documentation drafting, test generation, review passes |
| Codex CLI, Gemini CLI | OpenAI, Google | Planned as secondary review tools; not yet used on this project |

No passwords, keys, connection strings, or personal data were shared with any
AI tool. Secrets are placeholders in `.env.example` and real values live only in
the untracked `.env`.

## Verification approach

Every AI proposal was treated as a draft. Verification took one of these forms,
and each record names which one applied:

1. Executed against MySQL 8.4 (migrations, seed, queries, API smoke tests).
2. Covered by an automated test under `backend/tests`.
3. Compared with course concepts (normalization, keys, constraints, transactions).
4. Read line by line and rewritten where the intent was unclear.

## Contents

- `ai-use-record.md`: the running record (stage, tool, task, recommendation, component, decision, verification, responsible, lesson).
- `conversations/`: annotated conversation sequences. The brief requires three to five sequences covering at least three project areas with at least one accepted, one substantially revised, and one rejected suggestion.
- `reflection-notes.md`: notes the student keeps for the Week 8 starting point and the final reflection.

## Honesty rules for this directory

- Record only interactions that affected a decision or an implementation.
- Never paste secrets, even in redacted form.
- Mark the student annotation fields clearly; the AI does not write the student's reflection.
- If a record cannot be defended in a lab session, it is removed and the component is reworked until it can.
