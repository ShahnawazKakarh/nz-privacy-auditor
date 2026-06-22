"""Apply an LLM verification pass to an existing :class:`ScanResult`.

The verifier re-scores findings whose initial confidence is below a
configurable threshold. A ``confirmed`` verdict promotes confidence to at
least 0.95; a ``rejected`` verdict drops the finding entirely; ``uncertain``
leaves the original score in place.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from .detectors import Finding
from .scanner import CellFinding, ScanResult

if TYPE_CHECKING:
    from .verifiers.base import LLMVerifier


def apply_verification(
    result: ScanResult,
    verifier: LLMVerifier,
    threshold: float = 0.8,
    on_quota_exceeded: str = "stop",
) -> ScanResult:
    """Run a second-pass LLM verification over the findings.

    Args:
        result: a ScanResult produced by :class:`Scanner`.
        verifier: an :class:`LLMVerifier` implementation (typically
            :class:`GeminiVerifier`).
        threshold: only findings with ``confidence < threshold`` are
            verified. Defaults to 0.8.
        on_quota_exceeded: ``"stop"`` (default) returns the partially
            verified result; ``"raise"`` re-raises the QuotaExceededError.

    Returns:
        A new ScanResult with re-scored findings. Findings rejected by the
        LLM are dropped; confirmed findings have confidence promoted to
        ``max(original, 0.95)`` and gain ``verified: True`` plus the LLM's
        verdict / reason in their context.
    """
    # Imported here to avoid hard dependency on the [llm] extra.
    from .verifiers.base import Verdict
    from .verifiers.gemini import QuotaExceededError

    new_findings: list[CellFinding] = []
    quota_hit = False

    for cf in result.findings:
        if cf.finding.confidence >= threshold:
            new_findings.append(cf)
            continue
        if quota_hit:
            new_findings.append(cf)
            continue

        try:
            v = verifier.verify(
                detector=cf.finding.detector,
                value=cf.finding.value,
                context=cf.cell_value or cf.finding.value,
            )
        except QuotaExceededError:
            if on_quota_exceeded == "raise":
                raise
            quota_hit = True
            new_findings.append(cf)
            continue

        if v.verdict is Verdict.REJECTED:
            # Drop the finding entirely.
            continue

        new_confidence = cf.finding.confidence
        if v.verdict is Verdict.CONFIRMED:
            new_confidence = max(cf.finding.confidence, 0.95)

        verified_finding: Finding = replace(
            cf.finding,
            confidence=new_confidence,
            context={
                **cf.finding.context,
                "verified": True,
                "llm_verdict": v.verdict.value,
                "llm_confidence": v.confidence,
                "llm_reason": v.reason,
                "llm_cached": v.cached,
            },
        )
        new_findings.append(
            CellFinding(
                row=cf.row,
                column=cf.column,
                finding=verified_finding,
                cell_value=cf.cell_value,
            )
        )

    return ScanResult(
        rows_scanned=result.rows_scanned,
        columns_scanned=result.columns_scanned,
        detectors_used=result.detectors_used,
        findings=new_findings,
    )


__all__ = ["apply_verification"]
