"""A9 — the analyst never runs syntactically-broken generated code.

Persona was generating analysis scripts that don't parse (positional-after-keyword args, stray tokens,
malformed imports) and running them anyway, yielding misleading results. `_code_syntax_error` is the
pre-sandbox gate: broken code is rejected loud (the model gets the error to fix), never executed.
Uses the exact bug shapes the reviewer found. $0, no sandbox.
"""
from persona.agents.analyst import _code_syntax_error


def test_valid_code_passes():
    assert _code_syntax_error("import numpy as np\nx = int(np.arange(10).sum())\nprint(x)\n") is None


def test_positional_after_keyword_rejected():
    # real bug: np.random.gamma(shape=2.0, 1000) — positional arg follows keyword arg
    err = _code_syntax_error("import numpy as np\nprint(np.random.gamma(shape=2.0, 1000))\n")
    assert err is not None and "SyntaxError" in err


def test_stray_token_rejected():
    err = _code_syntax_error("n = 16\nsol = (n // 4, n // 4 * ?)\n")
    assert err is not None and "SyntaxError" in err


def test_malformed_import_rejected():
    err = _code_syntax_error("from sympy import __file__ if False else None\n")
    assert err is not None and "SyntaxError" in err


def test_error_names_the_line():
    err = _code_syntax_error("x = 1\ny = = 2\n")
    assert err is not None and "line 2" in err
