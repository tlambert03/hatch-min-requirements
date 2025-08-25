"""Tests for patch_pyproject with various TOML formatting styles.

This test specifically addresses issue #5 about incompatibility with pyproject-fmt.
"""
from pathlib import Path

from hatch_min_requirements import patch_pyproject


def test_patch_pyproject_preserves_formatting_and_entries(tmp_path: Path) -> None:
    """Test that patch_pyproject preserves existing optional dependencies and formatting."""
    # Test case that would be formatted by pyproject-fmt or similar tools
    pyproject_content = """\
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "myproject"
version = "0.1.0"
description = "My project"
dependencies = ["requests>=2.0.0", "numpy"]

[project.optional-dependencies]
test = ["pytest", "pytest-cov"]
dev = ["black", "mypy", "ruff"]
lint = ["pre-commit"]

[tool.hatch.version]
source = "vcs"
"""

    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml_BAK = tmp_path / "pyproject.toml.BAK"
    pyproject_toml.write_text(pyproject_content)

    patch_pyproject(pyproject_toml)
    
    # Check that backup was created
    assert pyproject_toml_BAK.exists()
    assert pyproject_toml_BAK.read_text() == pyproject_content
    
    result_content = pyproject_toml.read_text()
    
    # Verify that existing optional dependencies are preserved
    assert "test = [" in result_content
    assert "pytest" in result_content
    assert "dev = [" in result_content
    assert "black" in result_content
    assert "lint = [" in result_content
    assert "pre-commit" in result_content
    
    # Verify that min-reqs was added
    assert "min-reqs = [" in result_content
    assert "requests==2.0.0" in result_content
    assert "numpy==1.3.0" in result_content
    
    # Verify that other sections are preserved
    assert "[tool.hatch.version]" in result_content
    assert 'source = "vcs"' in result_content


def test_patch_pyproject_multiline_formatting(tmp_path: Path) -> None:
    """Test with multiline array formatting (common with pyproject-fmt)."""
    pyproject_content = """\
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "myproject"
version = "0.1.0"
dependencies = [
    "requests>=2.0.0",
    "numpy",
]

[project.optional-dependencies]
test = [
    "pytest",
    "pytest-cov",
    "coverage",
]
dev = [
    "black",
    "mypy",
    "ruff",
]
"""

    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(pyproject_content)

    patch_pyproject(pyproject_toml)
    
    result_content = pyproject_toml.read_text()
    
    # Verify all existing entries are preserved
    assert "pytest" in result_content
    assert "pytest-cov" in result_content
    assert "coverage" in result_content
    assert "black" in result_content
    assert "mypy" in result_content
    assert "ruff" in result_content
    
    # Verify min-reqs was added
    assert "min-reqs" in result_content
    assert "requests==2.0.0" in result_content
    assert "numpy==1.3.0" in result_content


def test_patch_pyproject_no_existing_optional_deps(tmp_path: Path) -> None:
    """Test when no [project.optional-dependencies] section exists."""
    pyproject_content = """\
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "myproject"
version = "0.1.0"
description = "My project"
dependencies = ["requests>=2.0.0", "numpy"]

[tool.hatch.version]
source = "vcs"
"""

    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(pyproject_content)

    patch_pyproject(pyproject_toml)
    
    result_content = pyproject_toml.read_text()
    
    # Verify that optional-dependencies section was added
    assert "[project.optional-dependencies]" in result_content
    assert "min-reqs = [" in result_content
    assert "requests==2.0.0" in result_content
    assert "numpy==1.3.0" in result_content
    
    # Verify other sections preserved
    assert "[tool.hatch.version]" in result_content