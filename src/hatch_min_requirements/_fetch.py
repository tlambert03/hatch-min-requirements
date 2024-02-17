from __future__ import annotations

import os
import re
import urllib.request
from contextlib import suppress
from functools import lru_cache
import warnings
from packaging.version import parse as parse_version
from packaging.version import Version as PackagingVersion

TRY_PIP = os.getenv("MIN_REQS_TRY_PIP", "1") in {"1", "true", "True", "yes", "Yes"}

__all__ = ["fetch_available_versions"]


@lru_cache
def fetch_available_versions(package_name: str) -> list[str]:
    if TRY_PIP:
        with suppress(ImportError):
            import pip  # noqa: F401

            return fetch_available_versions_pip(package_name)

    return fetch_available_versions_std_lib(package_name)


@lru_cache
def fetch_available_versions_pip(package_name: str) -> list[str]:
    """Return a list of available versions for the given `package_name`.

    This uses `pip index versions` to get the available versions, which requires
    pip >= 21.2.

    Parameters
    ----------
    package_name : str
        The name of the package.

    Returns
    -------
    list[str]
        A list of available version strings for the package.
    """
    import subprocess

    try:
        output = subprocess.check_output(
            ["pip", "index", "versions", package_name],
            text=True,
            stderr=subprocess.PIPE,
        )
        avail = output.split("Available versions:")[1].split("\n")[0].strip()
        return avail.split(", ")
    except subprocess.CalledProcessError as e:  # pragma: no cover
        warnings.warn(
            f"Failed to fetch available versions for {package_name}: {e}",
            RuntimeWarning,
            stacklevel=2,
        )
        return []


@lru_cache
def fetch_available_versions_std_lib(package_name: str) -> list[str]:
    """Fetch all versions of a package from the simple PyPI index."""
    url = f"https://pypi.org/simple/{package_name}/"
    try:
        with urllib.request.urlopen(url) as response:
            html = response.read().decode("utf-8")
            versions: set[PackagingVersion] = set()
            for link in re.findall(r">([^>]+)</a>", html):
                with suppress(ValueError):
                    version = parse_version(parse_filename(link)[1])
                    if not version.is_prerelease:
                        versions.add(version)
            return [str(x) for x in sorted(versions, reverse=True)]
    except Exception as e:  # pragma: no cover
        warnings.warn(
            f"Failed to fetch available versions for {package_name}: {e}",
            RuntimeWarning,
            stacklevel=2,
        )
        return []


# ---------- Below vendored from pypi-simple ---------------------
#
# https://github.com/jwodder/pypi-simple
#
# The MIT License (MIT)
#
# Copyright (c) 2018-2024 John Thorvald Wodder II and contributors

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


PROJECT_NAME = r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?"
PROJECT_NAME_NODASH = r"[A-Za-z0-9](?:[A-Za-z0-9._]*[A-Za-z0-9])?"
VERSION = r"[A-Za-z0-9_.!+-]+?"
VERSION_NODASH = r"[A-Za-z0-9_.!+]+?"
ARCHIVE_EXT = r"\.(?:tar|tar\.(?:bz2|gz|lz|lzma|xz|Z)|tbz|tgz|tlz|txz|zip)"
PLAT_NAME = r"(?:aix|cygwin|darwin|linux|macosx|solaris|sunos|[wW]in)[-.A-Za-z0-9_]*"
PYVER = r"py[0-9]+\.[0-9]+"

#: Regexes for package filenames that can be parsed unambiguously
GOOD_PACKAGE_RGXN = [
    # See <https://setuptools.readthedocs.io/en/latest
    #      /formats.html#filename-embedded-metadata>:
    (
        "egg",
        re.compile(
            r"^(?P<project>{})-(?P<version>{})(?:-{}(?:-{})?)?\.egg$".format(
                PROJECT_NAME_NODASH, VERSION_NODASH, PYVER, PLAT_NAME
            )
        ),
    ),
    # See <http://ftp.rpm.org/max-rpm/ch-rpm-file-format.html>:
    # (The architecture pattern is mainly just a guess based on what's
    # currently on PyPI.)
    (
        "rpm",
        re.compile(
            r"^(?P<project>{})-(?P<version>{})-[^-]+\.[A-Za-z0-9._]+\.rpm$".format(
                PROJECT_NAME, VERSION_NODASH
            )
        ),
    ),
    # Regex adapted from <https://github.com/pypa/pip/blob/18.0/src/pip/_internal/wheel.py#L569>:
    (
        "wheel",
        re.compile(
            r"^(?P<project>{})-(?P<version>{})(-[0-9][^-]*?)?" r"-.+?-.+?-.+?\.whl$".format(
                PROJECT_NAME_NODASH, VERSION_NODASH
            )
        ),
    ),
]

#: Partial regexes for package filenames with ambiguous grammars.  If a hint as
#: to the expected project name is given, it will be prepended to the regexes
#: when trying to determine a match; otherwise, a generic pattern that matches
#: all project names will be prepended.
BAD_PACKAGE_BASES = [
    # See <https://github.com/python/cpython/blob/v3.7.0/Lib/distutils/command/bdist_dumb.py#L93>:
    (
        "dumb",
        re.compile(rf"-(?P<version>{VERSION})\.{PLAT_NAME}{ARCHIVE_EXT}$"),
    ),
    # See <https://github.com/python/cpython/blob/v3.7.0/Lib/distutils/command/bdist_msi.py#L733>:
    (
        "msi",
        re.compile(rf"-(?P<version>{VERSION})\.{PLAT_NAME}(?:-{PYVER})?\.msi$"),
    ),
    ("sdist", re.compile(rf"-(?P<version>{VERSION}){ARCHIVE_EXT}$")),
    # See <https://github.com/python/cpython/blob/v3.7.0/Lib/distutils/command/bdist_wininst.py#L292>:
    (
        "wininst",
        re.compile(rf"-(?P<version>{VERSION})\.{PLAT_NAME}(?:-{PYVER})?\.exe$"),
    ),
]

#: Regexes for package filenames with ambiguous grammars, using a generic
#: pattern that matches all project names
BAD_PACKAGE_RGXN = [
    (pkg_type, re.compile("^(?P<project>" + PROJECT_NAME + ")" + rgx.pattern))
    for pkg_type, rgx in BAD_PACKAGE_BASES
]


def parse_filename(filename: str, project_hint: str | None = None) -> tuple[str, str, str]:
    for pkg_type, rgx in GOOD_PACKAGE_RGXN:
        m = rgx.match(filename)
        if m:
            return (m.group("project"), m.group("version"), pkg_type)
    if project_hint is not None:  # pragma: no cover
        proj_rgx = re.sub(r"[^A-Za-z0-9]+", "[-_.]+", project_hint)
        proj_rgx = re.sub(
            r"([A-Za-z])",
            lambda m: "[" + m.group(1).upper() + m.group(1).lower() + "]",
            proj_rgx,
        )
        m = re.match(proj_rgx + r"(?=-)", filename)
        if m:
            project = m.group(0)
            rest_of_name = filename[m.end(0) :]
            for pkg_type, rgx in BAD_PACKAGE_BASES:
                m = rgx.match(rest_of_name)
                if m:
                    return (project, m.group("version"), pkg_type)
    for pkg_type, rgx in BAD_PACKAGE_RGXN:
        m = rgx.match(filename)
        if m:
            return (m.group("project"), m.group("version"), pkg_type)
    raise ValueError(f"Could not parse filename: {filename!r}")  # pragma: no cover
