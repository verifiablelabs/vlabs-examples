# vlabs-examples

Public-safe examples for the Verifiable Labs SDK and clean promotion gate.

> Verifiable Labs builds clean feedback and promotion gates for increasingly general AI agents.

Everything in this repository is **illustrative**: fake IDs, dummy-provider
outputs, and synthetic numbers. No real customer data, no hidden evaluation
content, no gold answers, no raw traces, no private traps, no private engine
internals.

## Run the 5-minute demo

```bash
pip install "vlabs-sdk==0.0.2"
vlabs --help

# An honest candidate that genuinely improves clean generalization → ACCEPT (exit 0)
vlabs clean-gate --old examples/demo/baseline.json --new examples/demo/candidate.json

# A candidate that games the public checks (contamination up, OOD down) → REJECT (exit 1)
vlabs clean-gate --old examples/demo/baseline.json --new examples/demo/candidate_overfit.json
```

The candidate with the **highest public score** is the one the gate **rejects** —
because a higher visible score is not a promotion. The full walkthrough (what it
shows, what it does not, how to read the decision) is in
[`examples/demo/README.md`](examples/demo/README.md).

## Contents

- [`examples/demo/`](examples/demo/) — the 5-minute clean-gate demo: a baseline
  card, an honest candidate (ACCEPT), an overfit candidate (REJECT), the exact
  expected output, and a redacted `LIMITED_ROLLOUT` assurance card.
- [`examples/run_clean_gate_demo.md`](examples/run_clean_gate_demo.md) — run the
  `clean-gate` CLI against sample metric cards.
- [`examples/sample_assurance_card.json`](examples/sample_assurance_card.json) —
  an illustrative assurance card showing the shape of a gate decision.
- [`examples/run_evaluate_only_dummy.py`](examples/run_evaluate_only_dummy.py),
  [`improve_and_gate_mock.py`](examples/improve_and_gate_mock.py),
  [`substrate_mock.py`](examples/substrate_mock.py) — synthetic, dummy-provider walkthroughs.

## What this does not show

Synthetic / redacted demo data only — **not** a training dataset. No customer
data, hidden evaluations, gold answers, raw traces, private anti-hack traps, or
private engine internals; those are never published.

## Links

- PyPI — <https://pypi.org/project/vlabs-sdk/>
- Hugging Face evidence dataset — <https://huggingface.co/datasets/verifiablelabs/vlabs-clean-gate-evidence>
- Weights & Biases report — <https://wandb.ai/verifiable-labs/clean-generalization-gate/reports/Verifiable-Labs-Synthetic-Clean-Gate-Evidence-Pack--VmlldzoxNzIxNzA0NQ>
- Documentation — <https://github.com/verifiablelabs/vlabs-docs>

## Formal scope

Selected mathematical properties behind the contamination-resistant promotion
gate are machine-verified in Lean 4. The implementation is property-tested
against the formal specification.

## License

Apache-2.0.
