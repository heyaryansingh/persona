# Sandbox image for Persona's analyst (v4 P5). The scientific stack is baked in because the
# sandbox runs with --network none (no pip install at run time). Rebuild: see scripts below.
FROM python:3.12-slim
# LaTeX (offline pdflatex — the sandbox has no network, so packages must be baked in) + sci stack
RUN apt-get update && apt-get install -y --no-install-recommends \
      texlive-latex-base texlive-latex-recommended texlive-fonts-recommended texlive-latex-extra \
    && rm -rf /var/lib/apt/lists/*
# numeric + symbolic: sympy/mpmath give the analyst REAL math (derive, simplify, prove identities,
# exact/arbitrary-precision arithmetic) — not just numeric estimation; networkx for graph reasoning.
RUN pip install --no-cache-dir \
      numpy pandas scipy scikit-learn matplotlib statsmodels sympy mpmath networkx
# CPU PyTorch for the code editor / ML experiments (large; separate layer + index so the cache reuses it)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
# non-root user for defense in depth
RUN useradd -m -u 10001 analyst
USER analyst
WORKDIR /work
ENV PYTHONDONTWRITEBYTECODE=1 MPLBACKEND=Agg
