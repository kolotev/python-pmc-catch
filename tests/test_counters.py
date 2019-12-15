from pmc.catch import counters


def test_counts():

    c = counters.ExceptionCounter()
    assert c.counts() == (0, 0)
