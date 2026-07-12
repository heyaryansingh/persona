"""Sandboxed code execution (v4 P5) — the analyst runs REAL Python on REAL compute, safely.

Ephemeral Docker container from the `persona-sandbox` image (scientific stack baked in):
  --network none   -> no egress from inside the sandbox (data is fetched OUTSIDE, mounted RO)
  --read-only root + tmpfs, non-root user, CPU/memory/pids/time caps
The project dir is mounted rw at /work (code + outputs); an optional dataset dir RO at /work/data.
Host-side timeout kills a runaway container. This is the boundary that lets the agent compute
without being able to do anything irreversible or reach the network.
"""
from __future__ import annotations

import subprocess
import uuid
import hashlib
import re
from pathlib import Path

IMAGE = "persona-sandbox"


def _dockerize(p: Path) -> str:
    # Docker Desktop on Windows accepts forward-slash absolute paths (C:/Users/...)
    return str(p.resolve()).replace("\\", "/")


def run_python(code: str, workdir: Path, *, data_dir: Path = None, timeout: int = 60,
               memory: str = "1g", image: str = IMAGE) -> dict:
    """Run `code` in the sandbox with `workdir` mounted rw at /work. Returns stdout/stderr/exit."""
    workdir = Path(workdir)
    workdir.mkdir(parents=True, exist_ok=True)
    (workdir / "_run.py").write_text(code, encoding="utf-8")
    name = "persona_sbx_" + uuid.uuid4().hex[:10]
    args = ["docker", "run", "--rm", "--name", name, "--network", "none", "--read-only",
            "--tmpfs", "/tmp:size=256m", "--memory", memory, "--cpus", "1",
            "--pids-limit", "256", "-v", f"{_dockerize(workdir)}:/work"]
    if data_dir is not None:
        args += ["-v", f"{_dockerize(Path(data_dir))}:/work/data:ro"]
    args += [image, "python", "/work/_run.py"]
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=timeout, encoding="utf-8",
                           errors="replace")
        return {"exit_code": p.returncode, "stdout": (p.stdout or "")[-8000:],
                "stderr": (p.stderr or "")[-4000:], "timeout": False}
    except subprocess.TimeoutExpired:
        subprocess.run(["docker", "kill", name], capture_output=True)
        return {"exit_code": -1, "stdout": "", "stderr": f"execution exceeded {timeout}s and was killed",
                "timeout": True}
    except FileNotFoundError:
        return {"exit_code": -1, "stdout": "", "stderr": "docker not available", "timeout": False}


def compile_latex(workdir: Path, tex: str = "main.tex", timeout: int = 150, image: str = IMAGE,
                  source_date_epoch: int = 0) -> dict:
    """Compile a LaTeX file to PDF inside the sandbox (offline pdflatex, run twice for refs).
    The root filesystem is read-only; only /work and /tmp are writable. A stale PDF can never count
    as success. SOURCE_DATE_EPOCH makes identical source/environment builds byte-reproducible."""
    workdir = Path(workdir).resolve()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+\.tex", tex or ""):
        return {"ok": False, "pdf": None, "log": "invalid LaTeX filename", "exit_code": -1}
    source = workdir / tex
    if not source.is_file():
        return {"ok": False, "pdf": None, "log": "LaTeX source not found", "exit_code": -1}
    pdf = source.with_suffix(".pdf")
    logf = workdir / "_tex.log"
    for stale in (pdf, logf, source.with_suffix(".aux"), source.with_suffix(".out"),
                  source.with_suffix(".toc")):
        stale.unlink(missing_ok=True)

    logs, exit_code = [], -1
    base = ["docker", "run", "--rm", "--network", "none", "--read-only",
            "--tmpfs", "/tmp:size=256m", "--memory", "1g", "--cpus", "1",
            "--pids-limit", "256", "-e", f"SOURCE_DATE_EPOCH={int(source_date_epoch)}",
            "-e", "FORCE_SOURCE_DATE=1", "-e", "TZ=UTC",
            "-v", f"{_dockerize(workdir)}:/work", "-w", "/work", image,
            "pdflatex", "-interaction=nonstopmode", "-halt-on-error", tex]
    for run_number in range(2):
        name = "persona_tex_" + uuid.uuid4().hex[:10]
        args = base[:3] + ["--name", name] + base[3:]
        try:
            result = subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                                    encoding="utf-8", errors="replace")
        except subprocess.TimeoutExpired:
            subprocess.run(["docker", "kill", name], capture_output=True)
            logs.append(f"pass {run_number + 1}: compile timed out")
            exit_code = -1
            break
        except FileNotFoundError:
            logs.append("docker not available")
            exit_code = -1
            break
        exit_code = result.returncode
        logs.append(f"--- pass {run_number + 1} · exit {exit_code} ---\n"
                    f"{result.stdout or ''}\n{result.stderr or ''}")
        if exit_code != 0:
            break
    log_text = "\n".join(logs)
    logf.write_text(log_text, encoding="utf-8", errors="replace")
    ok = exit_code == 0 and pdf.is_file() and pdf.stat().st_size > 0
    if not ok:
        pdf.unlink(missing_ok=True)
    pdf_sha = hashlib.sha256(pdf.read_bytes()).hexdigest() if ok else ""
    return {"ok": ok, "pdf": str(pdf) if ok else None, "log": log_text[-8000:],
            "exit_code": exit_code, "pdf_sha256": pdf_sha,
            "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "image_digest": image_digest(image)}


def image_ready(image: str = IMAGE) -> bool:
    try:
        r = subprocess.run(["docker", "image", "inspect", image], capture_output=True, timeout=15)
        return r.returncode == 0
    except Exception:
        return False


def image_digest(image: str = IMAGE) -> str:
    """The image content id — pins the environment so a rebuilt image can't silently change results."""
    try:
        r = subprocess.run(["docker", "image", "inspect", "--format", "{{.Id}}", image],
                           capture_output=True, text=True, timeout=15)
        return (r.stdout or "").strip() if r.returncode == 0 else ""
    except Exception:
        return ""
