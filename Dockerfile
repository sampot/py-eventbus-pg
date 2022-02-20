FROM python:3.10.2-slim as base

# set work directory
WORKDIR /app


RUN pip install --upgrade pip 

FROM base
# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PYTHONFAULTHANDLER=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=on
ENV PIP_NO_CACHE_DIR=off
ENV POETRY_VERSION 1.0.0

COPY ./poetry.lock /app/poetry.lock
COPY ./pyproject.toml /app/pyproject.toml

RUN pip install "poetry>=${POETRY_VERSION}}" \
  && poetry config virtualenvs.create false \
  && poetry install --no-interaction --no-ansi --without dev


CMD ["python", "py_eventbus_pg/main.py"]