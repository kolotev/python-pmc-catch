
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
    ## Description

    `catch` of `pmc.catch` package is decorator and context manager
    rolled into one, which handles warnings and exceptions
    in the following way:

        - logs WARNING if caught an exception of a Warning type
        - logs ERROR if caught exception of an Exception type
        - re-raises StopIteration type transparently
        - re-raises Exception if `reraise_error` argument is True
        - re-raises Warning if `reraise_warning` argument is True
        - re-raises Exception if `debug` argument is >= 2
        - re-raises Warning if `debug` argument is >= 3
        - counts Global and contextual Exceptions/Warnings
        - raises exception of `click.exceptions.Exit(code=-1)`
          on argument `on_errors_raise_click_exit` value True, it useful
          when you are using `click` python package for your scripts
          and at the most outer/top level (command one) to catch exceptions
          and exit with non successful exit code if errors were present
          during execution of the script.
        - raises exception of `SystemExit(-1)` on argument `
          on_errors_raise_sys_exit` value True, it useful
          for your scripts at the most outer/top level (command one)
          to catch exceptions and exit with non successful exit code
          if errors were present during execution of the script.

    ## Notes

    access to properties/methods (like `exception`, `counts`, ...) of
    `catch` is performed in the following ways:

    - when it used as a decorator
    ```pythonstub
        from pmc.catch import catch

        @catch
        def func():
            pass
        ...
        func()
        ctx = func.context
        exception = ctx.exception
        errors_count = ctx.errors_count()
        warnings_count = ctx.warnings_count()
        errors_count, warnings_count = ctx.counts()
        ...
    ```
    - when it used as context manager is in a typical  way

    ```pythonstub
        from pmc.catch import catch

        with catch() as ctx:
            ...
        exception = ctx.exception
        errors_count = ctx.errors_count()
        warnings_count = ctx.warnings_count()
        errors_count, warnings_count = ctx.counts()
    ```
    """

    _kbd_interrupt_msg = "Keyboard interrupt was received. Aborting ..."
    _exc_counter = ExceptionCounterGlobal()

    def __init__(
        self,
        debug: int = 0,
        exception_handler: Callable = None,
        logger: logging.Logger = lg,
        on_error_exit_msg: str = None,
        on_errors_raise_click_exit: bool = False,
        on_errors_raise_sys_exit: bool = False,
        report_error_counts=False,
        reraise_error: bool = False,
        reraise_warning: bool = False,
    ):
        """
        :param debug:                     re-raise exception if value >= 2; re-raise warning
                                          exception if value >= 3;
        :param exception_handler:         a callable to handle an exception
                                         (in addition to what `catch` does);
        :param logger:                    your `logging` compatible logger to be used
                                          instead of built-in logging.
        :param on_error_exit_msg:         on error exception the value will be shown if supplied
                                          and at least one of 2 above argument is True;
        :param on_errors_raise_click_exit: on error exception if value is True
                                          the click.exceptions.Exit() will be raised;
        :param on_errors_raise_sys_exit:    on error exception if value is True
                                          the SystemExit(code) will be raised;
        :param report_error_counts:
        :param reraise_error:             re-raise error (non Warning derived) exception
                                          if value is True;
        :param reraise_warning:           re-raise warning exception if value is True;
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
        self._debug = debug
        self._exc_handler = exception_handler
        self._on_error_exit_msg = on_error_exit_msg
        self._on_errors_raise_click_exit = on_errors_raise_click_exit
        self._on_errors_raise_sys_exit = on_errors_raise_sys_exit
        self._report_error_counts = report_error_counts
        self._reraise_error = reraise_error
        self._reraise_warning = reraise_warning

        self._lg = logger
        if logger is None:
            self._lg = logging.getLogger(None)
            self._lg.addHandler(logging.NullHandler())

        self._exception = None

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
        try:
            if e:
                self._handle_exception(e)

            if cls.errors_count() and (
                self._on_errors_raise_sys_exit or self._on_errors_raise_click_exit
            ):
                self._on_error_raise__exit(e)
        except Exception:
            raise
        finally:
            if self._report_error_counts:
                local_errors_count = self.errors_count()  # cls._exc_counter.errors_count
                global_errors_count = cls.errors_count()
                self._lg.info(
                    f"encountered {local_errors_count} error"
                    f"{'s' if local_errors_count != 1 else ''} in the current context."
                )
                self._lg.info(
                    f"encountered {global_errors_count} total error"
                    f"{'s' if global_errors_count != 1 else ''}."
                )

        return True

    def _handle_exception(self, e):
        is_warning = isinstance(e, Warning)
        exc_counter = self._exc_counter
        exc_handler = self._exc_handler
        cls = self.__class__

        if isinstance(e, KeyboardInterrupt):
            self._lg.fatal(self._kbd_interrupt_msg)
            raise click.exceptions.Abort(self._kbd_interrupt_msg)
        elif (
            (self._reraise_warning and is_warning)
            or (self._reraise_error and not is_warning)
            or isinstance(e, (click.exceptions.Abort, click.exceptions.Exit, StopIteration))
            or (isinstance(e, BaseException) and not isinstance(e, Exception))
        ):
            raise e
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

    def _on_error_raise__exit(self, e):
        if self._on_error_exit_msg is not None:  # show exit message on errors
            lg.warning(self._on_error_exit_msg)
        # use exception property `exit_code` if present
        exit_code = getattr(e, "exit_code", -1)
        #
        if self._on_errors_raise_sys_exit:
            raise SystemExit(exit_code)
        if self._on_errors_raise_click_exit:
            raise click.exceptions.Exit(exit_code)

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
