# Quickstart: the clean promotion gate CLI

The `clean-gate` command compares a baseline metric card against a candidate
and prints an ACCEPT / REJECT decision (exit code 0 / 1). It ships with
[verifiable-labs-envs](https://github.com/verifiablelabs/verifiable-labs-envs).

```bash
git clone https://github.com/verifiablelabs/verifiable-labs-envs
cd verifiable-labs-envs/tools/vlabs-prm-eval
pip install -e .

# Sample fixtures are included:
vlabs-prm-eval clean-gate \
  --old tests/fixtures/clean/clean_old.json \
  --new tests/fixtures/clean/clean_new_accept.json
# -> ACCEPT (exit 0)

vlabs-prm-eval clean-gate \
  --old tests/fixtures/clean/clean_old.json \
  --new tests/fixtures/clean/clean_reject_dcr.json
# -> REJECT (exit 1): dcr_increased
```

The gate accepts a candidate only when clean verified-generalization score
improves without regressions in contamination risk, hack risk, calibration,
OOD transfer, cost, or latency. The decision logic mirrors the Lean 4
formal specification and is property-tested against it.
