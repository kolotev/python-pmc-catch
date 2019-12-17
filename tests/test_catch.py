# @pytest.mark.xfail(raises=IndexError)
from unittest import mock
import logging
import pytest
from pmc import catch

e = Exception("Just an exception")
e_ = Exception("Just another error")
w = Warning("Just a warning")


def with_catcher(catcher, e):
    with catcher() as catcher_ctx:
        raise e
    return catcher_ctx


def test_as_ctx(pmc_catcher):
    catcher_ctx1 = with_catcher(pmc_catcher, e)
    assert catcher_ctx1.exception == e
    catcher_ctx3 = with_catcher(pmc_catcher, w)
    assert catcher_ctx3.exception == w


def test_counts(pmc_catcher):  # local & global

    catcher_ctx1 = with_catcher(pmc_catcher, e)
    assert catcher_ctx1.counts() == (1, 0)

    catcher_ctx2 = with_catcher(pmc_catcher, e_)
    assert catcher_ctx2.counts() == (1, 0)

    catcher_ctx3 = with_catcher(pmc_catcher, w)
    assert catcher_ctx3.counts() == (0, 1)

    assert pmc_catcher.counts() == (2, 1)
    assert pmc_catcher.errors_count() == 2
    assert pmc_catcher.warnings_count() == 1


def test_decorator(pmc_catcher):
    @pmc_catcher
    def func_1001():
        return 1001

    @pmc_catcher
    def func_err():
        raise e

    @pmc_catcher
    def func_warn():
        raise w

    _1001 = func_1001()
    assert pmc_catcher.counts() == (0, 0)
    assert func_1001.context.exception is None
    assert _1001 == 1001

    func_err()
    assert pmc_catcher.counts() == (1, 0)
    assert func_err.context.exception == e

    func_warn()
    assert pmc_catcher.counts() == (1, 1)
    assert func_warn.context.exception == w


def test_argument_exception_handler__non_callable(pmc_catcher):
    # test non callable post_handler
    with pytest.raises(ValueError):
        pmc_catcher(post_handler=1)


def test_argument_exception_handler__callable(pmc_catcher):
    test_value = None

    # test callable post_handler as a function
    def exc_handler(exception):
        nonlocal test_value
        test_value = exception

    with pmc_catcher(post_handler=exc_handler):
        raise e
    assert test_value == e

    # test callable post_handler as a method
    class Cls:
        def exc_handler(self, exception):
            nonlocal test_value
            test_value = exception

    with pmc_catcher(post_handler=Cls().exc_handler):
        raise e
    assert test_value == e


def test_argument_exception_handler__callable_bad_number_of_args(pmc_catcher):
    exc_handler0 = lambda: None  # noqa
    exc_handler2 = lambda arg1, arg2="val2": None  # noqa
    exc_handler3 = lambda arg1, arg2, arg3="val3": None  # noqa

    with pytest.raises(TypeError):
        pmc_catcher(post_handler=exc_handler0)

    with pytest.raises(TypeError):
        pmc_catcher(post_handler=exc_handler2)

    with pytest.raises(TypeError):
        pmc_catcher(post_handler=exc_handler3)


def test_argument_logger(pmc_catcher):
    lg = logging.getLogger()

    @pmc_catcher(logger=lg)
    def func():
        raise Exception(e)

    with mock.patch.object(lg, "error") as mock_error:
        func()
        mock_error.assert_called_once_with(str(e))


def test_argument_logger__None(pmc_catcher):
    @pmc_catcher(logger=None)
    def func():
        raise e

    assert func() is None


def test_argument_on_errors_raise(pmc_catcher):
    with pytest.raises(SystemExit) as py_ctx:
        with pmc_catcher(on_errors_raise=SystemExit(-1)):
            raise e

    assert isinstance(py_ctx.value, SystemExit)
    assert py_ctx.value.code == -1


def test_argument_on_errors_raise__no_raised_error(pmc_catcher):
    with pmc_catcher(on_errors_raise=SystemExit(-1)):
        pass


def test_argument_on_errors_raise_nested(pmc_catcher):
    se1 = SystemExit(-1)
    se2 = SystemExit(-2)

    with pytest.raises(SystemExit) as py_ctx:
        with pmc_catcher() as ctx1:
            with pmc_catcher(on_errors_raise=se2) as ctx2:
                raise e
            assert ctx2.exception == e
        assert ctx1.exception == se2
    assert py_ctx.value.code == -2

    with pytest.raises(SystemExit) as py_ctx:
        with pmc_catcher(on_errors_raise=se1) as ctx3:
            with pmc_catcher(on_errors_raise=se2):
                raise e
        assert ctx3.exception == se1
    assert py_ctx.value.code == -1

    with pytest.raises(SystemExit) as py_ctx:
        with pmc_catcher(on_errors_raise=se2) as ctx4:
            with pmc_catcher():
                raise e
        assert ctx4.exception == e
    assert py_ctx.value.code == -2


def test_argument_reraise_error(pmc_catcher):
    @pmc_catcher(reraise=True)
    def func_e():
        raise e

    with pytest.raises(Exception):
        func_e()


def test_argument_reraise_warning(pmc_catcher):
    @pmc_catcher(reraise=True)
    def func_w():
        raise w

    with pytest.raises(Warning):
        func_w()


class ExitCodeException(Exception):
    exit_code = -3


def test_system_exit_with_exit_code(pmc_catcher):
    # exception argument exit_code
    with pytest.raises(SystemExit) as py_ctx:
        with pmc_catcher(on_errors_raise=SystemExit(-2)):
            raise SystemExit(-2)
    assert py_ctx.value.code == -2


def test_custom_exception_with_exit_code(pmc_catcher):
    # custom exception with property exit_code
    with pytest.raises(SystemExit) as py_ctx:
        with pmc_catcher(on_errors_raise=SystemExit(-3)):
            raise ExitCodeException("exit_code exception")
    assert py_ctx.value.code == -3


def test_argument_with_exit_code(pmc_catcher):
    _e = SystemExit("With exit_code", -2)
    with pytest.raises(SystemExit) as py_ctx:
        with pmc_catcher() as catcher_ctx:
            raise _e
    assert catcher_ctx.exception == _e
    assert py_ctx.value == _e


def test_argument_with_bad_exit_code(pmc_catcher):
    _e = SystemExit(-5)
    with pytest.raises(SystemExit) as py_ctx:
        with pmc_catcher() as catcher_ctx:
            raise _e
    assert catcher_ctx.exception == _e
    assert py_ctx.value == _e
    assert py_ctx.value.code == -5


def test_keyboard_interrupt(pmc_catcher, caplog):
    with caplog.at_level(logging.FATAL):
        with pytest.raises(KeyboardInterrupt):
            with pmc_catcher():
                raise KeyboardInterrupt()
    assert ("Keyboard interrupt was received" in caplog.messages[-1]) is True


def test_argument_exit_message_case1(pmc_catcher, caplog):
    # case 1: with SystemExit on error
    exit_msg = "Exit message"

    @pmc_catcher(exit_message=exit_msg, on_errors_raise=SystemExit(-3))
    def func():
        raise e

    with caplog.at_level(logging.INFO):
        with pytest.raises(SystemExit) as py_ctx:
            func()

    assert func.context.exception == e
    assert caplog.messages[-2] == str(e)
    assert caplog.messages[-1] == exit_msg
    assert py_ctx.value.code == -3


def test_argument_exit_message_case2(pmc_catcher, caplog):
    # case 2: without on_errors_raise
    exit_msg = "Exit message"
    with caplog.at_level(logging.INFO):
        with pmc_catcher(exit_message=exit_msg) as catcher_ctx:
            raise e

    assert catcher_ctx.exception == e
    assert caplog.messages[-2] == str(e)
    assert caplog.messages[-1] == exit_msg


def test_argument_exit_message_case3(pmc_catcher, caplog):
    # part 3 no errors took place
    exit_msg = "Exit message"
    with caplog.at_level(logging.INFO):
        with pmc_catcher(exit_message=exit_msg) as catcher_ctx:
            pass

    assert catcher_ctx.exception is None
    assert len(caplog.messages) == 0


def test_argument_report_counts(pmc_catcher, caplog):
    with caplog.at_level(logging.INFO):
        with pytest.raises(SystemExit):
            with pmc_catcher(
                on_errors_raise=SystemExit(-7), report_counts=True
            ):  # count report#1
                with pmc_catcher(report_counts=True):  # count report#2
                    with pmc_catcher():
                        raise e
                    with pmc_catcher(report_counts=True):  # count report#3
                        raise e
                with pmc_catcher():
                    raise w
                with pmc_catcher(report_counts=True):  # count report#4
                    raise e
                assert (
                    len(caplog.messages) == 7
                )  # 3(errors)+1(warning)+3(count reports#2,#3,#4)

    assert len(caplog.messages) == 8  # 3(errors)+1(warning)+4(count reports#1,#2,#3,#4)
    assert caplog.messages[-1] == "encountered 3 total errors."


def test_argument_type(pmc_catcher, caplog):

    with caplog.at_level(logging.WARNING):
        with pmc_catcher(type=True):
            raise e

    assert caplog.messages[-1] == f"<<{repr(e)}>>"


def test_abort(pmc_catcher, caplog):
    abort_msg = "Aborting ... !!!"
    with caplog.at_level(logging.FATAL):
        with pytest.raises(catch.exceptions.Exit) as py_ctx:
            with pmc_catcher():
                raise catch.exceptions.Abort(abort_msg)

    assert py_ctx.value.code == -1
    assert caplog.messages[-1] == abort_msg


def test_exit(pmc_catcher):
    with pytest.raises(catch.exceptions.Exit) as py_ctx:
        with pmc_catcher():
            raise catch.exceptions.Exit(-2)

    assert py_ctx.type == catch.exceptions.Exit
    assert py_ctx.value.code == -2
