"""Tests for configuration options in pyproject.toml."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from hatch_min_requirements import patch_pyproject


def test_patch_pyproject_with_offline_option(tmp_path: Path) -> None:
    """Test that patch_pyproject respects offline option."""
    pyproject_content = """\
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "myproject"
version = "0.1.0"
dependencies = ["requests>=2.0.0", "numpy"]
"""
    
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(pyproject_content)
    
    # Test with offline=True
    patch_pyproject(pyproject_toml, offline=True)
    
    result = pyproject_toml.read_text()
    # In offline mode, unconstrained dependencies should remain unchanged
    assert '"numpy",' in result
    # Constrained dependencies should be pinned to the constraint
    assert '"requests==2.0.0",' in result


def test_patch_pyproject_with_no_pip_option(tmp_path: Path) -> None:
    """Test that patch_pyproject respects no_pip option."""
    pyproject_content = """\
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "myproject"
version = "0.1.0"
dependencies = ["requests>=2.0.0", "numpy"]
"""
    
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(pyproject_content)
    
    # Test with no_pip=True (should behave like offline for version fetching)
    patch_pyproject(pyproject_toml, no_pip=True)
    
    result = pyproject_toml.read_text()
    # Should not use pip to fetch versions, so unconstrained deps remain unchanged
    assert '"numpy",' in result
    assert '"requests==2.0.0",' in result


def test_patch_pyproject_with_pin_unconstrained_false(tmp_path: Path) -> None:
    """Test that patch_pyproject respects pin_unconstrained=False."""
    pyproject_content = """\
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "myproject"
version = "0.1.0"
dependencies = ["requests>=2.0.0", "numpy"]
"""
    
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(pyproject_content)
    
    # Test with pin_unconstrained=False
    patch_pyproject(pyproject_toml, pin_unconstrained=False, offline=True)
    
    result = pyproject_toml.read_text()
    # Unconstrained dependencies should remain unchanged
    assert '"numpy",' in result
    # Constrained dependencies should still be pinned
    assert '"requests==2.0.0",' in result


def test_patch_pyproject_falls_back_to_env_vars(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that patch_pyproject falls back to environment variables when options not provided."""
    pyproject_content = """\
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "myproject"
version = "0.1.0"
dependencies = ["requests>=2.0.0", "numpy"]
"""
    
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(pyproject_content)
    
    # Set environment variables
    monkeypatch.setenv("MIN_REQS_OFFLINE", "1")
    monkeypatch.setenv("MIN_REQS_PIN_UNCONSTRAINED", "0")
    
    # Call without explicit options - should use env vars
    patch_pyproject(pyproject_toml)
    
    result = pyproject_toml.read_text()
    # Should behave as if offline=True and pin_unconstrained=False
    assert '"numpy",' in result  # unconstrained, not pinned due to pin_unconstrained=False
    assert '"requests==2.0.0",' in result  # constrained, pinned to minimum


def test_patch_pyproject_explicit_overrides_env_vars(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test that explicit options override environment variables."""
    pyproject_content = """\
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "myproject"  
version = "0.1.0"
dependencies = ["requests>=2.0.0", "numpy"]
"""
    
    pyproject_toml = tmp_path / "pyproject.toml"
    pyproject_toml.write_text(pyproject_content)
    
    # Set environment variables to opposite of what we want
    monkeypatch.setenv("MIN_REQS_OFFLINE", "0")
    monkeypatch.setenv("MIN_REQS_PIN_UNCONSTRAINED", "1")
    
    # Override with explicit options
    patch_pyproject(pyproject_toml, offline=True, pin_unconstrained=False)
    
    result = pyproject_toml.read_text()
    # Should behave according to explicit options, not env vars
    assert '"numpy",' in result  # unconstrained, not pinned
    assert '"requests==2.0.0",' in result  # constrained, pinned to minimum


class MockMetadataHook:
    """Mock metadata hook for testing configuration."""
    
    def __init__(self, config: dict):
        self.config = config


def test_metadata_hook_configuration():
    """Test that metadata hook properly reads configuration."""
    from hatch_min_requirements import MinRequirementsMetadataHook
    
    # Create a hook instance with mock configuration
    hook = MinRequirementsMetadataHook()
    hook.config = {
        'offline': True,
        'no_pip': True,
        'pin_unconstrained': False
    }
    
    # Mock metadata with dependencies
    metadata = {
        'dependencies': ['requests>=2.0.0', 'numpy'],
        'optional-dependencies': {}
    }
    
    # Call update method
    hook.update(metadata)
    
    # Check that min-reqs was added
    assert 'min-reqs' in metadata['optional-dependencies']
    min_reqs = metadata['optional-dependencies']['min-reqs']
    
    # In offline mode with pin_unconstrained=False, 
    # unconstrained deps should remain unchanged
    assert 'numpy' in min_reqs
    # Constrained deps should be pinned to their constraint
    assert 'requests==2.0.0' in min_reqs


def test_metadata_hook_fallback_to_env_vars(monkeypatch: pytest.MonkeyPatch):
    """Test that metadata hook falls back to environment variables."""
    from hatch_min_requirements import MinRequirementsMetadataHook
    
    # Set environment variables
    monkeypatch.setenv("MIN_REQS_OFFLINE", "1")
    monkeypatch.setenv("MIN_REQS_PIN_UNCONSTRAINED", "0")
    
    # Create hook without config
    hook = MinRequirementsMetadataHook()
    
    # Mock metadata with dependencies
    metadata = {
        'dependencies': ['requests>=2.0.0', 'numpy'],
        'optional-dependencies': {}
    }
    
    # Call update method
    hook.update(metadata)
    
    # Check that min-reqs was added and uses env var settings
    assert 'min-reqs' in metadata['optional-dependencies']
    min_reqs = metadata['optional-dependencies']['min-reqs']
    
    # Should behave as if offline=True and pin_unconstrained=False
    assert 'numpy' in min_reqs  # unconstrained, not pinned
    assert 'requests==2.0.0' in min_reqs  # constrained, pinned


def test_metadata_hook_config_overrides_env_vars(monkeypatch: pytest.MonkeyPatch):
    """Test that hook configuration overrides environment variables."""
    from hatch_min_requirements import MinRequirementsMetadataHook
    
    # Set environment variables to opposite of what we want
    monkeypatch.setenv("MIN_REQS_OFFLINE", "0")
    monkeypatch.setenv("MIN_REQS_PIN_UNCONSTRAINED", "1")
    
    # Create hook with explicit config
    hook = MinRequirementsMetadataHook()
    hook.config = {
        'offline': True,
        'pin_unconstrained': False
    }
    
    # Mock metadata with dependencies
    metadata = {
        'dependencies': ['requests>=2.0.0', 'numpy'],
        'optional-dependencies': {}
    }
    
    # Call update method
    hook.update(metadata)
    
    # Check that configuration overrides env vars
    assert 'min-reqs' in metadata['optional-dependencies']
    min_reqs = metadata['optional-dependencies']['min-reqs']
    
    # Should use config values, not env vars
    assert 'numpy' in min_reqs  # unconstrained, not pinned due to config
    assert 'requests==2.0.0' in min_reqs  # constrained, pinned