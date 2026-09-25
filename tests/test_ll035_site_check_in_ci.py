"""LL-035 -- CI's `no-third-party-site` job runs linkling-api's no-third-party check on this site.

The job checks out this repository and jpslav/linkling-api at its trunk, each into its own path
inside the workspace, and runs linkling-api's scripts/no-third-party-check.sh from the second against
the first. It needs Docker and the network, so the job is CI's to run. What does not need them is
pinned here, in the `test` job. The job is pinned by its shape, not by a list of things it must not
carry: its keys, its three steps, and the keys of each step are exactly these, so an `if:`, a `shell:`,
an `env:`, a `defaults:`, a `strategy:`, a fourth step that rewrites what the check runs, or a
checkout input that moves it to another ref or another server is a red here and has to be argued for:

- CI runs on every pull request and on every push to `main`, and on nothing else, so a change is
  checked when it is proposed;
- the job is a checkout of this repository at the pull request's own ref (no `ref:`), a checkout of
  linkling-api's `main` from github.com, and the one step that runs the check; both checkouts are
  pinned by commit SHA, take no token or key, and do not leave the action's own token configured
  behind (the site checkout is the Docker build context); no workflow refers to a secret;
- the step that runs the check points at exactly the paths the checkouts write to, and is not
  `--api-only` (which skips the site);
- every job runs on a versioned Ubuntu image (`ubuntu-NN.NN`), not on an alias or an expression,
  which move on GitHub's schedule; the comment at the top of ci.yml says why (`ubuntu-latest` is
  about to move to Ubuntu 26.04).

These tests read text. The check going red on a site with an external stylesheet, and blind with a
checkout missing, were shown by running it in CI (the pull request that added this file says how).
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"
CI = WORKFLOWS / "ci.yml"

CHECKOUT_SHA = re.compile(r"^\s+uses: actions/checkout@[0-9a-f]{40} # v\d+\.\d+\.\d+$", re.M)


def _code(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("#"))


def _job(name: str) -> str:
    found = re.search(rf"^  {re.escape(name)}:\n(.*?)(?=^  [A-Za-z0-9_-]+:\n|\Z)", _code(CI.read_text()), re.M | re.S)
    assert found, f"ci.yml has no job `{name}`"
    return found.group(1)


def _steps() -> list[str]:
    job = _job("no-third-party-site")
    assert "\n    steps:\n" in job, "the site job has no `steps:`"
    parts = re.split(r"^      - ", job.split("\n    steps:\n", 1)[1], flags=re.M)
    return ["      - " + part for part in parts[1:]]


def _step_keys(step: str) -> list[str]:
    return re.findall(r"^(?:      - |        )([A-Za-z0-9_-]+):", step, re.M)


def _with_keys(step: str) -> list[str]:
    found = re.search(r"^        with:\n((?:          [^\n]*(?:\n|\Z))+)", step, re.M)
    assert found, f"the step has no `with:`:\n{step}"
    return re.findall(r"^          ([A-Za-z0-9_-]+):", found.group(1), re.M)


def _path(step: str) -> str:
    found = re.search(r"^\s+path: (\S+)$", step, re.M)
    assert found, f"the checkout has no `path:`:\n{step}"
    return found.group(1)


def _own_api_and_run() -> tuple[str, str, str]:
    steps = _steps()
    assert len(steps) == 3, (
        f"the site job has {len(steps)} steps, not the three it is pinned to (this repository, linkling-api, the check): "
        "a fourth can rewrite what the check runs, so it has to be argued for here"
    )
    return steps[0], steps[1], steps[2]


def test_ci_runs_on_every_pull_request_and_every_push_to_main_and_on_nothing_else():
    found = re.search(r"^on:\n((?:  [^\n]*\n)+)", CI.read_text(), re.M)
    assert found, "ci.yml has no `on:` block"
    assert found.group(1) == "  pull_request:\n  push:\n    branches: [main]\n", (
        f"ci.yml's `on:` is not `pull_request` plus `push` to `main` and nothing else:\n{found.group(1)}"
    )


def test_the_job_carries_only_the_keys_it_is_pinned_to():
    keys = re.findall(r"^    ([A-Za-z0-9_-]+):", _job("no-third-party-site"), re.M)
    assert keys == ["name", "runs-on", "timeout-minutes", "steps"], (
        f"the site job carries {keys}: an `if:`, `defaults:`, `strategy:`, `env:` or `container:` can make the step "
        "a green no-op or change what it runs on"
    )


def test_the_job_checks_out_this_repository_at_the_pull_requests_ref_and_linkling_api_at_its_trunk():
    own, api, _ = _own_api_and_run()
    for step in (own, api):
        assert CHECKOUT_SHA.search(step), f"a checkout is not actions/checkout pinned by commit SHA with its tag:\n{step}"
    assert _step_keys(own) == ["name", "uses", "with"] and _step_keys(api) == ["name", "uses", "with"]
    # No `ref:` on the first: with none the action checks out what the event is about, the pull request's
    # merge with its base. A `ref:` there would test trunk on every pull request and never the change.
    assert _with_keys(own) == ["path", "persist-credentials"], f"the site checkout's inputs are {_with_keys(own)}"
    assert _with_keys(api) == ["repository", "ref", "path", "persist-credentials"], (
        f"the linkling-api checkout's inputs are {_with_keys(api)}: a `token`, an `ssh-key` or a "
        "`github-server-url` would change whose script this runs or how it is fetched"
    )
    assert re.search(r"^\s+repository: jpslav/linkling-api$", api, re.M), "the second checkout is not linkling-api"
    assert re.search(r"^\s+ref: main$", api, re.M), "the linkling-api checkout does not name its trunk"
    paths = [_path(own), _path(api)]
    assert paths[0] != paths[1], f"both checkouts write to {paths[0]!r}"
    # The site checkout is the Docker build context: linkling-api nested in it would ride along in the
    # context, and the check's scratch data (.smoke-data/, inside linkling-api) with it.
    for inner, outer in (paths, paths[::-1]):
        assert not inner.startswith(outer.rstrip("/") + "/"), f"the checkout at {inner!r} is inside the one at {outer!r}"
    for path in paths:
        # A checkout refuses a path outside the workspace, and `.` would put one inside the other.
        assert not path.startswith(("/", "..", ".")), f"path {path!r} is not a named directory inside the workspace"


def test_neither_checkout_persists_the_actions_own_token_and_no_workflow_refers_to_a_secret():
    own, api, _ = _own_api_and_run()
    for step in (own, api):
        assert re.search(r"^\s+persist-credentials: false$", step, re.M), (
            f"a checkout leaves the action's token configured in its `.git`:\n{step}"
        )
    workflows = sorted(WORKFLOWS.glob("*.y*ml"))
    assert CI in workflows, "the walk found no ci.yml"
    for workflow in workflows:
        assert not re.search(r"\bsecrets\b", _code(workflow.read_text())), f"{workflow.name} refers to secrets"
        assert "DEPLOY_KEY" not in workflow.read_text(), f"{workflow.name} names a deploy key"


def test_the_check_runs_from_the_linkling_api_checkout_against_this_repositorys_and_nothing_else_is_in_the_step():
    own, api, run = _own_api_and_run()
    assert _step_keys(run) == ["name", "run"], (
        f"the step that runs the check carries {_step_keys(run)}: an `if:`, `shell:`, `env:`, `continue-on-error:` or "
        "`working-directory:` can make it a green no-op"
    )
    expected = (
        r'^      - name: [^\n]+\n        run: LINKLING_WEB_DIR="\$GITHUB_WORKSPACE/'
        + re.escape(_path(own))
        + r'" '
        + re.escape(_path(api))
        + r"/scripts/no-third-party-check\.sh\n?$"
    )
    assert re.match(expected, run), (
        f"the step does not run linkling-api's check against this repository's checkout, from their paths, "
        f"as one plain command (no --api-only, no `|| true`):\n{run}"
    )


def test_every_job_runs_on_a_versioned_ubuntu_image():
    jobs = re.findall(r"^  ([A-Za-z0-9_-]+):\n", CI.read_text().split("\njobs:\n", 1)[1], re.M)
    # The population is fixed: these three exist, so a walk that found fewer read nothing.
    assert {"test", "image-privacy", "no-third-party-site"} <= set(jobs), f"the walk found the jobs {jobs}"
    runners = [
        (workflow.name, m.group(1))
        for workflow in sorted(WORKFLOWS.glob("*.y*ml"))
        for m in re.finditer(r"^\s*(?:- )?runs-on:[ \t]*(.*?)[ \t]*(?:#.*)?$", _code(workflow.read_text()), re.M)
    ]
    assert len(runners) >= 3, f"found {len(runners)} `runs-on:` lines for at least three jobs: {runners}"
    unpinned = [r for r in runners if not re.fullmatch(r"ubuntu-\d{2}\.\d{2}", r[1])]
    assert not unpinned, (
        f"these jobs do not name a versioned Ubuntu image (an alias such as ubuntu-latest or ubuntu-slim, an expression, "
        f"or a list, moves on GitHub's schedule or hides what it is): {unpinned}"
    )
