"""Guards against the project drifting out of step with itself.

These caught two real problems: __init__.py said 0.1.0 while
pyproject.toml said 0.1.1, and the README told people to run a demo.py
that had never been written.
"""

import os
import re

import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*parts):
    with open(os.path.join(PROJECT_ROOT, *parts), encoding="utf-8-sig") as handle:
        return handle.read()


def test_version_is_declared_in_exactly_one_place_worth_trusting():
    """__init__.py and pyproject.toml must agree, or pip and Python disagree."""
    import atomecon

    pyproject = _read("pyproject.toml")
    match = re.search(r'^version = "([^"]+)"', pyproject, re.M)
    assert match, "no version found in pyproject.toml"

    assert atomecon.__version__ == match.group(1)


def test_demo_script_actually_exists():
    """The README tells people to run it, so it has to be there."""
    assert os.path.isfile(os.path.join(PROJECT_ROOT, "demo.py"))


def test_readme_does_not_promise_files_that_are_missing():
    readme = _read("README.md")
    for referenced in re.findall(r"python (\w+\.py)", readme):
        assert os.path.isfile(os.path.join(PROJECT_ROOT, referenced)), (
            f"README references {referenced}, which does not exist"
        )


def test_readme_documents_the_public_api():
    """Anything exported should be findable by someone reading the docs."""
    import atomecon

    readme = _read("README.md")
    missing = []
    for name in atomecon.__all__:
        if name not in readme:
            missing.append(name)

    assert not missing, f"undocumented in README: {missing}"


def test_changelog_mentions_the_current_version():
    import atomecon

    assert atomecon.__version__ in _read("README.md")
