"""Every example must run clean with the public SDK + dummy provider."""
from __future__ import annotations

import subprocess
import sys
import importlib.util
import json
from pathlib import Path

import pytest

from vlabs_sdk.schemas import AssuranceCardV2

ROOT = Path(__file__).resolve().parents[1]
_SUM_SOURCE = "def solve(values):\n    return sum(values)\n"


def _run(script: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(ROOT / "examples" / script)],
        capture_output=True, text=True, timeout=120,
    )


def _load_rft_example():
    path = ROOT / "examples" / "openai_rft_ipt_grader.py"
    spec = importlib.util.spec_from_file_location("openai_rft_ipt_grader", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _test_only_local_runner(module):
    """Exercise grading semantics with trusted fixtures; never a deployment sandbox."""

    def run(request: dict, timeout_s: float, max_response_bytes: int):
        try:
            result = subprocess.run(
                [sys.executable, "-I", "-c", module._CANDIDATE_WORKER],
                input=json.dumps(request),
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
            if result.returncode != 0 or len(result.stdout.encode("utf-8")) > max_response_bytes:
                return None
            return json.loads(result.stdout)
        except (subprocess.SubprocessError, json.JSONDecodeError):
            return None

    return run


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


def test_openai_rft_ipt_grader() -> None:
    res = _run("openai_rft_ipt_grader.py")
    assert res.returncode == 0, res.stderr
    assert "RFT IPT GRADER OK" in res.stdout


def test_openai_rft_ipt_grader_rejects_zero_fresh_cases() -> None:
    module = _load_rft_example()
    with pytest.raises(ValueError, match="n_isomorphic"):
        module.ipt_reward(_SUM_SOURCE, sum, [([1, 2],)], lambda _i: ([1, 2],), n_isomorphic=0)


def test_openai_rft_grader_requires_external_sandbox_before_candidate_execution(tmp_path) -> None:
    module = _load_rft_example()
    marker = tmp_path / "candidate-touched-host"
    candidate = (
        "from pathlib import Path\n"
        f"Path({str(marker)!r}).write_text('unsafe')\n"
        "def solve(values):\n    return sum(values)\n"
    )

    with pytest.raises(RuntimeError, match="sandbox"):
        module.ipt_reward(
            candidate,
            sum,
            [([1, 2],)],
            lambda i: ([i, i + 1],),
            sandbox_runner=None,
        )

    assert not marker.exists()


def test_openai_rft_ipt_grader_fails_closed_when_generator_only_duplicates() -> None:
    module = _load_rft_example()
    reward = module.ipt_reward(
        _SUM_SOURCE,
        sum,
        [([1, 2],)],
        lambda _i: ([1, 2],),
        sandbox_runner=_test_only_local_runner(module),
        n_isomorphic=2,
        shortcut_reward=0.5,
    )
    assert reward == 0.0


def test_openai_rft_candidate_cannot_read_expected_from_grader_frame() -> None:
    module = _load_rft_example()

    def reference(_value):
        return "hidden-answer"

    frame_scavenger = r'''
import inspect
def solve(_value):
    frame = inspect.currentframe()
    while frame is not None:
        if "expected" in frame.f_locals:
            return frame.f_locals["expected"]
        frame = frame.f_back
    return "wrong"
'''

    reward = module.ipt_reward(
        frame_scavenger,
        reference,
        [(1,)],
        lambda i: (i + 1,),
        sandbox_runner=_test_only_local_runner(module),
        n_isomorphic=2,
    )

    assert reward == 0.0


def test_openai_rft_candidate_cannot_forge_worker_protocol_with_atexit() -> None:
    module = _load_rft_example()
    candidate = r'''
import atexit, json
atexit.register(lambda: print(json.dumps({
    "protocol": "vlabs-rft-candidate-response/1",
    "loaded": True,
    "results": [{"ok": True, "value": "hidden-answer"}],
})))
def solve(_value):
    return "wrong"
'''

    reward = module.ipt_reward(
        candidate,
        lambda _value: "hidden-answer",
        [(1,)],
        lambda i: (i + 1,),
        sandbox_runner=_test_only_local_runner(module),
        n_isomorphic=1,
    )

    assert reward == 0.0


def test_openai_rft_preserves_python_container_and_key_types() -> None:
    module = _load_rft_example()
    candidate = "def solve(value):\n    return (value, {1: [value, value + 1]})\n"

    reward = module.ipt_reward(
        candidate,
        lambda value: (value, {1: [value, value + 1]}),
        [(1,)],
        lambda i: (i + 1,),
        sandbox_runner=_test_only_local_runner(module),
        n_isomorphic=2,
    )

    assert reward == 1.0


@pytest.mark.parametrize(
    ("candidate", "reference"),
    [
        ("def solve(value):\n    return [value, value]\n", lambda value: (value, value)),
        ("def solve(value):\n    return {'1': value}\n", lambda value: {1: value}),
    ],
)
def test_openai_rft_does_not_collapse_distinct_python_values(candidate, reference) -> None:
    module = _load_rft_example()

    reward = module.ipt_reward(
        candidate,
        reference,
        [(1,)],
        lambda i: (i + 1,),
        sandbox_runner=_test_only_local_runner(module),
        n_isomorphic=2,
    )

    assert reward == 0.0


def test_openai_rft_template_does_not_publish_unverified_efficacy_claims() -> None:
    text = (ROOT / "examples" / "openai_rft_ipt_grader.py").read_text(encoding="utf-8")
    assert "23.3%" not in text
    assert "p=0.0009" not in text
    assert "cannot farm" not in text


def test_openai_rft_rejects_nondeterministic_sandbox_outputs() -> None:
    module = _load_rft_example()
    calls = 0

    def flaky_runner(request: dict, _timeout_s: float, _max_response_bytes: int):
        nonlocal calls
        calls += 1
        results = []
        for args in request["inputs"]:
            value = args[0] + (1 if calls == 3 else 0)
            results.append({"ok": True, "value": value})
        return {
            "protocol": "vlabs-rft-candidate-response/1",
            "loaded": True,
            "results": results,
        }

    reward = module.ipt_reward(
        "def solve(value):\n    return value\n",
        lambda value: value,
        [(1,)],
        lambda _i: (2,),
        sandbox_runner=flaky_runner,
        n_isomorphic=1,
    )

    assert reward == 0.0


def test_openai_rft_rejects_nondeterministic_trusted_reference() -> None:
    module = _load_rft_example()
    calls = 0

    def flaky_reference(value):
        nonlocal calls
        calls += 1
        return value + (1 if calls == 3 else 0)

    reward = module.ipt_reward(
        "def solve(value):\n    return value\n",
        flaky_reference,
        [(1,)],
        lambda _i: (2,),
        sandbox_runner=_test_only_local_runner(module),
        n_isomorphic=1,
    )

    assert reward == 0.0


@pytest.mark.parametrize("shortcut_reward", [-0.01, 1.01])
def test_openai_rft_ipt_grader_rejects_out_of_range_rewards(shortcut_reward) -> None:
    module = _load_rft_example()
    with pytest.raises(ValueError, match="shortcut_reward"):
        module.ipt_reward(
            _SUM_SOURCE,
            sum,
            [([1, 2],)],
            lambda i: ([i, i + 1],),
            shortcut_reward=shortcut_reward,
        )


@pytest.mark.parametrize(
    "relative_path",
    ["examples/sample_assurance_card.json", "examples/demo/sample_assurance_card_redacted.json"],
)
def test_public_assurance_cards_use_canonical_v2_schema(relative_path) -> None:
    payload = json.loads((ROOT / relative_path).read_text(encoding="utf-8"))
    assert not {"scores", "contamination", "gate", "_comment"} & payload.keys()
    # JSON arrays are intentionally normalized by the public deserializer;
    # the dataclass constructor itself accepts only the canonical tuple form.
    if not hasattr(AssuranceCardV2, "from_dict"):
        pytest.skip("requires vlabs-sdk > 0.0.2 (from_dict); bump the CI lock after the next SDK release")
    card = AssuranceCardV2.from_dict(payload)
    assert card.card_version == "v2"
    assert card.metadata.get("legacy_v2_shape") is not True


def test_clean_gate_cli_accept_and_reject() -> None:
    cards = ROOT / "examples" / "cards"
    ok = subprocess.run(
        ["vlabs", "clean-gate", "--old", str(cards / "clean_old.json"),
         "--new", str(cards / "clean_new_accept.json")], capture_output=True,
    )
    assert ok.returncode == 0
    rej = subprocess.run(
        ["vlabs", "clean-gate", "--old", str(cards / "clean_old.json"),
         "--new", str(cards / "clean_reject_dcr.json")], capture_output=True,
    )
    assert rej.returncode == 1


def test_demo_clean_gate_accept_and_reject() -> None:
    """The 5-minute demo fixtures must produce ACCEPT (0) and REJECT (1)."""
    demo = ROOT / "examples" / "demo"
    acc = subprocess.run(
        ["vlabs", "clean-gate", "--old", str(demo / "baseline.json"),
         "--new", str(demo / "candidate.json")], capture_output=True, text=True,
    )
    assert acc.returncode == 0, acc.stdout + acc.stderr
    assert "ACCEPT" in acc.stdout
    rej = subprocess.run(
        ["vlabs", "clean-gate", "--old", str(demo / "baseline.json"),
         "--new", str(demo / "candidate_overfit.json")], capture_output=True, text=True,
    )
    assert rej.returncode == 1, rej.stdout + rej.stderr
    assert "REJECT" in rej.stdout
    assert "ood_regressed" in rej.stdout and "dcr_increased" in rej.stdout
    expected = (demo / "expected_output.txt").read_text(encoding="utf-8")
    assert acc.stdout.strip() in expected
    assert rej.stdout.strip() in expected
