# geOrchestra analytics CLI

A CLI tool to process access log data for geOrchestra analytics.

Different sources are accepted for access log data:
- A postgresql buffer table reproducing the Opentelemetry access log data structure.
- File-based access logs. It is expected to contain CLF-like (or, say, text-based) access log entries. They are parsed using a regular expression pattern. 
- Fake access logs can also be generated for dev/testing/discovery purposes

The result is written in a postgresql table, preferably a timescaleDB hypertable, since a lot of data will be written and you will want time-enabled data management.

To know more about it, please read the doc on https://docs.georchestra.org/analytics

## Install

Create a virtualenv and install this package:
```bash
python -m venv .venv
source .venv/bin/activate
pip install georchestra_analytics_cli
```


## Build & publish

This project is based on [pyScaffold](https://pypi.org/project/PyScaffold/) and uses [tox](https://tox.wiki/en/latest/installation.html) for the build.

There is no CI as of now, it's done manually.

To install `tox`, we recommend installing it with [pipx](https://pypi.org/project/pipx):
```bash
pipx install tox
tox --help
```

### Build the project:
```
tox -e clean,build
```

### Publish to Pypi:
To publish to Pypi, there are some prerequisites:

- You must set a git tag on your current commit (e.g. `git tag -a 0.1.0 -m "v0.1.0"`)
- Your git working tree should be clean (nothing pending, `git status` should report `nothing to commit, working tree clean`).

This ensures that `setuptools_scm` will detect a clean version. `setuptools_scm` extracts automatically the version from the `git describe` information, behind the scene.

You will also also need a pypi token to publish

Publish on test.pypi.org:
```
tox -e publish
```

Publish on pypi.org:
```
tox -e publish -- --repository pypi
```

### Docker build:

We provide you with a utility script, `./docker_build.sh`.  
It takes 2 options:

- `--mode=`: the build mode (one of [dev, test, pypi]). `test` will try to fetch the package from test.pypi while `pypi` will try to fetch it from the main pypi repo. `dev` will build the local code base.
- `--version=`: allows to set the version to use. On dev mode, it can be arbitrary. 

Examples:

- Build from the latest version from pypi:
```
./docker_build.sh --mode=pypi
```
- Build from the 0.1.0 version from pypi: (version 0.1.0 has to exist there)
```
./docker_build.sh --mode=pypi --version=0.1.0
```
- Build from the 0.1.0 version from test.pypi: (version 0.1.0 has to exist there)
```
./docker_build.sh --mode=test --version=0.1.0
```
- Build from local codebase, tag it 0.1.0-dirty:
```
./docker_build.sh --mode=dev --version=0.1.0-dirty
```
- Build from local codebase, use the auto-generated tag:
```
./docker_build.sh --mode=dev
```
