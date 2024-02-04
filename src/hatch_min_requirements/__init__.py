"""Hatchling plugin to create optional-dependencies pinned to minimum versions"""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("hatch-min-requirements")
except PackageNotFoundError:
    __version__ = "uninstalled"
__author__ = "Talley Lambert"
__email__ = "talley.lambert@example.com"
