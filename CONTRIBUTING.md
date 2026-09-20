# Contributing

Thanks for taking a look at Elevator Simulator. It's a small, dependency-free
project, so the bar for contributing is low -- these are just the basics.

## Running the tests

```bash
python -m unittest discover -v tests
# or, if you have pytest installed
python -m pytest tests/ -v
```

All 33+ tests should pass before and after your change. If you touch
`elevator_simulator/`, also run the demo once to sanity-check the output
still makes sense:

```bash
python demo.py
```

## Code style

- Pure Python standard library only -- no new runtime dependencies.
- Match the existing style: `from __future__ import annotations`, type hints
  on public functions/methods, dataclasses for plain data (`Rider`,
  `Elevator`, `SimulationResult`).
- Keep dispatch strategies honest: `assign()` decides *who* answers a hall
  call, `next_direction()` decides *which way a car moves next*. Don't mix
  the two concerns in one method.
- Prefer a short docstring over inline comments for anything non-obvious --
  the existing modules explain *why*, not just *what*.

## Submitting changes

1. Fork/branch, make a focused change (one logical thing per commit).
2. Add or update tests for any behavioral change -- a bug fix without a
   regression test is easy to reintroduce.
3. Make sure `python -m unittest discover -v tests` is green.
4. Open a pull request describing what changed and why. Small, reviewable
   PRs are much easier to merge than large ones.
