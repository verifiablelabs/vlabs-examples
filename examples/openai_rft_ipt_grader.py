"""OpenAI RFT python-grader template — an Isomorphic Perturbation Testing (IPT) reward.

Drop-in shape for an OpenAI Reinforcement Fine-Tuning `python` grader: a self-contained
`grade(sample, item) -> float` (stdlib only and deterministic) that you adapt inside an RFT
grader. Candidate execution is deliberately delegated to a required external sandbox runner;
this file never executes rollout source on the grader host. It tests one concrete memorization
shortcut; it is not a proof that a reward cannot be gamed by other strategies.

WHY. An RFT grader that rewards "passes the provided test(s)" teaches the policy to memorize
those inputs (reward hacking). A genuine solution is invariant under a semantics-preserving
relabeling of the harness; a memorizer is not. So we reward the ISOMORPHIC re-grade:

    reward = 1.0  if the candidate passes fresh inputs recomputed from a trusted reference
             LOW  if it passes the provided tests but fails the fresh ones (a shortcut)
             0.0  if it fails the provided tests

This template intentionally publishes no efficacy number. Validate it on a preregistered,
independently reproduced evaluation for your own task distribution before making a claim.

HONEST SCOPE. IPT is a public method (Helff et al., arXiv:2604.15149); we productize it. This
reward only applies to tasks that ship a TRUSTED REFERENCE + an INPUT GENERATOR — i.e. where you
can recompute the correct answer on fresh inputs. It is not a universal free-form grader.
"""
from __future__ import annotations

import json
import math
from collections.abc import Callable, Sequence

_CANDIDATE_WORKER = r"""
import contextlib, json, math, os, sys
_MAX_DEPTH = 32
_MAX_NODES = 50000
_MAX_BLOB = 1000000

def _take(_budget, _depth):
    if _depth > _MAX_DEPTH:
        raise ValueError("tagged value is too deep")
    _budget[0] -= 1
    if _budget[0] < 0:
        raise ValueError("tagged value has too many nodes")

def _encode_tagged(_value, _depth=0, _budget=None):
    if _budget is None:
        _budget = [_MAX_NODES]
    _take(_budget, _depth)
    if _value is None:
        return {"t": "none"}
    if type(_value) is bool:
        return {"t": "bool", "v": _value}
    if type(_value) is int and _value.bit_length() <= 4096:
        return {"t": "int", "v": _value}
    if type(_value) is float and math.isfinite(_value):
        return {"t": "float", "v": _value}
    if type(_value) is str and len(_value.encode("utf-8")) <= _MAX_BLOB:
        return {"t": "str", "v": _value}
    if type(_value) in (list, tuple):
        return {
            "t": "tuple" if type(_value) is tuple else "list",
            "v": [_encode_tagged(_item, _depth + 1, _budget) for _item in _value],
        }
    if type(_value) is dict:
        _pairs = [
            [_encode_tagged(_key, _depth + 1, _budget), _encode_tagged(_item, _depth + 1, _budget)]
            for _key, _item in _value.items()
        ]
        _pairs.sort(key=lambda _pair: json.dumps(_pair[0], sort_keys=True, separators=(",", ":")))
        return {"t": "dict", "v": _pairs}
    raise ValueError("unsupported protocol value")

def _decode_tagged(_node, _depth=0, _budget=None):
    if _budget is None:
        _budget = [_MAX_NODES]
    _take(_budget, _depth)
    if not isinstance(_node, dict) or not isinstance(_node.get("t"), str):
        raise ValueError("invalid tagged value")
    _tag = _node["t"]
    if _tag == "none" and set(_node) == {"t"}:
        return None
    if set(_node) != {"t", "v"}:
        raise ValueError("invalid tagged value fields")
    _value = _node["v"]
    if _tag == "bool" and type(_value) is bool:
        return _value
    if _tag == "int" and type(_value) is int and _value.bit_length() <= 4096:
        return _value
    if _tag == "float" and type(_value) in (int, float) and math.isfinite(float(_value)):
        return float(_value)
    if _tag == "str" and type(_value) is str and len(_value.encode("utf-8")) <= _MAX_BLOB:
        return _value
    if _tag in {"list", "tuple"} and isinstance(_value, list):
        _items = [_decode_tagged(_item, _depth + 1, _budget) for _item in _value]
        return tuple(_items) if _tag == "tuple" else _items
    if _tag == "dict" and isinstance(_value, list):
        _result = {}
        for _pair in _value:
            if not isinstance(_pair, list) or len(_pair) != 2:
                raise ValueError("invalid tagged dictionary entry")
            _key = _decode_tagged(_pair[0], _depth + 1, _budget)
            _item = _decode_tagged(_pair[1], _depth + 1, _budget)
            try:
                if _key in _result:
                    raise ValueError("duplicate tagged dictionary key")
                _result[_key] = _item
            except TypeError as _exc:
                raise ValueError("unhashable tagged dictionary key") from _exc
        return _result
    raise ValueError("unsupported tagged value")

_decode = json.loads
_encode = json.dumps
_request = _decode(sys.stdin.read())
_protocol_stdout = sys.stdout
_inputs = _request.get("inputs")
_results = []
_loaded = False
_ns = {}
try:
    if set(_request) != {"protocol", "source", "entry_point", "inputs"}:
        raise ValueError("invalid request schema")
    if _request["protocol"] != "vlabs-rft-candidate-request/2" or not isinstance(_inputs, list):
        raise ValueError("invalid request protocol")
    _decoded_inputs = [_decode_tagged(_node) for _node in _inputs]
    if any(type(_args) not in (list, tuple) for _args in _decoded_inputs):
        raise ValueError("each input must be an argument list or tuple")
    with open(os.devnull, "w") as _sink, contextlib.redirect_stdout(_sink), contextlib.redirect_stderr(_sink):
        exec(compile(_request["source"], "<candidate>", "exec"), _ns)
        _fn = _ns.get(_request["entry_point"])
        if not callable(_fn):
            raise ValueError("entry point is not callable")
        _loaded = True
        for _args in _decoded_inputs:
            try:
                _value = _fn(*_args)
                _results.append({"ok": True, "value": _encode_tagged(_value)})
            except BaseException as _exc:
                _results.append({"ok": False, "error": type(_exc).__name__[:128]})
except BaseException as _exc:
    _results = [{"ok": False, "error": type(_exc).__name__[:128]} for _ in (_inputs or [])]
_response = {"protocol": "vlabs-rft-candidate-response/2", "loaded": _loaded, "results": _results}
_protocol_stdout.write(_encode(_response, allow_nan=False, separators=(",", ":")))
"""


_MAX_RUNNER_REQUEST_BYTES = 256_000
_MAX_RUNNER_RESPONSE_BYTES = 256_000
_CODEC_MAX_DEPTH = 32
_CODEC_MAX_NODES = 50_000
_CODEC_MAX_BLOB_BYTES = 1_000_000


def _take_codec_budget(budget: list[int], depth: int) -> None:
    if depth > _CODEC_MAX_DEPTH:
        raise ValueError("tagged value is too deep")
    budget[0] -= 1
    if budget[0] < 0:
        raise ValueError("tagged value has too many nodes")


def _encode_tagged(value: object, depth: int = 0, budget: list[int] | None = None) -> dict:
    if budget is None:
        budget = [_CODEC_MAX_NODES]
    _take_codec_budget(budget, depth)
    if value is None:
        return {"t": "none"}
    if type(value) is bool:
        return {"t": "bool", "v": value}
    if type(value) is int and value.bit_length() <= 4096:
        return {"t": "int", "v": value}
    if type(value) is float and math.isfinite(value):
        return {"t": "float", "v": value}
    if type(value) is str and len(value.encode("utf-8")) <= _CODEC_MAX_BLOB_BYTES:
        return {"t": "str", "v": value}
    if type(value) in (list, tuple):
        return {
            "t": "tuple" if type(value) is tuple else "list",
            "v": [_encode_tagged(item, depth + 1, budget) for item in value],
        }
    if type(value) is dict:
        pairs = [
            [
                _encode_tagged(key, depth + 1, budget),
                _encode_tagged(item, depth + 1, budget),
            ]
            for key, item in value.items()
        ]
        pairs.sort(key=lambda pair: json.dumps(pair[0], sort_keys=True, separators=(",", ":")))
        return {"t": "dict", "v": pairs}
    raise ValueError(f"unsupported protocol value: {type(value).__name__}")


def _decode_tagged(node: object, depth: int = 0, budget: list[int] | None = None) -> object:
    if budget is None:
        budget = [_CODEC_MAX_NODES]
    _take_codec_budget(budget, depth)
    if not isinstance(node, dict) or not isinstance(node.get("t"), str):
        raise ValueError("invalid tagged value")
    tag = node["t"]
    if tag == "none" and set(node) == {"t"}:
        return None
    if set(node) != {"t", "v"}:
        raise ValueError("invalid tagged value fields")
    value = node["v"]
    if tag == "bool" and type(value) is bool:
        return value
    if tag == "int" and type(value) is int and value.bit_length() <= 4096:
        return value
    if tag == "float" and type(value) in (int, float) and math.isfinite(float(value)):
        return float(value)
    if tag == "str" and type(value) is str and len(value.encode("utf-8")) <= _CODEC_MAX_BLOB_BYTES:
        return value
    if tag in {"list", "tuple"} and isinstance(value, list):
        items = [_decode_tagged(item, depth + 1, budget) for item in value]
        return tuple(items) if tag == "tuple" else items
    if tag == "dict" and isinstance(value, list):
        result = {}
        for pair in value:
            if not isinstance(pair, list) or len(pair) != 2:
                raise ValueError("invalid tagged dictionary entry")
            key = _decode_tagged(pair[0], depth + 1, budget)
            item = _decode_tagged(pair[1], depth + 1, budget)
            try:
                if key in result:
                    raise ValueError("duplicate tagged dictionary key")
                result[key] = item
            except TypeError as exc:
                raise ValueError("unhashable tagged dictionary key") from exc
        return result
    raise ValueError("unsupported tagged value")


def _canonical_tagged(value: object) -> str:
    return json.dumps(_encode_tagged(value), sort_keys=True, separators=(",", ":"))


def _candidate_outputs(
    source: str,
    entry_point: str,
    inputs: Sequence[tuple],
    sandbox_runner: Callable[[dict, float, int], dict | None] | None,
    timeout_s: float = 5.0,
):
    """Delegate candidate execution to a configured isolation boundary.

    The runner receives inputs and source but never expected/reference outputs. It must execute the
    request in a disposable non-root microVM/container with no credentials or network, a minimal
    read-only filesystem, and hard wall/CPU/memory/PID/file/output limits. The third argument is the
    maximum response-byte contract. A subprocess on the grader host is not a valid runner.
    """
    if not isinstance(source, str) or not source.strip():
        raise TypeError("candidate must be non-empty Python source, not an in-process callable")
    if not callable(sandbox_runner):
        raise RuntimeError(
            "an external sandbox_runner is required; candidate source is never executed on the grader host"
        )
    try:
        request = {
            "protocol": "vlabs-rft-candidate-request/2",
            "source": source,
            "entry_point": entry_point,
            "inputs": [_encode_tagged(args) for args in inputs],
        }
        encoded_request = json.dumps(request, allow_nan=False, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError):
        return None
    if len(encoded_request) > _MAX_RUNNER_REQUEST_BYTES:
        return None
    responses = []
    encoded_responses = []
    for _ in range(2):
        try:
            response = sandbox_runner(request, timeout_s, _MAX_RUNNER_RESPONSE_BYTES)
            encoded_response = json.dumps(
                response,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        except Exception:  # noqa: BLE001 - a failed isolation service is an inconclusive candidate
            return None
        if len(encoded_response) > _MAX_RUNNER_RESPONSE_BYTES:
            return None
        responses.append(response)
        encoded_responses.append(encoded_response)
    if encoded_responses[0] != encoded_responses[1]:
        return None
    response = responses[0]
    if type(response) is not dict or set(response) != {"protocol", "loaded", "results"}:
        return None
    if response["protocol"] != "vlabs-rft-candidate-response/2" or response["loaded"] is not True:
        return None
    results = response["results"]
    if type(results) is not list or len(results) != len(inputs):
        return None
    decoded_results = []
    for result in results:
        if type(result) is not dict or type(result.get("ok")) is not bool:
            return None
        if set(result) != ({"ok", "value"} if result["ok"] else {"ok", "error"}):
            return None
        if result["ok"]:
            try:
                decoded_results.append({"ok": True, "value": _decode_tagged(result["value"])})
            except (TypeError, ValueError):
                return None
        elif type(result["error"]) is str and len(result["error"].encode("utf-8")) <= 128:
            decoded_results.append(result)
        else:
            return None
    return decoded_results


def _passes(
    source: str,
    entry_point: str,
    cases: Sequence[tuple],
    sandbox_runner: Callable[[dict, float, int], dict | None],
) -> bool:
    """Compare candidate outputs in this trusted process; the worker receives no expected values."""
    results = _candidate_outputs(
        source,
        entry_point,
        [args for args, _expected in cases],
        sandbox_runner,
    )
    if results is None or not cases:
        return False
    for result, (_args, expected) in zip(results, cases):
        if not result["ok"]:
            return False
        try:
            candidate_json = _canonical_tagged(result["value"])
            expected_json = _canonical_tagged(expected)
        except (TypeError, ValueError):
            return False
        if candidate_json != expected_json:
            return False
    return True


def _stable_reference_cases(reference: Callable, inputs: Sequence[tuple]) -> list[tuple] | None:
    """Compute the entire trusted batch twice and reject exceptions or nondeterminism."""

    try:
        first_values = [reference(*args) for args in inputs]
        second_values = [reference(*args) for args in inputs]
    except Exception:  # noqa: BLE001 - a broken trusted reference invalidates the grade
        return None
    cases = []
    for args, first, second in zip(inputs, first_values, second_values):
        try:
            first_json = _canonical_tagged(first)
            second_json = _canonical_tagged(second)
        except Exception:  # noqa: BLE001 - a broken trusted reference invalidates the grade
            return None
        if first_json != second_json:
            return None
        cases.append((args, first))
    return cases


def ipt_reward(
    candidate: str,
    reference: Callable,
    public_inputs: Sequence[tuple],
    input_generator: Callable[[int], tuple],
    *,
    sandbox_runner: Callable[[dict, float, int], dict | None] | None = None,
    n_isomorphic: int = 16,
    shortcut_reward: float = 0.0,
    candidate_entry_point: str = "solve",
) -> float:
    """Isomorphic-invariant reward in [0, 1] for one candidate against a trusted reference.

    `public_inputs` and each `input_generator(i)` return an ARGS TUPLE. Expected outputs are
    recomputed with `reference`, so the grader never trusts a stored answer key. Deterministic:
    same candidate + reference + generator + n -> same reward.

    Misconfiguration fails closed: ``n_isomorphic`` must be positive,
    ``shortcut_reward`` must be in ``[0, 1]``, and a generator that cannot
    produce the requested number of fresh cases yields ``0.0``. A configured
    external ``sandbox_runner`` is mandatory; this function never executes
    candidate source locally.
    """
    if isinstance(n_isomorphic, bool) or not isinstance(n_isomorphic, int) or n_isomorphic < 1:
        raise ValueError("n_isomorphic must be a positive integer")
    if (
        isinstance(shortcut_reward, bool)
        or not isinstance(shortcut_reward, (int, float))
        or not math.isfinite(float(shortcut_reward))
        or not 0.0 <= float(shortcut_reward) <= 1.0
    ):
        raise ValueError("shortcut_reward must be a finite number in [0, 1]")
    if not callable(sandbox_runner):
        raise RuntimeError(
            "an external sandbox_runner is required; candidate source is never executed on the grader host"
        )
    try:
        if any(type(args) is not tuple for args in public_inputs):
            return 0.0
        seen = {_canonical_tagged(args) for args in public_inputs}
    except (TypeError, ValueError):
        return 0.0
    iso_inputs: list[tuple] = []
    i = 1
    while len(iso_inputs) < n_isomorphic and i <= n_isomorphic * 4:
        args = input_generator(i)
        if type(args) is not tuple:
            return 0.0
        try:
            key = _canonical_tagged(args)
        except (TypeError, ValueError):
            return 0.0
        i += 1
        if key in seen:
            continue
        seen.add(key)
        iso_inputs.append(args)
    if len(iso_inputs) != n_isomorphic:
        return 0.0
    all_cases = _stable_reference_cases(reference, [*public_inputs, *iso_inputs])
    if all_cases is None:
        return 0.0
    public_cases = all_cases[: len(public_inputs)]
    iso_cases = all_cases[len(public_inputs) :]
    if not _passes(candidate, candidate_entry_point, public_cases, sandbox_runner):
        return 0.0
    return 1.0 if _passes(candidate, candidate_entry_point, iso_cases, sandbox_runner) else shortcut_reward


# ── OpenAI RFT integration shell ──────────────────────────────────────────────────────────────
# In the RFT sandbox, `grade(sample, item)` is called per rollout. `item` carries the task
# (a trusted reference + provided tests + a generator spec); `sample` carries the model output.
# Replace `_load_candidate` / `_load_task` with your own extraction. The returned task must include
# an external `sandbox_runner(request, timeout_s, max_response_bytes)` that enforces a disposable
# zero-secret, no-network microVM/container boundary. A local subprocess is intentionally rejected
# as a deployment design; the runner owns CPU/memory/PID/file/output limits and returns protocol v1.
def grade(sample: dict, item: dict) -> float:  # pragma: no cover - shape for the RFT sandbox
    task = _load_task(item)
    candidate_source = _load_candidate(sample, task)
    return ipt_reward(
        candidate=candidate_source,
        reference=task["reference"],
        public_inputs=task["public_inputs"],
        input_generator=task["input_generator"],
        sandbox_runner=task["sandbox_runner"],
        candidate_entry_point=task["entry_point"],
    )


def _load_task(item: dict):  # pragma: no cover - user-supplied
    raise NotImplementedError(
        "Provide task['reference'] (Callable), task['public_inputs'] (list of arg-tuples), "
        "task['input_generator'] (i -> arg-tuple), and a production-isolated task['sandbox_runner']."
    )


def _load_candidate(sample: dict, task: dict):  # pragma: no cover - user-supplied
    raise NotImplementedError("Extract candidate Python source from the model's rollout `sample`.")


# ── Self-test: the template refuses to execute candidate code without an isolation runner ──────
def _demo() -> int:
    def reference(a):
        return sum(a)

    try:
        ipt_reward(
            "def solve(a):\n    return sum(a)\n",
            reference,
            [([1, 2, 3],)],
            lambda i: ([i, i + 1],),
        )
    except RuntimeError as exc:
        print(f"RFT IPT GRADER OK — fail-closed until configured: {exc}")
        return 0
    raise AssertionError("candidate execution unexpectedly proceeded without an external sandbox runner")


if __name__ == "__main__":
    raise SystemExit(_demo())
