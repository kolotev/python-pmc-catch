import logging
from typing import Callable, Tuple, Union, List, Set, Iterable

import click
from functools import wraps
from pmc.catch.counters import ExceptionCounter, ExceptionCounterGlobal
from pmc.catch.helper import class_or_instancemethod
from pmc.ctxdecoextended import ContextDecoratorExtended
from pmc.catch import exceptions

import inspect

lg = logging.getLogger(__name__)


class catcher(ContextDecoratorExtended):
    """
    ## Description

    `catcher` of `pmc.catcher` package is decorator and context manager
    rolled into one. It allows to customize of behaviors of exception handling
    for the context, function, class method.

    The following behaviors are customizable, which are controlled by
    the following initialization arguments/parameters in the captain ways:

        :param: post_handler: Callable = None,       # an additional routine to handle an exception
        :param: formatter: Callable = None,          # your exception formatter instead of builtin.
        :param: logger: logging.Logger = lg,         # your `logging` compatible logger to be used
                                                     # instead of built-in logging.
        :param:  enter_message: str = None,          # on context enter report a message
        :param:  exit_message: str = None,           # on context exit report a message
        :param:  report_counts: bool = False,        # on context exit report counts
        :param:  on_errors_raise: Exception = None,  # on context exit and if errors encountered
                                                     # raise an exception provided if any.
        :param:  reraise: bool = False,              # re-raise an exception if True
                                                     # (except Warning derived);
        :param:  reraise_types: Union[type, List[type], Tuple[type], Set[type]]
                                                     # transparently re-raise given types
                                                     # by default the following exception
                                                     # instance types are re-reraised: see below.
        :param:  type: bool = False,                 # show a type of exception in the logging

    ## Notes

    ### Transparently reraised exceptions

        click.exceptions.Abort,
        click.exceptions.Exit,
        exceptions.Exit,
        StopIteration,
        RuntimeError,
        SystemExit,
        KeyboardInterrupt

    ## API

    ### Properties access

    Access to properties/methods (like `exception`, `counts`, ...) of
    `catcher` is performed in the following ways:

    - when it is used as a decorator

    ```pythonstub
        from pmc.catcher import catcher

        @catcher
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
        from pmc.catcher import catcher

        with catcher() as ctx:
            ...
        exception = ctx.exception
        errors_count = ctx.errors_count()
        warnings_count = ctx.warnings_count()
        errors_count, warnings_count = ctx.counts()
    ```
    """

    _kbd_interrupt_msg = "Keyboard interrupt was received. Aborting ..."
    _exception_counter = ExceptionCounterGlobal()

    def __init__(
        self,
        post_handler: Callable = None,
        formatter: Callable = None,
        logger: logging.Logger = lg,
        enter_message: str = None,
        exit_message: str = None,
        report_counts: bool = False,
        on_errors_raise: Exception = None,
        reraise: bool = False,
        type: bool = False,
        reraise_types: Union[type, List[type], Tuple[type], Set[type]] = None,
    ):

        self._validate_arg_handler(name="post_handler", handler=post_handler, nargs=1)
        self._validate_arg_handler(name="formatter", handler=formatter, nargs=1)
        self._validate_arg_raise(name="on_errors_raise", value=on_errors_raise)

        self._post_handler = post_handler
        self._formatter = formatter
        self._enter_message = enter_message
        self._exit_message = exit_message
        self._on_errors_raise = on_errors_raise
        self._report_error_counts = report_counts
        self._reraise = reraise
        self._type = type
        self._lg = logger
        self._exception = None
        self._entered = False

        if logger is None:
            self._lg = logging.getLogger(None)
            self._lg.addHandler(logging.NullHandler())

        if reraise_types is None:
            self._reraise_types: Union[type, Tuple[type]] = (
                click.exceptions.Abort,
                click.exceptions.Exit,
                exceptions.Exit,
                StopIteration,
                RuntimeError,
                SystemExit,
                KeyboardInterrupt,
            )
        # print(f"\n__init__: id(self)={hex(id(self))} {repr(self)}")

    def __repr__(self):
        ret = ""
        for k in self.__dict__:
            if (
                getattr(self, k) is not None
                and getattr(self, k) is not False
                and k != "_reraise_types"
            ):
                ret += f"{k[1:]}={repr(getattr(self, k))},"
        return f"{self.__class__.__name__}({ret})"

    def __call__(self, func):
        # print(f"__call__: id(self)={hex(id(self))} {repr(self)}")
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
        # print(f"__enter__: id(self)={hex(id(self))} {repr(self)}")
        # resource acquiring phase
        if self._entered:
            raise RuntimeError(f"Cannot enter {repr(self)} twice.")

        self._entered = True
        self._exception_counter = ExceptionCounter()  # make context counters.

        if self._enter_message is not None:
            self._lg.info(self._enter_message)

        return self

    def __exit__(self, e_type, e, e_tb):
        # print(f"__exit__: id(self)={hex(id(self))} {repr(self)}")
        # resource release phase
        if not self._entered:
            raise RuntimeError(f"Cannot exit {repr(self)} without entering first.")

        self._exception = e

        try:
            if e:
                self._handle_exception(e, e_tb)
                self._call_post_handler(e)
        except BaseException:
            # print(f"__exit__[except]: e={repr(e)}")
            raise
        finally:
            # print(f"__exit__[finally]: e={repr(e)}")
            self._report_on_exit()
            self._raise_on_errors()

        # print(f"__exit__[return]: {None if self._reraise else True}")
        return None if self._reraise else True

    @staticmethod
    def _list(msg: Union[str, Iterable[str]]):
        if isinstance(msg, str) or not isinstance(msg, Iterable):
            return [msg]
        elif isinstance(msg, Iterable):
            return msg

    @staticmethod
    def _validate_arg_raise(name: str, value: Exception) -> None:
        if value is not None and not isinstance(value, BaseException):
            raise TypeError(
                f"argument `{name}` must be an instance of BaseException derived type, "
                f"but `{repr(value)}` is given. ."
            )

    @staticmethod
    def _validate_arg_handler(name: str, handler: Callable, nargs=0) -> None:
        if handler is not None:
            if not callable(handler):
                raise ValueError(
                    f"argument `{name}` must be a callable, "
                    f"but `{repr(handler)}` is given."
                )
            inspected_args = dict(inspect.signature(handler).parameters)
            if not len(inspected_args) == nargs:
                raise TypeError(
                    f"argument `{name}` must be a callable, "
                    f"accepting exactly {nargs} argument(s) of type Exception."
                )

    def _handle_exception(self, e, e_tb):
        # is_warning = isinstance(e, Warning)
        context_exception_counter = self._exception_counter
        global_exception_counter = self.__class__._exception_counter
        e_fname = e_tb.tb_frame.f_code.co_filename
        _messages = self._list(
            f"<<{repr( e )}>> [{e_fname}:{e_tb.tb_lineno}]"
            if self._type
            else self._format_exception(e)
        )

        # print(f"\ntype(e)={type(e)}\n isinstance(e, self._reraise_types)"
        #       f"={isinstance(e, self._reraise_types)}")

        if isinstance(e, KeyboardInterrupt):
            self._lg.fatal(self._kbd_interrupt_msg)
            raise exceptions.Exit(1)
        elif isinstance(e, exceptions.Abort):
            self._lg.fatal(e)
            raise exceptions.Exit(-1)
        elif isinstance(e, self._reraise_types):
            raise e
        elif isinstance(e, Warning):
            for _m in _messages:
                self._lg.warning(_m)
            context_exception_counter.warnings_count += len(_messages)
        else:
            for _m in _messages:
                self._lg.error(_m)
            context_exception_counter.errors_count += len(_messages)

        # pass counts to ExceptionCounterGlobal singleton
        global_exception_counter.errors_count += context_exception_counter.errors_count
        global_exception_counter.warnings_count += (
            context_exception_counter.warnings_count
        )

    def _call_post_handler(self, e):
        if self._post_handler is not None:
            self._post_handler(e)

    def _report_on_exit(self):
        cls = self.__class__

        if (
            cls.errors_count() and self._exit_message is not None
        ):  # show exit message on errors
            self._lg.info(self._exit_message)

        if self._report_error_counts:
            # local_errors_count = self.errors_count()
            global_errors_count = cls.errors_count()
            self._lg.info(
                f"encountered {global_errors_count} total error"
                f"{'s' if global_errors_count != 1 else ''}."
            )

    def _raise_on_errors(self):
        cls = self.__class__
        if cls.errors_count() and self._on_errors_raise is not None:
            raise self._on_errors_raise

    def _format_exception(self, e: Exception):
        if self._formatter:
            return self._formatter(e)
        return str(e)

    @property
    def exception(self):
        """Get last exception occurred if any"""
        return self._exception

    @class_or_instancemethod
    def errors_count(self_or_cls):
        """Get number of error"""
        return self_or_cls._exception_counter.errors_count

    @class_or_instancemethod
    def warnings_count(self_or_cls):
        return self_or_cls._exception_counter.warnings_count

    @class_or_instancemethod
    def counts(self_or_cls) -> Tuple[int, int]:
        """
        :return: errors_count, warnings_count
        """
        exception_counter = self_or_cls._exception_counter
        return (exception_counter.errors_count, exception_counter.warnings_count)
