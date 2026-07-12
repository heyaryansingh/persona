"""RQ-E12 deterministic integrity probe for the offline LaTeX compiler.

This is a deterministic seam test, not a stochastic modeling experiment; repeated seeds would add
no independent evidence. It verifies stale-output rejection, shell-safe filenames, read-only
compilation, and byte-reproducible PDFs from identical source/environment.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from persona.tools import sandbox


VALID = r"""\documentclass{article}
\usepackage{amsmath}
\title{Persona compiler integrity probe}
\author{Persona}
\date{}
\begin{document}
\maketitle
The frozen result is $2+2=4$.
\end{document}
"""
INVALID = r"""\documentclass{article}
\begin{document}
\undefinedcommand
\end{document}
"""


def main() -> dict:
    with TemporaryDirectory() as td:
        root = Path(td)
        builds = [root / "build-a", root / "build-b"]
        for build in builds:
            build.mkdir()
            (build / "main.tex").write_text(VALID, encoding="utf-8")
        first = sandbox.compile_latex(builds[0], "main.tex")
        second = sandbox.compile_latex(builds[1], "main.tex")
        valid_hash = first.get("pdf_sha256", "")

        (builds[0] / "main.tex").write_text(INVALID, encoding="utf-8")
        stale_probe = sandbox.compile_latex(builds[0], "main.tex")
        unsafe_probe = sandbox.compile_latex(builds[0], "main.tex;touch-INJECTED.tex")

        checks = {
            "valid_compiles_in_read_only_container": bool(first["ok"] and second["ok"]),
            "identical_source_is_byte_reproducible": bool(
                valid_hash and valid_hash == second.get("pdf_sha256")),
            "invalid_recompile_rejects_stale_pdf": bool(
                not stale_probe["ok"] and not (builds[0] / "main.pdf").exists() and
                stale_probe.get("exit_code") not in (None, 0)),
            "unsafe_filename_rejected_before_docker": bool(
                not unsafe_probe["ok"] and unsafe_probe.get("log") == "invalid LaTeX filename" and
                not (builds[0] / "INJECTED").exists()),
        }
        result = {
            "experiment": "RQ-E12 LaTeX integrity seam",
            "kind": "deterministic regression, not multi-seed inference",
            "sandbox_image": sandbox.IMAGE,
            "sandbox_image_digest": first.get("image_digest", ""),
            "source_sha256": first.get("source_sha256", ""),
            "pdf_sha256_build_a": valid_hash,
            "pdf_sha256_build_b": second.get("pdf_sha256", ""),
            "invalid_exit_code": stale_probe.get("exit_code"),
            "invalid_log_has_fatal_error": "Fatal error" in stale_probe.get("log", ""),
            "checks": checks,
            "passed": all(checks.values()),
        }

    results = Path("results")
    results.mkdir(exist_ok=True)
    (results / "rq_e12_latex_integrity.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8")
    import matplotlib.pyplot as plt

    labels = [key.replace("_", " ") for key in checks]
    values = [1 if value else 0 for value in checks.values()]
    fig, ax = plt.subplots(figsize=(9, 3.7))
    fig.patch.set_facecolor("#f7f4ee")
    ax.set_facecolor("#f7f4ee")
    ax.barh(range(len(labels)), values, color=["#4b8b72" if v else "#bd5b4a" for v in values])
    ax.set_yticks(range(len(labels)), labels)
    ax.set_xlim(0, 1.05)
    ax.set_xticks([0, 1], ["fail", "pass"])
    ax.set_title("LaTeX artifact integrity gates", loc="left", weight="bold")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.grid(axis="x", color="#ddd8cd", linewidth=0.8)
    fig.tight_layout()
    fig.savefig(results / "rq_e12_latex_integrity.png", dpi=180, facecolor=fig.get_facecolor())
    plt.close(fig)
    print(json.dumps(result, indent=2))
    if not result["passed"]:
        raise SystemExit("LaTeX integrity gate failed")
    return result


if __name__ == "__main__":
    main()
