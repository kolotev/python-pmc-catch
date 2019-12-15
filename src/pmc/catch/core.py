
import logging
from typing import Callable, Tuple

import click
from functools import wraps
from pmc.catch.counters import ExceptionCounter, ExceptionCounterGlobal
from pmc.catch.helper import class_or_instancemethod
from pmc.ctxdecoextended import ContextDecoratorExtended
import inspect

lg = logging.getLogger(__name__)


class catch(ContextDecoratorExtended):
    """
    `catch` is decorator and context manager rolled into one, which
    handles warnings and exceptions in the following way:

        - logs WARNING if caught exception is an instance of Warning
        - logs ERROR if caught exception is an instance of Exception
        - re-raise StopIteration unconditionally
        - re-raise Warning if `reraise_warning` argument is True
        - re-raise Exception if `reraise_error` argument is True
        - re-raise Exception if `debug` argument is >= 2
        - re-raise Warning if `debug` argument is >= 3
        - counts Global and context Exceptions and Warnings
        - raises exception of `click.exceptions.Exit(code=-1)` of argument
          `on_errors_click_exit` is True, useful in context of using `click` python
          module and in the most outer (command) level to catch exceptions
          and exit with non successful exit code. You can pass you own exit
          code with exception raised if you would pass a 2nd argument
          with your exception as `raise Exception(..., N)`
          where N is you integer exit code or your exception class
          has a property `exit_code`.

    Notes

        access to properties/methods (like `exception`, `counts`, ...) of `catch` is performed
        in the following ways:

            - when it used as decorator

                @catch
                def func(...)
                    pass
                ...
                func()
                func.context.exception
                errors_count, warnings_count = func.context.counts()
                ...

            - when it used as context manager is in a typical  way

                with catch() as ctx:
                    ...
                ctx.exception
                errors_count, warnings_count = ctx.counts()


    """

    _kbd_interrupt_msg = "Keyboard interrupt was received. Aborting ..."
    _exc_counter = ExceptionCounterGlobal()

    def __init__(
        self,
        reraise_error: bool = False,
        reraise_warning: bool = False,
        debug: int = 0,
        on_errors_exit: bool = False,
        on_errors_click_exit: bool = False,
        on_errors_exit_msg: str = None,
        exception_handler: Callable = None,
        logger: logging.Logger = lg,
    ):
        """
        :param reraise_error:
        :param reraise_warning:
        :param debug:
        :param on_errors_exit:
            Set True if you want the SystemExit(code) to be raised
        :param on_errors_click_exit:
            Set True if you want the click.exceptions.Exit() to be raised
        :param on_errors_exit_msg:
            Supply a message to show at the time of exit if exceptions
            or warnings are encountered.
        :param exception_handler:
        :param logger:
        """
        if exception_handler is not None:
            if not callable(exception_handler):
                raise ValueError(
                    f"argument `exception_handler` must be a callable, "
                    f"but `{repr( exception_handler )}` is given."
                )
            if len(inspect.getfullargspec(exception_handler).args) != 1:
                raise TypeError(
                    f"argument `exception_handler` must be a callable, "
                    f"accepting exactly one argument of type Exception."
                )
        self._reraise_error = reraise_error
        self._reraise_warning = reraise_warning
        self._debug = debug
        self._on_errors_exit = on_errors_exit
        self._on_errors_click_exit = on_errors_click_exit
        self._on_errors_exit_msg = on_errors_exit_msg
        self._exc_handler = exception_handler

        self._lg = logger
        if logger is None:
            self._lg = logging.getLogger(None)
            self._lg.addHandler(logging.NullHandler())

        self._exception = None
        # print("\n" + "="*79)
        # print(f"__init__: self._on_errors_exit={self._on_errors_exit}")
        # print(f"__init__: self._on_errors_click_exit={self._on_errors_click_exit}")

    def __call__(self, func):
        parent = self

        class Inner:
            @wraps(func)
            def __call__(self, *args, **kwargs):
                with parent as ctx:
                    self._context = ctx
                    return func(*args, **kwargs)

            @property
            def context(self):
                return self._context

        return Inner()

    def __enter__(self, *args, **kwargs):
        # resource acquiring phase
        # print(f"__enter__: self._on_errors_exit={self._on_errors_exit}")
        # print(f"__enter__: self._on_errors_click_exit={self._on_errors_click_exit}")
        self._exc_counter = ExceptionCounter()  # make context counters.
        return self

    def __exit__(self, e_type, e, e_tb):
        # resource release phase
        self._exception = e
        debug = self._debug
        cls = self.__class__

        is_warning = isinstance(e, Warning)
        self._reraise_error = debug >= 2 and not is_warning or self._reraise_error
        self._reraise_warning = debug >= 3 or self._reraise_warning

        #
        if e:
            self._on_exception(e, is_warning)

        #
        # print(f"__exit__: self._on_errors_exit={self._on_errors_exit}")
        # print(f"__exit__: self._on_errors_click_exit={self._on_errors_click_exit}")
        if cls._exc_counter.errors_count and (self._on_errors_exit or self._on_errors_click_exit):
            self._on_errors__exit(e)

        return True, self

    def _on_exception(self, e, is_warning):
        exc_counter = self._exc_counter
        exc_handler = self._exc_handler
        cls = self.__class__

        if (
            (self._reraise_warning and is_warning)
            or (self._reraise_error and not is_warning)
            or isinstance(e, (click.exceptions.Abort, click.exceptions.Exit, StopIteration))
        ):
            raise e
        elif isinstance(e, KeyboardInterrupt):
            self._lg.fatal(self._kbd_interrupt_msg)
            raise click.Abort()
        elif isinstance(e, Warning):
            _message = self._format_exception(e)
            self._lg.warning(_message)
            exc_counter.warnings_count += 1
        else:
            _message = self._format_exception(e)
            self._lg.error(_message)
            exc_counter.errors_count += 1
        # pass counts to ExceptionCounterGlobal singleton
        cls._exc_counter.errors_count += exc_counter.errors_count
        cls._exc_counter.warnings_count += exc_counter.warnings_count
        if exc_handler is not None:
            exc_handler(e)

    def _on_errors__exit(self, e):
        if self._on_errors_exit_msg is not None:  # show exit message on errors
            lg.warning(self._on_errors_exit_msg)
        #
        try:
            # second argument from exception expected ot be exit code.
            exit_code = int(e.args[1])
        except (IndexError, ValueError, TypeError):
            exit_code = -1
        # use exception property `exit_code` if present
        exit_code = getattr(e, "exit_code", exit_code)
        #
        if self._on_errors_exit:
            raise SystemExit(exit_code)
        if self._on_errors_click_exit:
            raise click.exceptions.Exit(code=exit_code)

    def _format_exception(self, e: Exception):
        return f"<<{repr( e )}>>" if self._debug else str(e)

    @property
    def exception(self):
        """Get last exception occurred if any"""
        return self._exception

    @class_or_instancemethod
    def errors_count(self_or_cls):
        """Get number of error"""
        return self_or_cls._exc_counter.errors_count

    @class_or_instancemethod
    def warnings_count(self_or_cls):
        return self_or_cls._exc_counter.warnings_count

    @class_or_instancemethod
    def counts(self_or_cls) -> Tuple[int, int]:
        """
        :return: errors_count, warnings_count
        """
        return (self_or_cls._exc_counter.errors_count, self_or_cls._exc_counter.warnings_count)
