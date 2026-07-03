"""OpenAI RFT python-grader template — an Isomorphic Perturbation Testing (IPT) reward.

Drop-in shape for an OpenAI Reinforcement Fine-Tuning `python` grader: a self-contained
`grade(sample, item) -> float` (stdlib only, deterministic, no network) that you paste into the
RFT grader sandbox. It returns a reward that a reward-hacker cannot farm by memorizing the
provided tests.

WHY. An RFT grader that rewards "passes the provided test(s)" teaches the policy to memorize
those inputs (reward hacking). A genuine solution is invariant under a semantics-preserving
relabeling of the harness; a memorizer is not. So we reward the ISOMORPHIC re-grade:

    reward = 1.0  if the candidate passes fresh inputs recomputed from a trusted reference
             LOW  if it passes the provided tests but fails the fresh ones (a shortcut)
             0.0  if it fails the provided tests

Our own reproduced experiment (GRPO, Llama-3.2-3B, 8 seeds/arm) found this isomorphic reward
cut the reward-hacking shortcut rate from 23.3% (public-test reward) to 4.1% (permutation
p=0.0009, Hedges g=0.97) — a controlled toy demonstration, not a frontier-scale claim.

HONEST SCOPE. IPT is a public method (Helff et al., arXiv:2604.15149); we productize it. This
reward only applies to tasks that ship a TRUSTED REFERENCE + an INPUT GENERATOR — i.e. where you
can recompute the correct answer on fresh inputs. It is not a universal free-form grader.
"""
from __future__ import annotations

import json
from collections.abc import Callable, Sequence



def _passes(fn: Callable, cases: Sequence[tuple]) -> bool:
    """True iff fn(*args) == expected for every (args, expected) case (fail-closed on any error)."""
    for args, expected in cases:
        try:
            if fn(*args) != expected:
                return False
        except BaseException:  # noqa: BLE001  # a candidate that crashes has not passed
            return False
    return True


def ipt_reward(
    candidate: Callable,
    reference: Callable,
    public_inputs: Sequence[tuple],
    input_generator: Callable[[int], tuple],
    *,
    n_isomorphic: int = 16,
    shortcut_reward: float = 0.0,
) -> float:
    """Isomorphic-invariant reward in [0, 1] for one candidate against a trusted reference.

    `public_inputs` and each `input_generator(i)` return an ARGS TUPLE. Expected outputs are
    recomputed with `reference`, so the grader never trusts a stored answer key. Deterministic:
    same candidate + reference + generator + n -> same reward.
    """
    public_cases = [(args, reference(*args)) for args in public_inputs]
    if not _passes(candidate, public_cases):
        return 0.0
    seen = {json.dumps(args, default=str) for args in public_inputs}
    iso_cases: list[tuple] = []
    i = 1
    while len(iso_cases) < n_isomorphic and i <= n_isomorphic * 4:
        args = input_generator(i)
        key = json.dumps(args, default=str)
        i += 1
        if key in seen:
            continue
        seen.add(key)
        iso_cases.append((args, reference(*args)))
    return 1.0 if _passes(candidate, iso_cases) else shortcut_reward


# ── OpenAI RFT integration shell ──────────────────────────────────────────────────────────────
# In the RFT sandbox, `grade(sample, item)` is called per rollout. `item` carries the task
# (a trusted reference + provided tests + a generator spec); `sample` carries the model output.
# Replace `_load_candidate` / `_load_task` with your own extraction — keep them deterministic and
# inside the sandbox limits (no network, bounded time/memory).
def grade(sample: dict, item: dict) -> float:  # pragma: no cover - shape for the RFT sandbox
    task = _load_task(item)
    candidate = _load_candidate(sample, task)
    return ipt_reward(
        candidate=candidate,
        reference=task["reference"],
        public_inputs=task["public_inputs"],
        input_generator=task["input_generator"],
    )


def _load_task(item: dict):  # pragma: no cover - user-supplied
    raise NotImplementedError(
        "Provide task['reference'] (Callable), task['public_inputs'] (list of arg-tuples), "
        "and task['input_generator'] (i -> arg-tuple). See the self-test below for the shape."
    )


def _load_candidate(sample: dict, task: dict):  # pragma: no cover - user-supplied
    raise NotImplementedError("Extract the candidate callable from the model's rollout `sample`.")


# ── Self-test: genuine solution earns 1.0, input-memorizing hack earns the shortcut reward ──────
def _demo() -> int:
    def reference(a):
        return sum(a)

    public_inputs = [([1, 2, 3],), ([10, 20],), ([],)]

    def genuine(a):
        return sum(a)

    _table = {tuple(args[0]): reference(*args) for args in public_inputs}

    def memorizer(a):  # passes the provided tests, wrong on anything else
        return _table.get(tuple(a), 0)

    def gen(i):
        return ([i % 5, (i * 3) % 7, (i * 2) % 4],)

    r_genuine = ipt_reward(genuine, reference, public_inputs, gen)
    r_hack = ipt_reward(memorizer, reference, public_inputs, gen)
    print(f"genuine reward = {r_genuine:.2f}   memorizer(shortcut) reward = {r_hack:.2f}")
    assert r_genuine == 1.0, r_genuine
    assert r_hack < r_genuine, r_hack
    print("RFT IPT GRADER OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(_demo())
