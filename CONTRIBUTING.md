# Contributing

Thanks for helping improve Agent Retro. Bug reports, fixes, and focused improvements are welcome.

## Before you start

For anything larger than a small fix, open an issue first so we can agree on the approach.
Report security problems privately as described in [SECURITY.md](SECURITY.md), not in an issue.

## Making a change

1. Fork the repo and create a branch from `main`.
2. Keep the runtime standard-library only. Development-only tools go in `requirements-dev.txt`.
3. Never commit real session logs, prompts, or generated retros. Tests use synthetic data only.
4. If you change preparation code, regenerate the portable toolkit:
   `python tools/build_toolkit.py`
5. Run the tests:

   ```sh
   python3 -m unittest discover -s tests
   python tools/build_toolkit.py --check
   ```

   The browser tests in the [README](README.md#tests) also run in CI.

6. Open a pull request that explains what changed and why.

## Review

A maintainer must approve every pull request, and CI must pass before it can merge. For first-time
contributors, a maintainer starts CI after reviewing the change. Pull requests are squash-merged, so
the PR title becomes the commit message on `main`.

By contributing, you agree that your contributions are licensed under the [MIT License](LICENSE).
