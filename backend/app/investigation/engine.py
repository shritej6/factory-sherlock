"""Runs every rule in order and collects the evidence."""

from dataclasses import dataclass

from app.investigation.rules import RULES, Evidence, InvestigationContext
from app.investigation.summary import build_summary
from app.repositories.query_runner import QueryRunner


@dataclass(frozen=True)
class InvestigationReport:
    evidence: list[Evidence]
    summary: str
    affected_batch_ids: list[int]
    elevated: bool


def investigate(ctx: InvestigationContext, runner: QueryRunner) -> InvestigationReport:
    evidence = [card for rule in RULES if (card := rule(ctx, runner)) is not None]
    return InvestigationReport(
        evidence=evidence,
        summary=build_summary(ctx),
        affected_batch_ids=list(ctx.affected_batch_ids),
        elevated=ctx.elevated,
    )
