"""MODEL_SURVEY W4 confirmatory tests (`docs/stage0/MODEL_SURVEY_W4_LOCKED_REGISTRATION_DRAFT.md` §6-§7), offline.

Pure functions over per-item counts; `scripts/model_survey_w4_analyze.py` reads the runs and calls them.

Decisions taken before any locked score was computed (see `docs/stage0/MODEL_SURVEY_W4_ANALYSIS_NOTES.md`):

- **Cluster bootstrap.** Items sharing an `image_sha256` are resampled together; 10,000 resamples, seed
  20261012, percentile 95% intervals (§6).
- **S1** (per model and task that looped on at least 5% of calibration items): the Δ micro F1 (stop − greedy)
  with a one-sided bootstrap p-value `(1 + #{draws <= 0}) / (1 + B)`, Holm-adjusted over the S1 family. It passes
  when the adjusted p is below 0.05, which is the lower bound of the Holm-adjusted one-sided interval being
  above 0.
- **S2**: pooled over the models read, the share of *ended* outputs (not at `max_new_tokens`) the stop changes.
  Passes when the point share is at most 1%; the upper 95% bound is reported (cluster bootstrap and exact
  one-sided binomial).
- **R1** (per model, Full-page, stopped outputs): (line_missing + span_missing) / misread_with_base,
  passes when the lower bound of the 95% percentile interval is above 3.
- Holm is also applied to the p-values of S2 (exact one-sided binomial against the 1% threshold, treating the
  ended outputs as independent) and R1 (one-sided bootstrap against 3), as a conservative second reading,
  reported beside the as-written criteria.
"""

from __future__ import annotations

import collections
import math
import random
from typing import Any, Callable, Sequence

from labbs2026.thai_marks.order_free import prf

SEED = 20261012
RESAMPLES = 10_000
ALPHA = 0.05
LOOP_SHARE_MIN = 0.05
S2_MAX_SHARE = 0.01
R1_RATIO = 3.0


def clusters(ids: Sequence[str], page_hash: dict[str, str]) -> list[list[str]]:
    """Items grouped by image hash (ids without a hash are their own group), in a stable order."""
    groups: dict[str, list[str]] = collections.defaultdict(list)
    for i in sorted(ids):
        groups[page_hash.get(i, i)].append(i)
    return [groups[k] for k in sorted(groups)]


def draws(groups: list[list[str]], statistic: Callable[[list[str]], float | None], *,
          resamples: int = RESAMPLES, seed: int = SEED) -> list[float]:
    """`statistic` over resamples of whole groups (the same resamples for every call with the same seed)."""
    rng = random.Random(seed)
    out = []
    n = len(groups)
    for _ in range(resamples):
        sample = [i for g in (groups[rng.randrange(n)] for _ in range(n)) for i in g]
        value = statistic(sample)
        if value is not None:
            out.append(value)
    return sorted(out)


def percentile_interval(sorted_draws: list[float]) -> list[float] | None:
    if not sorted_draws:
        return None
    n = len(sorted_draws)
    return [sorted_draws[int(0.025 * n)], sorted_draws[min(n - 1, int(0.975 * n))]]


def one_sided_p(sorted_draws: list[float], null: float, *, greater: bool = True) -> float | None:
    """Bootstrap p-value for H1 `statistic > null` (or `< null`): `(1 + #{draws on the null side}) / (1 + B)`."""
    if not sorted_draws:
        return None
    b = len(sorted_draws)
    count = sum(1 for d in sorted_draws if (d <= null if greater else d >= null))
    return (1 + count) / (1 + b)


def holm(p_values: dict[str, float | None], alpha: float = ALPHA) -> dict[str, dict[str, Any]]:
    """Holm step-down adjusted p-values (monotone) and whether each is below `alpha`."""
    items = sorted(((k, p) for k, p in p_values.items() if p is not None), key=lambda kv: kv[1])
    m = len(items)
    out: dict[str, dict[str, Any]] = {k: {"p": None, "p_holm": None, "reject": False}
                                       for k in p_values}
    running = 0.0
    for rank, (key, p) in enumerate(items):
        running = max(running, min(1.0, (m - rank) * p))
        out[key] = {"p": p, "p_holm": running, "reject": running < alpha}
    return out


def micro_f1(counts: dict[str, dict], ids: Sequence[str]) -> float | None:
    """Micro F1 of `mark_counts` rows over `ids` (`order_free.prf`; None when it is undefined)."""
    return prf([counts[i] for i in ids])["f1"]


def s1_difference(greedy: dict[str, dict], stopped: dict[str, dict], page_hash: dict[str, str], *,
                  resamples: int = RESAMPLES, seed: int = SEED) -> dict[str, Any]:
    """Δ micro F1 (stopped − greedy) over the items both have, with its bootstrap draws summarised."""
    ids = sorted(set(greedy) & set(stopped))

    def diff(sample: list[str]) -> float | None:
        a, b = micro_f1(greedy, sample), micro_f1(stopped, sample)
        return None if a is None or b is None else b - a

    d = draws(clusters(ids, page_hash), diff, resamples=resamples, seed=seed)
    return {"n": len(ids), "difference": diff(ids), "ci95": percentile_interval(d),
            "p_one_sided": one_sided_p(d, 0.0)}


def stop_effects(records: dict[str, dict], cut: dict[str, str]) -> dict[str, list[str]]:
    """Ids of ended outputs, and the subset the stop changed (`cut`: id -> stopped text)."""
    ended = sorted(i for i, r in records.items() if not r["reached_max_new_tokens"])
    changed = [i for i in ended if cut[i] != records[i]["raw_output"]]
    return {"ended": ended, "changed": changed}


def binomial_upper(k: int, n: int, level: float = 0.95) -> float | None:
    """Clopper-Pearson one-sided upper bound for a share `k / n` (bisection on the binomial tail)."""
    if n == 0:
        return None
    if k >= n:
        return 1.0
    lo, hi = k / n, 1.0
    for _ in range(80):
        mid = (lo + hi) / 2
        tail = sum(math.comb(n, j) * mid ** j * (1 - mid) ** (n - j) for j in range(k + 1))
        if tail > 1 - level:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def binomial_cdf(k: int, n: int, p: float) -> float:
    """P(X <= k) for X ~ Binomial(n, p)."""
    return sum(math.comb(n, j) * p ** j * (1 - p) ** (n - j) for j in range(k + 1))


def s2_pooled(per_model: dict[str, dict[str, list[str]]], page_hash: dict[str, str], *,
              resamples: int = RESAMPLES, seed: int = SEED) -> dict[str, Any]:
    """Share of ended outputs the stop changes, pooled over models, with cluster-bootstrap and exact bounds.

    `per_model`: model -> {"ended": ids, "changed": ids}.
    """
    ended = {m: set(v["ended"]) for m, v in per_model.items()}
    changed = {m: set(v["changed"]) for m, v in per_model.items()}
    n = sum(len(v) for v in ended.values())
    k = sum(len(v) for v in changed.values())
    all_ids = sorted({i for v in ended.values() for i in v})

    def share(sample: list[str]) -> float | None:
        count = collections.Counter(sample)
        total = sum(c for m in ended for i, c in count.items() if i in ended[m])
        moved = sum(c for m in changed for i, c in count.items() if i in changed[m])
        return moved / total if total else None

    d = draws(clusters(all_ids, page_hash), share, resamples=resamples, seed=seed)
    return {"models": sorted(per_model), "ended": n, "changed": k,
            "share": k / n if n else None, "ci95_bootstrap": percentile_interval(d),
            "upper95_bootstrap_one_sided": d[min(len(d) - 1, int(0.95 * len(d)))] if d else None,
            "upper95_binomial_one_sided": binomial_upper(k, n),
            # exact one-sided binomial p of seeing at most k changed in n ended outputs if the true share
            # were the 1% threshold (the bootstrap cannot express uncertainty when k = 0)
            "p_one_sided_above_threshold": binomial_cdf(k, n, S2_MAX_SHARE) if n else None,
            "passes_as_written": bool(n and k / n <= S2_MAX_SHARE)}


def r1_ratio(attr: dict[str, collections.Counter], ids: Sequence[str]) -> float | None:
    """(line_missing + span_missing) / misread_with_base over `ids` (inf when the denominator is 0)."""
    num = sum(attr[i]["line_missing"] + attr[i]["span_missing"] for i in ids)
    den = sum(attr[i]["misread_with_base"] for i in ids)
    if den:
        return num / den
    return math.inf if num else None


def r1_test(attr: dict[str, collections.Counter], page_hash: dict[str, str], *,
            resamples: int = RESAMPLES, seed: int = SEED) -> dict[str, Any]:
    ids = sorted(attr)
    d = draws(clusters(ids, page_hash), lambda s: r1_ratio(attr, s), resamples=resamples, seed=seed)
    ci = percentile_interval(d)
    est = r1_ratio(attr, ids)
    return {"n": len(ids), "ratio": est if est is None or math.isfinite(est) else "inf",
            "ci95": None if ci is None else [x if math.isfinite(x) else "inf" for x in ci],
            "passes_as_written": bool(ci and ci[0] > R1_RATIO),
            "p_one_sided": one_sided_p(d, R1_RATIO)}


def loop_share(records: Sequence[dict]) -> float | None:
    """Share of records that reached `max_new_tokens` (the calibration loop rate used for S1 eligibility)."""
    return sum(bool(r["reached_max_new_tokens"]) for r in records) / len(records) if records else None
