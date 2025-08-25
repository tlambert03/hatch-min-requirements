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
        min_reqs = [sub_min_compatible_version(dep) for dep in metadata["dependencies"]]
        metadata["optional-dependencies"][MIN_REQS_EXTRA] = min_reqs


@hookimpl  # type: ignore
def hatch_register_metadata_hook() -> type[MetadataHookInterface]:
    return MinRequirementsMetadataHook


def patch_pyproject(
    path: str | Path = "pyproject.toml", extra_name: str = MIN_REQS_EXTRA, tab: str = " " * 4
) -> None:
    """Modify pyproject.toml to add min-reqs optional-dependency using proper TOML library.

    The pyproject.toml file is modified in place, with a backup created as
    "pyproject.toml.BAK". Uses tomlkit for proper TOML parsing and writing to preserve
    formatting and existing structure.

    Parameters
    ----------
    path : str or Path
        Path to the pyproject.toml file.
    extra_name : str, optional
        Name of the extra to add to the optional-dependencies table, by default
        'min-reqs'. Can be set with the MIN_REQS_EXTRA_NAME environment variable.
    tab : str, optional
        String to use for indentation, by default four spaces.
    """
    # Try to import tomlkit first, fall back to tomllib for reading
    try:
        import tomlkit
    except ImportError:
        tomlkit = None

    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore
        except ImportError as e:
            raise ImportError("patch_pyproject requires tomllib/tomli or tomlkit") from e

    # Read the original content
    with open(path) as f:
        pyproject_text = f.read()

    # Parse to get dependencies
    pyproject_data = tomllib.loads(pyproject_text)
    project = pyproject_data.get("project", {})
    deps = project.get("dependencies", [])
    if not deps:
        return

    min_reqs = [sub_min_compatible_version(dep) for dep in deps]

    # Create backup
    with open(Path(path).with_suffix(".toml.BAK"), "w") as f:
        f.write(pyproject_text)

    if tomlkit is not None:
        # Use tomlkit for proper TOML manipulation that preserves formatting
        doc = tomlkit.parse(pyproject_text)
        
        # Ensure project section exists
        if "project" not in doc:
            doc["project"] = tomlkit.table()
        
        # Ensure optional-dependencies subsection exists
        if "optional-dependencies" not in doc["project"]:
            doc["project"]["optional-dependencies"] = tomlkit.table()
        
        # Add the min-reqs entry (this will preserve existing entries)
        doc["project"]["optional-dependencies"][extra_name] = min_reqs
        
        # Write back with preserved formatting
        with open(path, "w") as f:
            f.write(tomlkit.dumps(doc))
    else:
        # Fallback to more robust string manipulation if tomlkit not available
        _patch_pyproject_fallback(path, pyproject_text, min_reqs, extra_name, tab)


def _patch_pyproject_fallback(
    path: str | Path, pyproject_text: str, min_reqs: list[str], extra_name: str, tab: str
) -> None:
    """Fallback implementation for when tomlkit is not available."""
    import re
    
    # Check if [project.optional-dependencies] exists
    opt_deps_pattern = r'(\[project\.optional-dependencies\])'
    opt_deps_match = re.search(opt_deps_pattern, pyproject_text)
    
    # Create the min-reqs entry
    min_reqs_lines = [f'{extra_name} = [']
    for dep in min_reqs:
        min_reqs_lines.append(f'{tab}"{dep}",')
    min_reqs_lines.append(']')
    min_reqs_text = '\n'.join(min_reqs_lines)
    
    if opt_deps_match:
        # Find insertion point - look for next section or end of file
        start_pos = opt_deps_match.end()
        
        # Look for the next section
        next_section_pattern = r'\n\[[^\]]+\]'
        rest_of_file = pyproject_text[start_pos:]
        next_section_match = re.search(next_section_pattern, rest_of_file)
        
        if next_section_match:
            # Insert before the next section
            insert_pos = start_pos + next_section_match.start()
            modified_pyproject_text = (pyproject_text[:insert_pos] + 
                                     '\n' + min_reqs_text + 
                                     pyproject_text[insert_pos:])
        else:
            # Append to the end of the file
            modified_pyproject_text = pyproject_text.rstrip() + '\n' + min_reqs_text + '\n'
    else:
        # Add the entire section
        section_text = f'\n[project.optional-dependencies]\n{min_reqs_text}\n'
        modified_pyproject_text = pyproject_text.rstrip() + section_text
    
    # Write the modified content
    with open(path, "w") as f:
        f.write(modified_pyproject_text)
