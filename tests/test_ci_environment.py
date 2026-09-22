import sys
import tomllib
from pathlib import Path


def test_ci_pins_python_312():
    assert sys.version_info[:2] == (3, 12)


def test_pyproject_declares_312():
    data = tomllib.loads(Path(__file__).parent.parent.joinpath("pyproject.toml").read_text())
    assert data["project"]["requires-python"] == ">=3.12"
