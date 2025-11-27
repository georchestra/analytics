# geOrchestra analytics module

See the project's documentation at https://docs.georchestra.org/analytics/

## Run the docs in dev mode

The docs use the mkdocs engine. 

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