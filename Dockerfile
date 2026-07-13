FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PERSONA_WORKSPACE=/data/workspace

RUN useradd --create-home --uid 10001 persona \
    && mkdir -p /app /data/workspace \
    && chown -R persona:persona /app /data
WORKDIR /app

COPY pyproject.toml README.md ./
COPY persona ./persona
RUN pip install --no-cache-dir .

USER persona
VOLUME ["/data/workspace"]
CMD ["persona", "--host", "0.0.0.0", "--port", "8137"]
