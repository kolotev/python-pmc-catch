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
    return catch_ctx


def test_as_ctx(pmc_catch):
    catch_ctx1 = catch_ctx(pmc_catch, e)
    assert catch_ctx1.exception == e
    catch_ctx3 = catch_ctx(pmc_catch, w)
    assert catch_ctx3.exception == w


def test_counts(pmc_catch):  # local & global

    catch_ctx1 = catch_ctx(pmc_catch, e)
    assert catch_ctx1.counts() == (1, 0)

    catch_ctx2 = catch_ctx(pmc_catch, e_)
    assert catch_ctx2.counts() == (1, 0)

    catch_ctx3 = catch_ctx(pmc_catch, w)
    assert catch_ctx3.counts() == (0, 1)

    assert pmc_catch.counts() == (2, 1)
    assert pmc_catch.errors_count() == 2
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


def test_argument_on_errors_raise_click_exit__no_raised_error(pmc_catch):
    with pmc_catch(on_errors_raise_click_exit=True):
        pass


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


def test_argument_on_errors_raise_sys_exit(pmc_catch):
    with pytest.raises(SystemExit) as py_ctx:
        with pmc_catch(on_errors_raise_sys_exit=True):
            raise Exception("Time to exit")

    assert py_ctx.value.code == -1


def test_argument_on_errors_raise_click_exit(pmc_catch):
    with pytest.raises(click.exceptions.Exit) as py_ctx:
        with pmc_catch(on_errors_raise_click_exit=True):
            raise Exception("Time to exit")

    assert isinstance(py_ctx.value, click.exceptions.Exit)
    assert py_ctx.value.exit_code == -1


class ExitCodeException(Exception):
    exit_code = -3


def test_exit_code(pmc_catch, caplog):
    # exception argument exit_code
    with pytest.raises(SystemExit) as py_ctx:
        with pmc_catch(on_errors_raise_sys_exit=True):
            raise SystemExit(-2)
    assert py_ctx.value.code == -2

    # custom exception with property exit_code
    with pytest.raises(SystemExit) as py_ctx:
        with pmc_catch(on_errors_raise_sys_exit=True):
            raise ExitCodeException("exit_code exception")
    assert py_ctx.value.code == -3


def test_argument_with_exit_code(pmc_catch):
    _e = SystemExit("With exit_code", -2)
    with pytest.raises(SystemExit) as py_ctx:
        with pmc_catch() as catch_ctx:
            raise _e
    assert catch_ctx.exception == _e
    assert py_ctx.value == _e


def test_argument_with_bad_exit_code(pmc_catch):
    _e = SystemExit(-5)
    with pytest.raises(SystemExit) as py_ctx:
        with pmc_catch() as catch_ctx:
            raise _e
    assert catch_ctx.exception == _e
    assert py_ctx.value == _e
    assert py_ctx.value.code == -5


def test_keyboard_interrupt(pmc_catch, caplog):
    with caplog.at_level(logging.FATAL):
        with pytest.raises(click.exceptions.Abort):
            with pmc_catch():
                raise KeyboardInterrupt()
    assert ("Keyboard interrupt was received" in caplog.messages[-1]) is True


def test_argument_on_error_exit_msg(pmc_catch, caplog):
    # in decorator form
    exit_msg = "Exit message"

    @pmc_catch(on_errors_raise_sys_exit=True, on_error_exit_msg=exit_msg)
    def func():
        raise Exception("Time to exit")

    with caplog.at_level(logging.WARNING):
        with pytest.raises(SystemExit) as py_ctx:
            func()

    assert caplog.messages[-1] == exit_msg
    assert py_ctx.value.code == -1


def test_argument_report_error_counts(pmc_catch, caplog):
    with caplog.at_level(logging.INFO):
        with pytest.raises(SystemExit):
            with pmc_catch(on_errors_raise_sys_exit=True, report_error_counts=True):
                with pmc_catch(report_error_counts=True):
                    with pmc_catch():
                        raise e
                    with pmc_catch(report_error_counts=True):
                        raise e
                    assert caplog.messages[-2] == "encountered 1 error in the current context."
                assert caplog.messages[-2] == "encountered 0 errors in the current context."
                assert caplog.messages[-1] == "encountered 2 total errors."

                with pmc_catch():
                    raise w

                with pmc_catch(report_error_counts=True):
                    raise e
                assert caplog.messages[-2] == "encountered 1 error in the current context."

    assert len(caplog.messages) == 12  # 3(errors) + 1(warning) + 4(count reports) *2
    assert caplog.messages[-2] == "encountered 0 errors in the current context."
    assert caplog.messages[-1] == "encountered 3 total errors."
