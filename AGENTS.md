# ZenTracker Agent Notes

Use this file for project-specific operational facts that are easy to forget during implementation.

## Tests

- Run the suite with `python -m unittest discover -s tests -q`.
- `python -m unittest -q` does not discover this project's tests reliably.

## Versioning

- The source of truth for the package version is `pyproject.toml`.
- After a version bump, verify both `python -m zentracker --version` and the test suite.

## Persistence

- Keep metric file write behavior centralized in `zentracker/storage.py`.
- Metric files are written sorted by date using Python's stable sort.
- Preserve the relative order of multiple entries from the same day.

## CLI

- Prefer keeping parsing and UX rules in `zentracker/cli.py`.
- Do not duplicate storage semantics in CLI handlers when a storage-layer rule can own them.
