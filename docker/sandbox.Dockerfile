# Sandbox image for Persona's analyst (v4 P5). The scientific stack is baked in because the
# sandbox runs with --network none (no pip install at run time). Rebuild: see scripts below.
FROM python:3.12-slim
RUN pip install --no-cache-dir \
      numpy pandas scipy scikit-learn matplotlib statsmodels
# non-root user for defense in depth
RUN useradd -m -u 10001 analyst
USER analyst
WORKDIR /work
ENV PYTHONDONTWRITEBYTECODE=1 MPLBACKEND=Agg
