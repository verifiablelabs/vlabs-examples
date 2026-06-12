"""Every example must run clean with the public SDK + dummy provider."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(script: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(ROOT / "examples" / script)],
        capture_output=True, text=True, timeout=120,
    )


def test_dummy_refund_agent_runs() -> None:
    assert _run("agents/dummy_refund_agent.py").returncode == 0


def test_dummy_coding_agent_runs() -> None:
    assert _run("agents/dummy_coding_agent.py").returncode == 0


def test_evaluate_only_demo() -> None:
    res = _run("run_evaluate_only_dummy.py")
    assert res.returncode == 0, res.stderr
    assert "EVALUATE-ONLY DEMO OK" in res.stdout


def test_improve_and_gate_mock() -> None:
    res = _run("improve_and_gate_mock.py")
    assert res.returncode == 0, res.stderr
    assert "MOCK gate decision: ACCEPT" in res.stdout


def test_substrate_mock() -> None:
    res = _run("substrate_mock.py")
    assert res.returncode == 0, res.stderr
    assert "PROHIBITED" in res.stdout


def test_clean_gate_cli_accept_and_reject() -> None:
    cards = ROOT / "examples" / "cards"
    ok = subprocess.run(
        ["vlabs-prm-eval", "clean-gate", "--old", str(cards / "clean_old.json"),
         "--new", str(cards / "clean_new_accept.json")], capture_output=True,
    )
    assert ok.returncode == 0
    rej = subprocess.run(
        ["vlabs-prm-eval", "clean-gate", "--old", str(cards / "clean_old.json"),
         "--new", str(cards / "clean_reject_dcr.json")], capture_output=True,
    )
    assert rej.returncode == 1
