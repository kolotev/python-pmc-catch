class Exit(SystemExit):
    """An exception that indicates that the application should exit with some
    status code.

    :param code: the status code to exit with.
    """


class Abort(RuntimeError):
    """An internal signalling exception that signals catcher to abort.
    """
