# python-pmc-catch

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
>>> from pmc.catch import catch as pmc_catch

```
