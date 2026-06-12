"""MOCK improve-and-gate walkthrough — synthetic numbers, public schemas only.

The real improvement and gate engines are private; this mock only shows the
shape of the loop: baseline scores → candidate scores → clean-delta check.
"""
from __future__ import annotations

from verifiable_labs_envs.schemas import ScoreSet

BASELINE = ScoreSet(
    public_score=0.78, hidden_score=0.70, ood_score=0.66, adversarial_score=0.60,
    dcr=0.04, hack_risk=0.02, calibration=0.90,
)
CANDIDATE = ScoreSet(
    public_score=0.82, hidden_score=0.76, ood_score=0.70, adversarial_score=0.63,
    dcr=0.04, hack_risk=0.02, calibration=0.91,
)


def main() -> int:
    # clean_score = raw * (1 - dcr) — the public formal-spec definition.
    base_clean = BASELINE.hidden_score * (1 - BASELINE.dcr)
    cand_clean = CANDIDATE.hidden_score * (1 - CANDIDATE.dcr)
    improved = cand_clean > base_clean
    regressed = (
        CANDIDATE.dcr > BASELINE.dcr
        or CANDIDATE.hack_risk > BASELINE.hack_risk
        or CANDIDATE.ood_score < BASELINE.ood_score
    )
    decision = "ACCEPT" if improved and not regressed else "REJECT"
    print(f"baseline clean hidden: {base_clean:.4f}")
    print(f"candidate clean hidden: {cand_clean:.4f}")
    print(f"MOCK gate decision: {decision}")
    print("IMPROVE-AND-GATE MOCK OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
