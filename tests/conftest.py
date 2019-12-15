import pytest
import pmc.catch


@pytest.fixture(scope="function")
def pmc_catch():
    # provide the fixture value
    yield pmc.catch.catch
    # reset global counters
    pmc.catch.counters.ExceptionCounterGlobal().reset()
