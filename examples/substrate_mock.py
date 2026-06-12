"""MOCK substrate record — synthetic, shows the shape only."""
from __future__ import annotations

import json

RECORD = {
    "_comment": "ILLUSTRATIVE MOCK — synthetic numbers, fake IDs.",
    "record_type": "substrate_record",
    "agent_id": "agent_demo_0001",
    "transfer": {"public_to_hidden_gap": 0.06, "clean_transfer": 0.71},
    "failure_memory": [{"scenario_kind": "adversarial", "failure": "policy_override_attempt"}],
    "generated_curriculum": [{"kind": "ood", "difficulty": "harder", "count": 8}],
    "future_training_use": "PROHIBITED",
}

if __name__ == "__main__":
    print(json.dumps(RECORD, indent=2))
    print("SUBSTRATE MOCK OK")
