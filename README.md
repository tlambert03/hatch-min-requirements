# hatch-min-requirements

[![License](https://img.shields.io/pypi/l/hatch-min-requirements.svg?color=green)](https://github.com/tlambert03/hatch-min-requirements/raw/main/LICENSE)
[![PyPI](https://img.shields.io/pypi/v/hatch-min-requirements.svg?color=green)](https://pypi.org/project/hatch-min-requirements)
[![Python
Version](https://img.shields.io/pypi/pyversions/hatch-min-requirements.svg?color=green)](https://python.org)
[![CI](https://github.com/tlambert03/hatch-min-requirements/actions/workflows/ci.yml/badge.svg)](https://github.com/tlambert03/hatch-min-requirements/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/tlambert03/hatch-min-requirements/branch/main/graph/badge.svg)](https://codecov.io/gh/tlambert03/hatch-min-requirements)

*Hatchling plugin to create optional-dependencies pinned to minimum versions*

## Rationale

When creating a library, it is often useful to specify the minimum version of a
dependency that is required.  However, pip's default behavior is to install the
*latest* version of a package that satisfies your requirement.  As a result, if
aren't carefully testing your minimum dependencies, you may inadvertently
introduce changes to your package that are not compatible with the minimum
version you specified.

This plugin will inspect your packages dependencies and dynamically add an extra
(named `min-reqs` by default) to the `project.optional-dependencies` table of
your `pyproject.toml` file.  This extra will contain all of your dependendencies
pinned to their *minimum* version.

This makes it easy to test your package against your minimum stated dependencies
on CI, or to install your package with the minimum dependencies for local
development.

## Usage

In your `pyproject.toml` make the following changes:

- Append `hatch-min-requirements` to `[build-system.requires]`.
- Add a `[tool.hatch.metadata.hooks.min_requirements]` table.

```toml
# pyproject.toml
[build-system]
requires = ["hatchling", "hatch-min-requirements"]
build-backend = "hatchling.build"

[tool.hatch.metadata.hooks.min_requirements]
```

Then, you can **install your package using the `min-reqs` extra** and it will
dynamically use the minimum compatible versions of your dependencies.

```bash
pip install -e .[min-reqs]
```

## Environment variables

Environment variables can be used to configure the behavior.
Described in detail below:

| Variable | Default | Description |
|----------|---------|-------------|
| `MIN_REQS_EXTRA_NAME` | `min-reqs` | The name of the extra to add to `pyproject.toml` |
| `MIN_REQS_PIN_UNCONSTRAINED` | `True` | Pin unconstrained dependencies to minimum available version on PyPI. (e.g. `numpy` -> `numpy==1.3.0`) |
| `MIN_REQS_OFFLINE` | `False` | Do not connect to PyPI to fetch available versions |
| `MIN_REQS_TRY_PIP` | `True` | Use `pip` to fetch available versions in online mode.  Set to `0` to use stdlib tools only |

## Considerations

### Dependencies with no constraints

In cases of dependencies declared without constraints (e.g. `foo`), the plugin
*will* search for the minimum available version of the package from PyPI. The
goal here is to encourage *accurate* requirement pinning. If you want to disable
this behavior and leave unconstrained specifiers as is, you can either set the
`MIN_REQS_PIN_UNCONSTRAINED` environment variable to `0` or `False`, or use
offline mode with `MIN_REQS_OFFLINE=1` (see below).

### Offline Mode

In cases such as upper-bounds (`<X.Y`), non-inclusive lower bounds (`>X.Y`), and
exclusions (`!=X.Y`), it's not possible to declare a minimum version without
fetching available versions from PyPI.  By default, this plugin *will* attempt
to connect to PyPI in order to determine compatible minimum version strings.  If
you want to disable this behavior, you can set the `MIN_REQS_OFFLINE`
environment variable to `1` or `True`.

```bash
MIN_REQS_OFFLINE=1 pip install -e .[min-reqs]
```

In offline mode, no attempt is made to guess the next compatible version of a
package after a non-inclusive lower bound.  Instead, the plugin will simply use
your dependency as stated (meaning you won't be testing lower bounds).  If you
want to test lower bounds without connecting to PyPI, you should pin your
dependencies with *inclusive* lower bounds:

```toml
[project]
dependencies = [
    "foo>=1.2.3"  # will be pinned to "foo==1.2.3"
    "baz~=1.2"    # will be pinned to "baz==1.2"
    "bar>1.2.3"   # will be unchanged
]
```

### Usage of pip vs standard-lib tools

Fetching the available versions of a package is not trivial, and `pip` is the
*de facto* tool for doing so.  If `pip` is available in the build environment,
this plugin will use it to fetch the available versions of a package. But, you
must opt in to this behavior by adding `pip` to your `build-system.requires`

```toml
# pyproject.toml
[build-system]
requires = ["hatchling", "hatch-min-requirements", "pip"]
```

To explicitly opt out of using pip (even if it's available) and use standard library tools only, you can
set the `MIN_REQS_TRY_PIP` environment variable to `0` or `False`.

## TODO

- make the `min-reqs` extra configurable
- add `offline` and `no-pip` options to the `min_requirements` table in
  pyproject
