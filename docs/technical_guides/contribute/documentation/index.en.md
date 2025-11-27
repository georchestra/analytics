# Contributing some documentation

Contributing documentation can be the easiest way to contribute to the project. It is not very technical and will be
very helpful. This is the best way to make sure that your knowledge and experience is shared with others.

The docs use the [mkdocs](https://www.mkdocs.org/) engine.   
The documentation files are located in the `docs/` folder.

To contribute documentation, the best way is to

- install and run mkdocs locally
- run the mkdocs dev server so you can see the changes live
- work on the documentation content
- when you are happy about it, you can commit the changes and open a pull request

## Install mkdocs

You will have to create a python virtualenv and install mkdocs first:

```bash
python3 -m venv venv_mkdocs
source venv_mkdocs/bin/activate
pip install -r mkdocs_requirements.txt
```

If your virtualenv already was created, you can just activate it:

```bash
source venv_mkdocs/bin/activate
```

And run the docs in dev mode:

```bash
mkdocs serve
```


