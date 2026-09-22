# ADR-0001 — The first CI test asserts environment truth; this repo installs no package

- Status: Proposed
- Approver: (pending)
- Date: 2026-09-22

## Context

LL-002 (`R-018`) requires CI on an empty repo: pytest running on every PR, with branch
protection naming that run as a required check. `pytest` exits 5 on an empty test suite,
which is itself red, so a real test has to exist before there is any site content — and
LL-002's scope forbids writing that content (no pages; that is LL-013).

Unlike `linkling-api`, this repo will never hold an installable Python package:
`linkling-api/docs/adr/0008-repo-layout-and-names.md` already fixed `linkling-web` as
hand-written HTML and CSS with no build step. So the sibling decision made in
`linkling-api` (a `src/` package skeleton, importable for its own sake) does not transfer
here, and needed its own answer rather than a copy.

## Decision

**Proposed.**

1. **`pyproject.toml` declares `[tool.setuptools] packages = []`** — explicit, not
   auto-discovery. It exists only to give CI a `test` extra (`pytest>=8`) to install via
   `pip install -e ".[test]"`, matching the `linkling-api` CI shape so a future worker
   does not need to learn a second install pattern. It does not, and should not, declare
   any importable module: there is nothing here for one to wrap.
2. **The one real test has two parts, both asserting configuration truth:**
   - `test_ci_pins_python_312` — `assert sys.version_info[:2] == (3, 12)`. Verified
     locally: passes under Python 3.12.14, **fails** (`assert (3, 13) == (3, 12)`) under
     3.13.
   - `test_pyproject_declares_312` — parses `pyproject.toml` with `tomllib` and asserts
     `project.requires-python == ">=3.12"`. This is this repo's analogue of `linkling-api`'s
     "package installs" test: since there is no package to import, the thing worth
     proving instead is that the interpreter pin and the declared metadata cannot
     silently drift apart from each other.
3. **Rejected: mirroring `linkling-api`'s src-layout package.** Would fabricate a Python
   package for a site that ADR-0008 already decided has none — pre-empting that decision
   rather than building on it.
4. **Rejected: `assert True`.** Vacuous; catches no misconfiguration.

## Consequences

- LL-013 adds HTML/CSS pages and any static-content tests directly; the CI workflow
  (`pip install -e ".[test]"`, `pytest -q`) does not need to change to accommodate them,
  since it never assumed a package existed.
- If this repo later needs a real Python tool (e.g. an HTML/link validator script), it can
  either drop straight into `dependencies`/`test` in `pyproject.toml` (no CI change) or,
  if it becomes substantial, revisit `packages = []` in a follow-up ADR rather than
  silently growing a package nobody decided to have.
- Cross-repo note: `linkling-api/docs/adr/0010-ci-first-test-and-package-skeleton.md`
  is this decision's sibling for the API repo — same problem (CI needs a real test before
  there is application code), different answer because the two repos' packaging shapes
  differ by ADR-0008.
