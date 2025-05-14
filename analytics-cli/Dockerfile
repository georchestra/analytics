FROM python:3.11-slim-bookworm AS base

LABEL maintainer="jean.pommier@pi-geosolutions.fr" \
      description="Python CLI for geOrchestra analytics data processing"

# Avoid warnings by switching to noninteractive
ARG DEBIAN_FRONTEND=noninteractive

ENV LANG=C.UTF-8
ENV LC_ALL=C.UTF-8
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get -y install python3-venv \
    && apt-get -q clean \
    && rm -rf /var/lib/apt/lists/*

# Use a virtualenv
RUN python -m venv /opt/venv
# Enable venv
ENV PATH="/opt/venv/bin:$PATH"

#-----------
FROM base AS dev

WORKDIR /app
COPY . /app

# Install analytics-cli local code (not from pypi)

RUN pip install --upgrade pip setuptools setuptools_scm wheel
ARG VERSION
# Apparently, it fails with a "dirty" version string. But since the version is in the image's tag, we can go with a
# non-meaningful version here
ENV SETUPTOOLS_SCM_PRETEND_VERSION_FOR_GEORCHESTRA_ANALYTICS_CLI=0.0.0
#ENV SETUPTOOLS_SCM_DEBUG=true

RUN pip install --root-user-action=ignore --no-cache-dir .

CMD ["analytics-cli"]

#-----------
FROM base AS test

WORKDIR /app
ARG VERSION
ENV SET_VERSION="==$VERSION"
RUN pip install --upgrade pip \
    && pip install -i https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ georchestra-analytics-cli$SET_VERSION

CMD ["analytics-cli"]

#-----------
FROM base AS release

WORKDIR /app
ARG VERSION
ENV SET_VERSION="==$VERSION"
RUN pip install --upgrade pip \
    && pip install georchestra-analytics-cli$SET_VERSION

CMD ["analytics-cli"]