# python-pmc-catch

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

## Install

### Regular use _(assuming that you've already published your package on NCBI Artifactory PyPI)_:

```sh
pip install pmc-catch  # or add it to your requirements file
```

### For development:

Before you run scripts from misc/ folder make sure you 
installed pipenv independently of your virtual environments, 
for example you may want to consider using `pipx` 
to install various python package/scripts in kind 
of `standalone` mode.

```sh
git clone ssh://git@bitbucket.be-md.ncbi.nlm.nih.gov:9418/pmc/python-pmc-catch.git
cd python-pmc-catch
misc/run_pipenv_init.sh 
misc/run_pip_install_req_dev.sh 
```

Then do your development. 

### Notes:

- Do not forget to create new git tags
(to keep version of the package bumped/updated). 
- Do not forget to update CHANGELOG.md. 
- Do not forget to add descriptions to doc/*.md files or to this README.md file. 

## Test

Test configuration is defined in the `tox.ini` file and includes
`py.test` tests and `flake8` source code checker.

You can run all of the tests:

```sh
misc/run_bash.sh
python setup.py test
```

or 

```sh
misc/run_tests_setup.sh
```


To run just the `py.test` tests, not `flake8`, and to re-use pipenv `virtualenv` do the following:

```sh
misc/run_bash.sh
py.test
```

or with 

```sh
misc/run_tests_pytest.sh
```


## Usage

```python
>>> from pmc.catch import catcher

```

### As decorator

```python
from pmc.catch import catcher
import click

@click.command(...)
@click.option(...)
...
@catcher(on_errors_raise=SystemExit(-1), report_counts=True)
def your_command(*args, **kwargs):
    ...
    with catcher() as catch_ctx:
        ...
        with catcher():
            raise Exception("Something bad took place.")             
        ...
        with catcher():
            raise Exception("Something bad took place.")             
    ...
```
There should be reported 2 errors.

After executing the script, you should find the exit code is not `0`