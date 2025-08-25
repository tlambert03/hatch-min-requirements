"""Hatchling plugin to create optional-dependencies pinned to minimum versions."""

from __future__ import annotations

import os
from importlib import metadata
from pathlib import Path

from hatchling.metadata.plugin.interface import MetadataHookInterface
from hatchling.plugin import hookimpl

from .util import sub_min_compatible_version

try:
    __version__ = metadata.version("hatch-min-requirements")
except metadata.PackageNotFoundError:  # pragma: no cover
    __version__ = "uninstalled"
__author__ = "Talley Lambert"

__all__ = ["MinRequirementsMetadataHook", "patch_pyproject", "sub_min_compatible_version"]


MIN_REQS_EXTRA = os.getenv("MIN_REQS_EXTRA_NAME", "min-reqs")


class MinRequirementsMetadataHook(MetadataHookInterface):
    """Hatchling metadata hook to populate optional-dependencies from dependencies."""

    PLUGIN_NAME = "min_requirements"

    def update(self, metadata: dict) -> None:
        """Update the project.optional-dependencies metadata."""
        # Get configuration from pyproject.toml, falling back to environment variables
        config = getattr(self, 'config', {})
        
        # Handle 'offline' option
        offline = config.get('offline')
        if offline is None:
            # Fall back to environment variable
            offline = os.getenv("MIN_REQS_OFFLINE") in {"1", "true", "True", "yes", "Yes"}
        
        # Handle 'no_pip' option (inverse of TRY_PIP)
        no_pip = config.get('no_pip')
        if no_pip is None:
            # Fall back to environment variable (note: no_pip is inverse of TRY_PIP)
            try_pip = os.getenv("MIN_REQS_TRY_PIP", "1") in {"1", "true", "True", "yes", "Yes"}
            no_pip = not try_pip
        
        # Handle 'pin_unconstrained' option
        pin_unconstrained = config.get('pin_unconstrained')
        if pin_unconstrained is None:
            # Fall back to environment variable
            pin_unconstrained = os.getenv("MIN_REQS_PIN_UNCONSTRAINED", "1") in {"1", "true", "True", "yes", "Yes"}
        
        # If no_pip is True, we need to set offline to True for the _fetch module
        if no_pip:
            # Temporarily override the TRY_PIP setting for this call
            import sys
            if 'hatch_min_requirements._fetch' in sys.modules:
                original_try_pip = sys.modules['hatch_min_requirements._fetch'].TRY_PIP
                sys.modules['hatch_min_requirements._fetch'].TRY_PIP = False
            else:
                original_try_pip = None
        
        try:
            min_reqs = [
                sub_min_compatible_version(dep, offline=offline, pin_unconstrained=pin_unconstrained) 
                for dep in metadata["dependencies"]
            ]
            # Ensure optional-dependencies exists in metadata
            if "optional-dependencies" not in metadata:
                metadata["optional-dependencies"] = {}
            metadata["optional-dependencies"][MIN_REQS_EXTRA] = min_reqs
        finally:
            # Restore original TRY_PIP setting if we modified it
            if no_pip and original_try_pip is not None:
                import sys
                if 'hatch_min_requirements._fetch' in sys.modules:
                    sys.modules['hatch_min_requirements._fetch'].TRY_PIP = original_try_pip


@hookimpl  # type: ignore
def hatch_register_metadata_hook() -> type[MetadataHookInterface]:
    return MinRequirementsMetadataHook


def patch_pyproject(
    path: str | Path = "pyproject.toml", 
    extra_name: str = MIN_REQS_EXTRA, 
    tab: str = " " * 4,
    offline: bool | None = None,
    no_pip: bool | None = None,
    pin_unconstrained: bool | None = None,
) -> None:
    """Directly modify pyproject.toml to add min-reqs optional-dependency.

    The pyproject.toml file is modified in place, with a backup created as
    "pyproject.toml.BAK".

    Parameters
    ----------
    path : str or Path
        Path to the pyproject.toml file.
    extra_name : str, optional
        Name of the extra to add to the optional-dependencies table, by default
        'min-reqs'. Can be set with the MIN_REQS_EXTRA_NAME environment variable.
    tab : str, optional
        String to use for indentation, by default four spaces.
    offline : bool, optional
        If True, do not connect to PyPI to fetch available versions. If None,
        falls back to environment variable MIN_REQS_OFFLINE.
    no_pip : bool, optional
        If True, do not use pip to fetch available versions. If None,
        falls back to environment variable MIN_REQS_TRY_PIP (inverted).
    pin_unconstrained : bool, optional
        If True, pin unconstrained dependencies to minimum available version.
        If None, falls back to environment variable MIN_REQS_PIN_UNCONSTRAINED.
    """
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore
        except ImportError as e:
            raise ImportError("patch_pyproject requires tomllib or tomli") from e

    with open(path) as f:
        pyproject_text = f.read()
        pyproject_data = tomllib.loads(pyproject_text)

    # get the dependencies and create min-reqs
    project = pyproject_data.get("project", {})
    deps = project.get("dependencies", [])
    if not deps:
        return
    
    # Handle configuration parameters, falling back to environment variables
    if offline is None:
        offline = os.getenv("MIN_REQS_OFFLINE") in {"1", "true", "True", "yes", "Yes"}
    
    if no_pip is None:
        try_pip = os.getenv("MIN_REQS_TRY_PIP", "1") in {"1", "true", "True", "yes", "Yes"}
        no_pip = not try_pip
    
    if pin_unconstrained is None:
        pin_unconstrained = os.getenv("MIN_REQS_PIN_UNCONSTRAINED", "1") in {"1", "true", "True", "yes", "Yes"}
    
    # If no_pip is True, temporarily override TRY_PIP
    if no_pip:
        import sys
        if 'hatch_min_requirements._fetch' in sys.modules:
            original_try_pip = sys.modules['hatch_min_requirements._fetch'].TRY_PIP
            sys.modules['hatch_min_requirements._fetch'].TRY_PIP = False
        else:
            original_try_pip = None
    
    try:
        min_reqs = [
            sub_min_compatible_version(dep, offline=offline, pin_unconstrained=pin_unconstrained) 
            for dep in deps
        ]
    finally:
        # Restore original TRY_PIP setting if we modified it
        if no_pip and original_try_pip is not None:
            import sys
            if 'hatch_min_requirements._fetch' in sys.modules:
                sys.modules['hatch_min_requirements._fetch'].TRY_PIP = original_try_pip

    # modify pyproject.toml text directly
    table_header = "[project.optional-dependencies]"
    min_reqs_text = f"{table_header}\n{extra_name} = [\n"
    for dep in min_reqs:
        min_reqs_text += f'{tab}"{dep}",\n'
    min_reqs_text += "]"

    # either append or add the optional-dependencies table
    if table_header in pyproject_text:
        modified_pyproject_text = pyproject_text.replace(table_header, min_reqs_text, 1)
    else:
        modified_pyproject_text = pyproject_text + "\n" + min_reqs_text + "\n"

    # backup original pyproject.toml
    with open(Path(path).with_suffix(".toml.BAK"), "w") as f:
        f.write(pyproject_text)

    with open(path, "w") as f:
        f.write(modified_pyproject_text)
