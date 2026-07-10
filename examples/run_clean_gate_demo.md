# Clean promotion gate demo

```bash
pip install "vlabs-sdk==0.0.2"

vlabs clean-gate --old examples/cards/clean_old.json --new examples/cards/clean_new_accept.json
# -> ACCEPT (exit 0)
vlabs clean-gate --old examples/cards/clean_old.json --new examples/cards/clean_reject_dcr.json
# -> REJECT (exit 1): dcr_increased
```
