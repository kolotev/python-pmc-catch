# python-pmc-catch

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
  of argument `on_errors_raise_click_exit` is True, it useful 
  when you are using `click` python package for you scripts 
  and at the most outer level (command one) to catch exceptions
  and exit with non successful exit code. You can pass your own exit
  code with exception raised if you would pass a 2nd argument
  with your exception as `raise Exception(..., N)`
  where N is you integer exit code or your exception class
  has a property `exit_code`.

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
>>> from pmc.catch import catch

```

### As decorator

```python
from pmc.catch import catch
import click

@click.command(...)
@click.option(...)
...
@catch(on_errors_raise_click_exit=True, report_error_counts=True)
def your_command(*args, **kwargs):
    ...
    with catch() as catch_ctx:
        ...
        with catch():
            raise Exception("Something bad took place.")             
        ...
        with catch():
            raise Exception("Something bad took place.")             
    ...
```
There should be reported 2 errors.

After executing the script, you should find the exit code is not `0`