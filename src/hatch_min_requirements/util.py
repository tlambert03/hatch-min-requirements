"""Functions for determining the minimum compatible constrained version of a package."""

from __future__ import annotations

import operator
import os
import re
from contextlib import suppress
from typing import TYPE_CHECKING, Callable

from packaging.version import Version as PackagingVersion
from packaging.version import parse as parse_version

from ._fetch import fetch_available_versions

if TYPE_CHECKING:
    from typing import Literal, Sequence, TypeAlias

    # version_cmp   = wsp* <'<=' | '<' | '!=' | '==' | '>=' | '>' | '~=' | '==='>
    VersionCmp: TypeAlias = Literal["<=", "<", "!=", "==", ">=", ">", "~=", "==="]
    # version       = wsp* <( letterOrDigit | '-' | '_' | '.' | '*' | '+' | '!' )+>
    VersionStr: TypeAlias = str
    # version_one   = version_cmp:op version:v wsp* -> (op, v)
    VersionConstraint = tuple[VersionCmp, VersionStr]
    VersionOp = Callable[[PackagingVersion, PackagingVersion], bool]


__all__ = ["sub_min_compatible_version"]


# >>> version_specifier_pattern.findall('~= 0.9, >= 1.0, ===asdfds, <    2.0')
# [('~=', '0.9'), ('>=', '1.0'), ('===', 'asdfds'), ('<', '2.0')]
version_specifier_pattern = re.compile(
    r"""
    (~=|===?|!=|<=?|>=?)  # Comparison operator, captured in a group
    \s*                   # Optional whitespace
    ([^,]*?)              # version string: Non-greedy match for any non-comma character
    (?=                   # Positive lookahead for comma or end of string
        ,\s*              # Comma followed by optional whitespace
        |                 # OR
        $                 # End of string
    )
    """,
    re.VERBOSE,
)


def version_is_compatible(a: PackagingVersion, b: PackagingVersion) -> bool:
    """Return True if package version `a` ~= `b`.

    https://peps.python.org/pep-0440/#compatible-release

    Where ~= is the compatible release operator:
     - ~= x.y        <==>   >= X.Y, == X.*
     - ~= x.y.z      <==>   >= X.Y.Z, == X.Y.*
     - ~= 2.2.post3  <==>   >= 2.2.post3, == 2.*
     - ~= 1.4.5.0    <==>   >= 1.4.5.0, == 1.4.5.*

    """
    # Check if the epoch values match, since different epochs are always incompatible
    if a.epoch != b.epoch:
        return False

    # The ~= operator MUST NOT be used with a single segment version number such as ~=1.
    if len(b.release) < 2:
        raise ValueError(
            "The version for comparison must have at least two segments "
            "(e.g., 1.0, not just 1)"
        )

    # Build the minimum release tuple for compatibility (ignoring pre/post/dev segments)
    # e.g., (1, 2, 0) for 1.2, (1, 2, 3) for 1.2.3
    min_compat_release = b.release[:2] + (0,) * (len(a.release) - 2)

    # Check if `x` is greater than or equal to the minimum compatible version
    # and if `x` starts with the same prefix as `v` for the significant segments
    is_greater_or_equal = a.release >= min_compat_release
    is_same_prefix = a.release[: len(b.release) - 1] == b.release[: len(b.release) - 1]

    return bool(is_greater_or_equal and is_same_prefix)


# Mapping of pep440 version comparison operators to their corresponding functions
# https://peps.python.org/pep-0440/#version-specifiers
COMP_OPS: dict[str, Callable[[PackagingVersion, PackagingVersion], bool]] = {
    "<=": operator.le,
    "<": operator.lt,
    "!=": operator.ne,
    "==": operator.eq,
    ">=": operator.ge,
    ">": operator.gt,
    "~=": version_is_compatible,
    "===": operator.eq,
}


def _min_compatible_version(
    available_versions: Sequence[PackagingVersion],
    constraints: Sequence[VersionConstraint] | None = None,
) -> PackagingVersion:
    """Return the minimum version that satisfies the provided constraints.

    If no constraints are provided, the minimum version is the lowest available version.

    Parameters
    ----------
    available_versions : Sequence[PackagingVersion]
        A sequence of `packaging.version.Version` objects.
    constraints : Sequence[VersionConstraint], optional
        A sequence of version constraint tuples to satisfy, e.g. `[(">=", "1.20")]`.

    Returns
    -------
    PackagingVersion
        The minimum version that satisfies the constraints.

    Examples
    --------
    >>> min_compatible_version([Version("1.3.0"), Version("1.20.1")])
    <Version('1.3.0')>
    >>> min_compatible_version([Version("1.3.0"), Version("1.20.1")], [('>=', '1.5.0')])
    <Version('1.20.1')>

    """
    if not constraints:
        return min(available_versions)

    constraint_ops: list[tuple[VersionOp, PackagingVersion]] = [
        (COMP_OPS[op], parse_version(v)) for op, v in constraints
    ]

    def satisfies_all_constraints(x: PackagingVersion) -> bool:
        return all(op(x, v) for op, v in constraint_ops)

    try:
        min_ver = min(x for x in available_versions if satisfies_all_constraints(x))
    except ValueError:
        raise ValueError(
            f"No available version satisfies the constraints: {constraints}"
        ) from None
    return min_ver


def fetch_min_compatible_version(
    package: str, constraints: Sequence[VersionConstraint] | None = None
) -> str:
    """Fetch minimum version of `package` that satisfies `constraints`.

    This requires network access to fetch the available versions.

    Parameters
    ----------
    package : str
        The name of the package.
    constraints : Sequence[VersionConstraint], optional
        A sequence of version constraints to satisfy, e.g. `[(">=", "1.20")]`.
        By default, `None`.

    Returns
    -------
    str
        The minimum version of the package that satisfies the constraints.

    Examples
    --------
    >>> fetch_min_compatible_version('numpy')
    '1.3.0'
    >>> fetch_min_compatible_version("numpy", [(">=", "1.20")])
    '1.20.0'
    >>> fetch_min_compatible_version("numpy", [(">", "1.20")])
    '1.20.1'
    >>> fetch_min_compatible_version("numpy", [("<", "1.20")])
    '1.3.0'
    >>> fetch_min_compatible_version("numpy", [("<", "1.20"), ("!=", "1.3")])
    '1.4.1'
    """
    available: list[PackagingVersion] = []
    for v in fetch_available_versions(package):
        with suppress(ValueError):  # TODO: warn if we can't parse?
            available.append(parse_version(v))
    if not available:
        raise ValueError(f"No available versions found for package {package!r}")
    return str(_min_compatible_version(available, constraints))


def min_compatible_version_offline(
    constraints: Sequence[VersionConstraint],
) -> str | None:
    """Return the minimum version that satisfies `constraints` without the internet.

    If we don't have internet access, we can't fetch the available versions, and so
    we have to make some assumptions about the available versions in cases with
    non-inclusive lower bounds.
    """
    if not constraints:
        return None

    min_version: PackagingVersion | None = None
    for op, version in constraints:
        # if we find a hard equality constraint, we can return it immediately
        if op in {"==", "==="}:
            return version
        # if we find an inclusive lower bound, check if it's lower than the current min
        if op in {">=", "~="}:
            try:
                v = parse_version(version)
            except ValueError:
                continue
            # if we haven't seen any lower bounds yet, or if this lower bound is greater
            # than the current min, update the min
            if min_version is None or v > min_version:
                min_version = v

        # the remaining possible ops are {"<", "<=", ">", "!="}:
        # with upper-bounds, non-inclusive lower bounds, and exclusions,
        # we can't make any assumptions about the minimum version

    return None if min_version is None else str(min_version)


# ###########################################################################
# This is the primary function in this module
# ###########################################################################

OFFLINE = os.getenv("MIN_REQS_OFFLINE") in {"1", "true", "True", "yes", "Yes"}


def sub_min_compatible_version(spec: str, offline: bool = OFFLINE) -> str:
    """Replace the version in a dependency specifier with the min compatible version.

    Parameters
    ----------
    spec : str
        A PEP 440 compliant dependency specifier. Such as:
        - "package-name"
        - "package-name>=1.20"
        - "package-name[extra1,extra2]>=1.20,<2.0"
        - "package-name[extra1,extra2]>=1.20,<2.0 ; python_version == '3.6'"
    offline : bool, optional
        If True, the function will not fetch available versions from the internet.
        By default, False.

    Returns
    -------
    str
        A PEP 440 compliant dependency specifier pinned to the minimum
        version that satisfies the constraints in the original specifier.

    Examples
    --------
    These examples would require internet access to fetch the available versions.

    >>> sub_min_compatible_version("numpy")
    'numpy==1.3.0'
    >>> sub_min_compatible_version("numpy>1.3")
    'numpy==1.4.1'
    >>> sub_min_compatible_version("numpy[extra1,extra2]>=1.20,<2.0")
    'numpy[extra1,extra2]==1.20.0'
    >>> sub_min_compatible_version("numpy[extra]<2; python_version == '3.6'")
    "numpy[extra]==1.3.0 ; python_version == '3.6'"
    """
    # Break on semi-colon to separate markers from the name and version spec
    name_spec, *markers = spec.partition(";")

    # Find all version constraints in the first part
    constraints: list[VersionConstraint] = []
    str_idx = None  # index of the first version specifier in the name_spec
    for match in version_specifier_pattern.finditer(name_spec):
        if not str_idx:  # Save the index of the first version specifier
            str_idx = match.start()
        constraints.append(match.groups())  # type: ignore

    # split the name from the extras and version spec
    name_and_extra = name_spec[:str_idx]

    if offline:
        if (min_compat := min_compatible_version_offline(constraints)) is None:
            # if we can't determine a minimum version, just return the original spec
            return spec
        min_compat = min_compat
    else:
        # solve the min version compatible with the constraints, uses the internet
        name = name_and_extra.split("[", 1)[0]
        min_compat = fetch_min_compatible_version(name, constraints)

    return f"{name_and_extra}=={min_compat}{''.join(markers)}"
