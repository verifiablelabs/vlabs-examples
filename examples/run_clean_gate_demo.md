# Clean promotion gate demo

```bash
pip install "vlabs-sdk @ git+https://github.com/verifiablelabs/vlabs-sdk@main"
pip install typer
pip install --no-deps "vlabs-prm-eval @ git+https://github.com/verifiablelabs/vlabs-sdk@main#subdirectory=tools/vlabs-prm-eval"

vlabs clean-gate --old examples/cards/clean_old.json --new examples/cards/clean_new_accept.json
# -> ACCEPT (exit 0)
vlabs clean-gate --old examples/cards/clean_old.json --new examples/cards/clean_reject_dcr.json
# -> REJECT (exit 1): dcr_increased
```
