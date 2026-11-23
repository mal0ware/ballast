# Ballast

**A famous result, and the paper that says it does not survive real time. Both reproduced.**

> **Status: planned.** This repository holds the design. No results exist yet, and nothing below is a finding. Each box in the roadmap gets ticked when the code and its tests are in.

## The question

Hold less when markets are volatile and more when they are calm. One paper says that raises risk-adjusted returns across factors. A later one says an investor could not have captured it. Who is right?

## What this will contain

- Moreira and Muir's volatility-scaled factors and their alphas
- The real-time version from Cederburg, O'Doherty, Wang and Yan, where the scaling uses only past data
- Momentum crashes as the worked example

## The result it is built to show

Two tables side by side. In sample, it works. In real time, mostly it does not.

Whatever the answer turns out to be goes at the top of this file, with one chart, before any installation step.

## Sources

- Moreira and Muir, "Volatility-Managed Portfolios", Journal of Finance 72(4), 2017
- Cederburg, O'Doherty, Wang and Yan, "On the performance of volatility-managed portfolios", Journal of Financial Economics 138(1), 2020
- Daniel and Moskowitz, "Momentum crashes", Journal of Financial Economics 122(2), 2016

Every number that differs from a source will be listed in `PAPER.md` with the likely reason.

## Data

Daily and monthly factors from the Kenneth R. French Data Library. Free, no key; fetched by script.

## How it is tested

The maths is tested before any result is trusted.

- The scaled factor has the same unconditional variance as the original, as the paper constructs it
- The real-time version never touches a date after the one it is trading
- Alphas match the paper's Table 1 to stated tolerance over the paper's own sample

## Layout

```
src/ballast/      the code
tests/             maths tests first
scripts/reproduce.py   one command rebuilds every figure and table
scripts/fetch_data.py  downloads public data into data/ (never committed)
results/           committed figures and small tables
PAPER.md           citations, claims tested, comparison with the sources
```

## Roadmap

- [ ] Project skeleton, CI, and the reproduce command
- [ ] Moreira and Muir's volatility-scaled factors and their alphas
- [ ] The real-time version from Cederburg, O'Doherty, Wang and Yan, where the scaling uses only past data
- [ ] Momentum crashes as the worked example
- [ ] `PAPER.md` comparison with the sources
- [ ] Results and limits written up at the top of this file

## Limits

- Factor returns ignore trading costs. Scaling exposure every month is not free.
- The sample here runs past both papers. Results on the extra years are new and are marked as such.
- This is research code. It is not investment advice and it does not trade.

## The name

Ballast is weight a ship takes on or sheds to stay level. Volatility management does that with risk.

## Licence

MIT. See `LICENSE`.
