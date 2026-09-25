"""LL-035 -- CI's `no-third-party-site` job runs linkling-api's no-third-party check on this site.

The job checks out this repository and jpslav/linkling-api at its trunk, each into its own path
inside the workspace, and runs linkling-api's scripts/no-third-party-check.sh from the second against
the first. It needs Docker and the network, so the job is CI's to run. What does not need them is
pinned here, in the `test` job:

- CI runs on every pull request and on every push to `main`, so a change is checked when it is
  proposed;
- the job has both checkouts, the second one of linkling-api's `main`, with no token or key input
  and without leaving the action's own token configured behind (the site checkout is the Docker
  build context), and no workflow refers to a secret;
- the step that runs the check points at exactly the paths the checkouts write to, is not
  `--api-only` (which skips the site) and comes after both checkouts;
- nothing in the job can turn that step into a green no-op: no `if:`, `continue-on-error:` or
  `working-directory:`;
- no job runs on a moving `-latest` runner alias, which moves on GitHub's schedule (the alias moves to
  Ubuntu 26 from 2026-10-19, actions/runner-images#14748).

These tests read text. The check going red on a site with an external stylesheet, and blind with a
checkout missing, were shown by running it in CI (the pull request that added this file says how).
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WORKFLOWS = ROOT / ".github" / "workflows"
CI = WORKFLOWS / "ci.yml"


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
    steps = ["      - " + part for part in parts[1:]]
    assert steps, "the site job has no steps"
    return steps


def _checkouts() -> list[str]:
    return [s for s in _steps() if re.search(r"^\s+(?:- )?uses: actions/checkout@", s, re.M)]


def _own_and_api_checkout() -> tuple[str, str]:
    """(this repository's checkout step, linkling-api's), each found by what it names."""
    checkouts = _checkouts()
    assert len(checkouts) == 2, f"the site job has {len(checkouts)} checkouts, not the two it needs"
    api = [s for s in checkouts if re.search(r"^\s+repository: ", s, re.M)]
    own = [s for s in checkouts if not re.search(r"^\s+repository: ", s, re.M)]
    assert len(api) == 1 and len(own) == 1, "one checkout must name a repository and one must not"
    return own[0], api[0]


def _path(step: str) -> str:
    found = re.search(r"^\s+path: (\S+)$", step, re.M)
    assert found, f"the checkout has no `path:`:\n{step}"
    return found.group(1)


def test_ci_runs_on_every_pull_request_and_every_push_to_main():
    head = CI.read_text().split("\njobs:\n", 1)[0]
    assert re.search(r"^on:\n  pull_request:\n  push:\n    branches: \[main\]$", head, re.M), (
        "ci.yml's `on:` is not `pull_request` plus `push` to `main`, so a change may not be checked when proposed"
    )


def test_the_job_checks_out_this_repository_and_linkling_api_at_its_trunk_into_separate_workspace_paths():
    own, api = _own_and_api_checkout()
    assert re.search(r"^\s+repository: jpslav/linkling-api$", api, re.M), "the second checkout is not linkling-api"
    assert re.search(r"^\s+ref: main$", api, re.M), "the linkling-api checkout does not name its trunk"
    paths = [_path(own), _path(api)]
    assert paths[0] != paths[1], f"both checkouts write to {paths[0]!r}"
    for path in paths:
        # A checkout refuses a path outside the workspace, and `.` would put one inside the other.
        assert not path.startswith(("/", "..", ".")), f"path {path!r} is not a named directory inside the workspace"


def test_neither_checkout_passes_a_token_or_key_or_persists_the_actions_own_token():
    for step in _own_and_api_checkout():
        assert not re.search(r"^\s+(?:token|ssh-key|ssh-known-hosts|ssh-user):", step, re.M), (
            f"a checkout passes a `token:` or an SSH key input; linkling-api is public and needs neither:\n{step}"
        )
        assert re.search(r"^\s+persist-credentials: false$", step, re.M), (
            f"a checkout leaves the action's token configured in its `.git`:\n{step}"
        )
    workflows = sorted(WORKFLOWS.glob("*.y*ml"))
    assert CI in workflows, "the walk found no ci.yml"
    for workflow in workflows:
        assert not re.search(r"\bsecrets\b", _code(workflow.read_text())), f"{workflow.name} refers to secrets"
        assert "DEPLOY_KEY" not in workflow.read_text(), f"{workflow.name} names a deploy key"


def test_the_check_runs_from_the_linkling_api_checkout_against_this_repositorys_after_both_checkouts():
    steps = _steps()
    own, api = _own_and_api_checkout()
    own_path, api_path = _path(own), _path(api)
    runs = [
        i
        for i, s in enumerate(steps)
        if re.search(
            rf'^\s+run: LINKLING_WEB_DIR="\$GITHUB_WORKSPACE/{re.escape(own_path)}" {re.escape(api_path)}/scripts/no-third-party-check\.sh$',
            s,
            re.M,
        )
    ]
    assert len(runs) == 1, (
        f"{len(runs)} steps run the check from {api_path!r} against {own_path!r}, the checkouts' paths, not one"
    )
    assert runs[0] > max(steps.index(own), steps.index(api)), "the check runs before both checkouts are made"
    assert "--api-only" not in steps[runs[0]], "the check is --api-only, which skips the site"
    others = [s for i, s in enumerate(steps) if i != runs[0] and "no-third-party-check.sh" in _code(s)]
    assert not others, f"a second step names the check, which would need its own test: {others}"


def test_nothing_in_the_site_job_can_turn_a_step_into_a_no_op():
    # An `if:` that is false, `continue-on-error`, or a `working-directory` that moves the check would
    # leave the job green with the site unchecked. None of them is in the job today, so a later one has
    # to be argued for here.
    found = re.findall(r"^\s+(?:if|continue-on-error|working-directory):.*$", _job("no-third-party-site"), re.M)
    assert not found, f"the site job carries {found}, which can make a step, or the job, a green no-op"


def test_no_job_runs_on_a_moving_alias():
    jobs = re.findall(r"^  ([A-Za-z0-9_-]+):\n", CI.read_text().split("\njobs:\n", 1)[1], re.M)
    # The population is fixed: these three exist, so a walk that found fewer read nothing.
    assert {"test", "image-privacy", "no-third-party-site"} <= set(jobs), f"the walk found the jobs {jobs}"
    runners = [
        (workflow.name, m.group(1))
        for workflow in sorted(WORKFLOWS.glob("*.y*ml"))
        for m in re.finditer(r"^\s*(?:- )?runs-on:\s*(.*?)\s*(?:#.*)?$", _code(workflow.read_text()), re.M)
    ]
    assert len(runners) >= 3, f"found {len(runners)} `runs-on:` lines for at least three jobs: {runners}"
    aliases = [r for r in runners if "latest" in r[1].lower()]
    assert not aliases, f"these jobs run on an alias that moves on GitHub's schedule, not a named image: {aliases}"
