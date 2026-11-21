"""Exact McNemar power for a paired success difference, as used by the pair rule fixed before the pilot.

Power = sum over D discordant pairs of P(D) * P(exact two-sided binomial test on D rejects at alpha).
Usage: python3 power.py
"""
from math import comb, log, exp, lgamma


def binom_pmf(k, n, p):
    if p <= 0:
        return 1.0 if k == 0 else 0.0
    if p >= 1:
        return 1.0 if k == n else 0.0
    return exp(lgamma(n + 1) - lgamma(k + 1) - lgamma(n - k + 1) + k * log(p) + (n - k) * log(1 - p))


def reject_set(d, alpha=0.05):
    """Counts g (gains among d discordant pairs) where the exact two-sided McNemar p-value <= alpha."""
    out = []
    for g in range(d + 1):
        k = min(g, d - g)
        p = min(1.0, 2 * sum(comb(d, i) for i in range(k + 1)) / 2 ** d)
        if p <= alpha:
            out.append(g)
    return out


def power(n, discordance, effect, alpha=0.05):
    p_gain = (discordance + effect) / 2
    q = p_gain / discordance
    tot = 0.0
    for d in range(n + 1):
        pd = binom_pmf(d, n, discordance)
        if pd < 1e-12:
            continue
        tot += pd * sum(binom_pmf(g, d, q) for g in reject_set(d, alpha))
    return tot


if __name__ == "__main__":
    print("power, 500 pairs, 17.5% discordance, 3 points:", round(power(500, 0.175, 0.03), 3))
    for n in range(1400, 1900, 50):
        print(n, round(power(n, 0.175, 0.03), 3))
    for disc in (0.05, 0.0535, 0.055):
        print("disc", disc, round(power(500, disc, 0.03), 3))
