"""A deterministic toy coding agent (synthetic — for demos only)."""
from __future__ import annotations


class DummyCodingAgent:
    """Answers a tiny fixed set of coding prompts; refuses the rest."""

    _KNOWN = {
        "reverse a string": "def reverse(s):\n    return s[::-1]",
        "sum a list": "def total(xs):\n    return sum(xs)",
    }

    def solve(self, observation: dict) -> dict:
        task = str(observation.get("task", "")).lower().strip()
        code = self._KNOWN.get(task)
        if code is None:
            return {"status": "refuse", "reason": "task not in demo set"}
        return {"status": "ok", "code": code}


if __name__ == "__main__":
    agent = DummyCodingAgent()
    print(agent.solve({"task": "reverse a string"}))
    print(agent.solve({"task": "write an operating system"}))
