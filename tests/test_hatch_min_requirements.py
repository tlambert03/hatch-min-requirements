import pytest

from hatch_min_requirements.util import sub_min_compatible_version

# these may change if the min versions change upstream
PARAMS = [
    ("numpy", "numpy==1.3.0", "numpy"),
    ("numpy!=1.3.6", "numpy==1.3.0", "numpy!=1.3.6"),
    ("numpy!=1.3.0", "numpy==1.4.1", "numpy!=1.3.0"),
    ("numpy~=1.7", "numpy==1.7.0", "numpy==1.7"),
    ("numpy>=1.5.0", "numpy==1.5.0", "numpy==1.5.0"),
    ("numpy[extra]", "numpy[extra]==1.3.0", "numpy[extra]"),
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
