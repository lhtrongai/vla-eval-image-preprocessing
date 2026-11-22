"""Exact percentile bootstrap for binary outcomes, with no random draws.

With outcomes 0/1, a resample of n paired episodes is fixed by how many lost pairs (reference 1, variant 0) and
gained pairs (reference 0, variant 1) it draws, and these counts follow a multinomial distribution. The bootstrap
distribution of the net change G - L is therefore known exactly; its percentiles are the limit of a Monte Carlo
bootstrap as the number of draws grows. Computing them exactly gives the same numbers on every machine and with
every numpy version, and avoids the last digit of an interval depending on the seed when a percentile lies close to
the boundary between two values. The same holds for two independent (unpaired) samples, where the resampled
success counts are two independent binomials.

Requires numpy only.
"""
import math

import numpy as np

_TOL = 1e-12


def _binom_pmf(n, p):
    k = np.arange(n + 1)
    if p <= 0.0:
        return (k == 0).astype(float)
    if p >= 1.0:
        return (k == n).astype(float)
    logc = np.array([math.lgamma(n + 1) - math.lgamma(i + 1) - math.lgamma(n - i + 1) for i in k])
    return np.exp(logc + k * math.log(p) + (n - k) * math.log1p(-p))


def paired_distribution(lost, gained, n):
    """Support (net change G - L, in episodes, from -n to n) and probabilities of the paired bootstrap."""
    pl, pg = lost / n, gained / n
    probs = np.zeros(2 * n + 1)
    p_l = _binom_pmf(n, pl)
    q = pg / (1.0 - pl) if pl < 1.0 else 0.0
    for l in range(n + 1):
        if p_l[l] == 0.0:
            continue
        p_g = _binom_pmf(n - l, q)
        probs[n - l: n - l + (n - l) + 1] += p_l[l] * p_g      # index of G - L is (G - L) + n
    return np.arange(-n, n + 1), probs / probs.sum()


def unpaired_distribution(k_ref, k_var, n):
    """Support (k_var* - k_ref*, in episodes) and probabilities of the bootstrap of two independent samples."""
    probs = np.convolve(_binom_pmf(n, k_var / n), _binom_pmf(n, k_ref / n)[::-1])
    return np.arange(-n, n + 1), probs / probs.sum()


def quantile(values, probs, q):
    """Smallest value whose cumulative probability reaches q."""
    return values[int(np.searchsorted(np.cumsum(probs), q - _TOL))]


def summarize(values, probs, n):
    """95% interval of the change (variant minus reference) and one-sided 95% upper bound on the loss, in points."""
    lo = quantile(values, probs, 0.025)
    hi = quantile(values, probs, 0.975)
    ub = quantile(-values[::-1], probs[::-1], 0.95)          # 95th percentile of the loss L - G
    return 100 * lo / n + 0.0, 100 * hi / n + 0.0, 100 * ub / n + 0.0


def paired(reference, variant):
    """Exact paired bootstrap of two 0/1 vectors aligned by episode: (lo, hi, upper bound on the loss) in points."""
    r, x = np.asarray(reference), np.asarray(variant)
    lost, gained, n = int(((r == 1) & (x == 0)).sum()), int(((r == 0) & (x == 1)).sum()), len(r)
    return summarize(*paired_distribution(lost, gained, n), n)


def unpaired(reference, variant):
    """Exact bootstrap of two independent samples of equal size: (lo, hi, upper bound on the loss) in points."""
    r, x = np.asarray(reference), np.asarray(variant)
    assert len(r) == len(x)
    return summarize(*unpaired_distribution(int(r.sum()), int(x.sum()), len(r)), len(r))
