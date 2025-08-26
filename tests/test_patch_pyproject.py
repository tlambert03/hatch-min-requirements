from pathlib import Path

from hatch_min_requirements import patch_pyproject

PYPROJECT = """\
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "myproject"
version = "0.1.0"
description = "My project"
dependencies = ["requests>=2.0.0", "numpy"]
"""

MIN_REQS = """
[project.optional-dependencies]
min-reqs = ["requests==2.0.0", "numpy==1.3.0"]
"""


def test_patch_pyproject(tmp_path: Path) -> None:
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml_BAK = tmp_path / "pyproject.toml.BAK"
    pyproject_toml.write_text(PYPROJECT)

    patch_pyproject(pyproject_toml)
    assert pyproject_toml_BAK.exists()
    assert pyproject_toml_BAK.read_text() == PYPROJECT
    assert pyproject_toml.read_text() == PYPROJECT + MIN_REQS
