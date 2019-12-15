# @pytest.mark.xfail(raises=IndexError)
from unittest import mock
import logging
import pytest
import click

e = Exception("Just an exception")
e_ = Exception("Just another error")
w = Warning("Just a warning")


def catch_ctx(catch, e):
    with catch() as catch_ctx:
        raise e
    return catch_ctx, e


def test_as_ctx(pmc_catch):
    catch_ctx1, e1 = catch_ctx(pmc_catch, e)
    assert catch_ctx1.exception == e1


def test_counts(pmc_catch):  # local & global

    catch_ctx1, e1 = catch_ctx(pmc_catch, e)
    assert catch_ctx1.counts() == (1, 0)
    assert catch_ctx1.exception == e1
    assert pmc_catch.counts() == (1, 0)
    assert pmc_catch.errors_count() == 1

    catch_ctx2, e2 = catch_ctx(pmc_catch, e_)
    assert catch_ctx2.counts() == (1, 0)
    assert catch_ctx2.exception == e2
    assert pmc_catch.counts() == (2, 0)
    assert pmc_catch.errors_count() == 2

    catch_ctx3, w3 = catch_ctx(pmc_catch, w)
    assert catch_ctx3.exception == w
    assert pmc_catch.counts() == (2, 1)
    assert pmc_catch.warnings_count() == 1


def test_decorator(pmc_catch):
    @pmc_catch
    def func_1001():
        return 1001

    @pmc_catch
    def func_err():
        raise e

    @pmc_catch
    def func_warn():
        raise w

    _1001 = func_1001()
    assert pmc_catch.counts() == (0, 0)
    assert func_1001.context.exception is None
    assert _1001 == 1001

    func_err()
    assert pmc_catch.counts() == (1, 0)
    assert func_err.context.exception == e

    func_warn()
    assert pmc_catch.counts() == (1, 1)
    assert func_warn.context.exception == w


def test_argument_exception_handler__non_callable(pmc_catch):
    # test non callable exception_handler
    with pytest.raises(ValueError):
        pmc_catch(exception_handler=1)


def test_argument_exception_handler__callable(pmc_catch):
    test_value = None

    def exc_handler(exc):
        nonlocal test_value
        test_value = exc

    # callable exception_handler
    @pmc_catch(exception_handler=exc_handler)
    def func():
        raise e

    func()
    assert test_value == e


def test_argument_exception_handler__callable_bad_number_of_args(pmc_catch):
    exc_handler0 = lambda: None  # noqa
    exc_handler2 = lambda arg1, arg2="val2": None  # noqa
    exc_handler3 = lambda arg1, arg2, arg3="val3": None  # noqa

    with pytest.raises(TypeError):
        pmc_catch(exception_handler=exc_handler0)

    with pytest.raises(TypeError):
        pmc_catch(exception_handler=exc_handler2)

    with pytest.raises(TypeError):
        pmc_catch(exception_handler=exc_handler3)


def test_argument_logger(pmc_catch):
    lg = logging.getLogger()

    @pmc_catch(logger=lg)
    def func():
        raise Exception(e)

    with mock.patch.object(lg, "error") as mock_error:
        func()
        mock_error.assert_called_once_with(str(e))


def test_argument_logger__None(pmc_catch):
    @pmc_catch(logger=None)
    def func():
        raise e

    assert func() is None


def test_argument_on_error_exit(pmc_catch):
    with pytest.raises(SystemExit) as py_ctx:
        with pmc_catch(on_errors_exit=True):
            raise Exception("Time to exit", -2)

    assert py_ctx.value.code == -2


def test_argument_on_errors_click_exit(pmc_catch):
    with pytest.raises(click.exceptions.Exit) as py_ctx:
        with pmc_catch(on_errors_click_exit=True):
            raise Exception("Time to exit", -2)

    assert py_ctx.value.exit_code == -2


def test_argument_on_errors_exit_msg(pmc_catch, caplog):
    # in decorator form
    exit_msg = "Exit message"

    @pmc_catch(on_errors_exit=True, on_errors_exit_msg=exit_msg)
    def func():
        raise Exception("Time to exit", -2)

    with caplog.at_level(logging.WARNING):
        with pytest.raises(SystemExit) as py_ctx:
            func()
    assert caplog.messages[-1] == exit_msg
    assert py_ctx.value.code == -2


def test_argument_reraise_warning(pmc_catch):
    @pmc_catch(reraise_warning=True)
    def func_w():
        raise w

    @pmc_catch(reraise_warning=True)
    def func_e():
        raise e

    with pytest.raises(Warning):
        func_w()

    # no interruption on exception `e`, because @pmc_catch is not passing/re-raising them.
    func_e()


def test_argument_reraise_error(pmc_catch):
    @pmc_catch(reraise_error=True)
    def func_w():
        raise w

    @pmc_catch(reraise_error=True)
    def func_e():
        raise e

    with pytest.raises(Exception):
        func_e()

    # no interruption on exception `w` (aka `Warning`),
    # because @pmc_catch is not passing/re-raising them.
    func_w()


class ExitCodeException(Exception):
    exit_code = -3


def test_exit_code(pmc_catch, caplog):
    # exception argument exit_code
    with pytest.raises(SystemExit) as py_ctx:
        with pmc_catch(on_errors_exit=True):
            raise Exception("exit argument exception", -2)
    assert py_ctx.value.code == -2
    # custom exception with property exit_code
    with pytest.raises(SystemExit) as py_ctx:
        with pmc_catch(on_errors_exit=True):
            raise ExitCodeException("exit_code exception")
    assert py_ctx.value.code == -3


def test_keyboard_interrupt(pmc_catch, caplog):
    with caplog.at_level(logging.FATAL):
        with pytest.raises(click.exceptions.Abort):
            with pmc_catch():
                raise KeyboardInterrupt()
    assert ("Keyboard interrupt was received" in caplog.messages[-1]) is True
