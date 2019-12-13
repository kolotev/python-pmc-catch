from pmc.catch import demo_function


def test_demo_function():
    """
    Test ``pmc.catch.demo_function(int)`` functionality.
    """
    assert demo_function(1) == 1
