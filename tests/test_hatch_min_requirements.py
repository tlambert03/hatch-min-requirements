import pytest

from hatch_min_requirements.util import sub_min_compatible_version
from hatch_min_requirements import _fetch

MIN_NUMPY = "1.3.0"
# these may change if the min versions change upstream
PARAMS = [
    ("numpy", f"numpy=={MIN_NUMPY}", "numpy"),
    ("numpy!=1.3.6", f"numpy=={MIN_NUMPY}", "numpy!=1.3.6"),
    ("numpy!=1.3.0", "numpy==1.4.1", "numpy!=1.3.0"),
    ("numpy~=1.7", "numpy==1.7.0", "numpy==1.7"),
    ("numpy===1.7", "numpy==1.7.0", "numpy==1.7"),  # current behavior, perhaps weird
    ("numpy>=1.5.0", "numpy==1.5.0", "numpy==1.5.0"),
    ("numpy >=1.5.0", "numpy ==1.5.0", "numpy ==1.5.0"),
    ("numpy[extra]", f"numpy[extra]=={MIN_NUMPY}", "numpy[extra]"),
    ("numpy>1.3", "numpy==1.4.1", "numpy>1.3"),
    ("numpy[extra]>1.3", "numpy[extra]==1.4.1", "numpy[extra]>1.3"),
    (
        "numpy[extra]>1.3; python_version=='3.7'",
        "numpy[extra]==1.4.1; python_version=='3.7'",
        "numpy[extra]>1.3; python_version=='3.7'",
    ),
]


@pytest.mark.parametrize("offline", [True, False])
@pytest.mark.parametrize("package, online_expectation, offline_expectation", PARAMS)
def test_sub_min_compatible_version(
    package: str, online_expectation: str, offline_expectation: str, offline: bool
) -> None:
    expectation = offline_expectation if offline else online_expectation
    assert sub_min_compatible_version(package, offline=offline) == expectation


def test_pin_unconstrained() -> None:
    assert (
        sub_min_compatible_version("numpy", offline=False, pin_unconstrained=True)
        == f"numpy=={MIN_NUMPY}"
    )
    assert (
        sub_min_compatible_version("numpy", offline=False, pin_unconstrained=False) == "numpy"
    )
    assert (
        sub_min_compatible_version("numpy", offline=True, pin_unconstrained=False) == "numpy"
    )
    assert (
        sub_min_compatible_version("numpy", offline=True, pin_unconstrained=True) == "numpy"
    )


@pytest.mark.parametrize("use_pip", [True, False])
def test_fetch_versions(use_pip: bool, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_fetch, "TRY_PIP", use_pip)

    _fetch.fetch_available_versions.cache_clear()
    available = _fetch.fetch_available_versions("numpy")
    assert available[-1] == MIN_NUMPY
    assert available[-4:] == ["1.5.1", "1.5.0", "1.4.1", "1.3.0"]
