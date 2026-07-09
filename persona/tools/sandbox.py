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
