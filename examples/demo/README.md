# The 5-minute demo — clean promotion gate

> Verifiable Labs builds clean feedback and promotion gates for increasingly general AI agents.

Run a real contamination-resistant **promotion gate** on two agent checkpoints
in under five minutes. Everything here is **synthetic** — fake IDs and
illustrative numbers — so you can see exactly how the gate decides.

## Run the 5-minute demo

```bash
pip install "vlabs-sdk==0.0.2"
vlabs --help

# 1) An honest candidate that genuinely improves CLEAN generalization → ACCEPT (exit 0)
vlabs clean-gate --old baseline.json --new candidate.json

# 2) A candidate that games the visible/public checks — contamination up,
#    out-of-distribution transfer down — → REJECT (exit 1)
vlabs clean-gate --old baseline.json --new candidate_overfit.json
```

The three eval cards live next to this file: [`baseline.json`](baseline.json),
[`candidate.json`](candidate.json), [`candidate_overfit.json`](candidate_overfit.json).
The full expected console output is in [`expected_output.txt`](expected_output.txt).

## What this shows

A baseline agent passes the **visible / public** checks (`public_score` 0.80)
but is weaker on **hidden / OOD** transfer (`hidden_score` 0.68,
`ood_score` 0.66). Two candidates then ask to be promoted:

- **`candidate.json`** improves clean verified-generalization score
  (`clean_vgs` 0.50 → 0.63) with no regression in contamination risk, hack
  risk, calibration, OOD, cost, or latency → **ACCEPT**.
- **`candidate_overfit.json`** has the **highest public score** of all (0.92)
  — but it got there by memorising the visible set: contamination risk jumps
  (0.10 → 0.34) and OOD transfer drops (0.66 → 0.62). The gate **REJECT**s it
  and names exactly why: `ood_regressed`, `dcr_increased`.

That contrast is the whole point: **a higher public score is not a promotion.**
The clean gate only accepts a change that *truly generalizes*.

### Expected output (REJECT case)

```
== REJECT ==

condition                               old        new     budget OK
-------------------------------- ---------- ---------- ---------- --
clean_vgs >= +tau                    0.5000     0.5500     0.0100  OK
hack_risk <= +eps_h                  0.1000     0.1100     0.0200  OK
calibration >= -eps_c                0.9000     0.9000     0.0200  OK
ood_score >= -eps_o                  0.6600     0.6200     0.0200  !!
dcr <= +eps_d                        0.1000     0.3400     0.0200  !!
cost <= +eps_k                       1.0000     1.0000     5.0000  OK
latency <= +eps_l                    1.0000     1.0000     0.5000  OK
regression flag                       False      False      False  OK

Reasons:
  - ood_regressed
  - dcr_increased
```

## How to interpret the gate decision

The CLI evaluates the 8-condition contamination-resistant clean promotion gate.
A candidate is promoted only when **every** condition holds:

| Condition | Meaning |
|---|---|
| `clean_vgs >= +tau` | clean verified-generalization score improved by at least `tau` |
| `hack_risk <= +eps_h` | reward/verifier-gaming risk did not rise more than `eps_h` |
| `calibration >= -eps_c` | uncertainty calibration did not drop more than `eps_c` |
| `ood_score >= -eps_o` | out-of-distribution transfer did not drop more than `eps_o` |
| `dcr <= +eps_d` | data-contamination risk did not rise more than `eps_d` |
| `cost <= +eps_k`, `latency <= +eps_l` | cost / latency stayed within budget |
| `regression flag` | no flagged regression |

The CLI prints **`ACCEPT`** (exit 0) or **`REJECT`** (exit 1) with the failing
reasons. The full platform gate can additionally return **`LIMITED_ROLLOUT`** —
a partial promotion when a change is a net improvement but carries a watch-item
(e.g. a soft OOD regression). See the redacted example in
[`sample_assurance_card_redacted.json`](sample_assurance_card_redacted.json),
which records a `LIMITED_ROLLOUT` decision with reason `ood_regressed`.

`clean_score = raw * (1 - dcr)` — contamination directly discounts the score,
which is why a memorised public win cannot buy a promotion.

## What this does NOT show

- This is **synthetic / redacted** demo data — **not** a training dataset, and
  not a measurement of any real agent or customer.
- It does **not** include hidden evaluations, gold answers, raw traces,
  customer data, private anti-hack traps, private engine internals, or secrets.
  Those are never published — that separation is what keeps the feedback clean.
- The CLI scores eval **cards** you provide; it does not run a model, call a
  provider, or generate the hidden/OOD/adversarial scenarios (that is the
  private evaluation platform).

## Links

- **PyPI** — <https://pypi.org/project/vlabs-sdk/>
- **Hugging Face evidence dataset** — <https://huggingface.co/datasets/verifiablelabs/vlabs-clean-gate-evidence>
- **Weights & Biases report** — <https://wandb.ai/verifiable-labs/clean-generalization-gate/reports/Verifiable-Labs-Synthetic-Clean-Gate-Evidence-Pack--VmlldzoxNzIxNzA0NQ>
- **Documentation** — <https://github.com/verifiablelabs/vlabs-docs>
- **SDK** — <https://github.com/verifiablelabs/vlabs-sdk>

## Formal scope

Selected mathematical properties behind the contamination-resistant promotion
gate are machine-verified in Lean 4. The implementation is property-tested
against the formal specification.
