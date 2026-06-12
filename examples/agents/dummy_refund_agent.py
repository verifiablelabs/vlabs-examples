"""A deterministic toy refund-policy agent (synthetic — for demos only)."""
from __future__ import annotations


class DummyRefundAgent:
    """Approves refunds under a threshold, escalates otherwise."""

    def solve(self, observation: dict) -> dict:
        amount = float(observation.get("amount", 0.0))
        days = int(observation.get("days_since_purchase", 0))
        if amount <= 50.0 and days <= 30:
            return {"action": "approve_refund", "reason": "within policy"}
        if days > 30:
            return {"action": "deny", "reason": "outside return window"}
        return {"action": "escalate_to_human", "reason": "amount above auto-approve limit"}


if __name__ == "__main__":
    agent = DummyRefundAgent()
    print(agent.solve({"amount": 25.0, "days_since_purchase": 3}))
    print(agent.solve({"amount": 900.0, "days_since_purchase": 3}))
    print(agent.solve({"amount": 10.0, "days_since_purchase": 90}))
