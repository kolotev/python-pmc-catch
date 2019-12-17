import pytest
import pmc.catch


@pytest.fixture(scope="function")
def pmc_catcher():
    # provide the fixture value
    yield pmc.catch.catcher
    # reset global counters
    pmc.catch.counters.ExceptionCounterGlobal().reset()
