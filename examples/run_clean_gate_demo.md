# Clean promotion gate demo

```bash
pip install "vlabs-prm-eval @ git+https://github.com/verifiablelabs/verifiable-labs-envs@main#subdirectory=tools/vlabs-prm-eval"

vlabs-prm-eval clean-gate --old examples/cards/clean_old.json --new examples/cards/clean_new_accept.json
# -> ACCEPT (exit 0)
vlabs-prm-eval clean-gate --old examples/cards/clean_old.json --new examples/cards/clean_reject_dcr.json
# -> REJECT (exit 1): dcr_increased
```
