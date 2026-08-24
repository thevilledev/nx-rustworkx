"""Shared plumbing for the external benchmark runners in this directory."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_WORKDIR = HERE / ".work"


def log(msg: str) -> None:
    print(f"[external-bench] {msg}", flush=True)


def run(
    cmd: list,
    *,
    cwd: Path | None = None,
    env: dict | None = None,
    timeout: float | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess:
    """Run a subprocess, echoing the command line first."""
    printable = " ".join(str(c) for c in cmd)
    log(f"$ {printable}" + (f"  (cwd={cwd})" if cwd else ""))
    return subprocess.run([str(c) for c in cmd], cwd=cwd, env=env, timeout=timeout, check=check)


def clone_at(url: str, rev: str, workdir: Path, name: str) -> Path:
    """Clone ``url`` into ``workdir/name`` and pin a local ``main`` at ``rev``.

    Both suites' asv configs declare ``branches: ["main"]``, so the pinned
    checkout reuses that branch name even when ``rev`` is a tag commit.
    A ``--filter=blob:none`` partial clone keeps arbitrary-SHA pins cheap.
    """
    dest = workdir / name
    if not (dest / ".git").exists():
        workdir.mkdir(parents=True, exist_ok=True)
        run(["git", "clone", "--filter=blob:none", url, dest])
    have_rev = subprocess.run(
        ["git", "-C", str(dest), "rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}"],
        capture_output=True,
    )
    if have_rev.returncode != 0:
        run(["git", "-C", dest, "fetch", "--tags", "origin", rev], check=False)
        run(["git", "-C", dest, "fetch", "--tags", "origin"], check=False)
    run(["git", "-C", dest, "checkout", "--quiet", "-B", "main", rev])
    # Restore a pristine tree so runner-applied patches and previous asv
    # output never leak into the next run.
    run(["git", "-C", dest, "reset", "--hard", "--quiet", rev])
    run(["git", "-C", dest, "clean", "-fdxq"])
    return dest


def patch_file(path: Path, replacements: list[tuple], label: str) -> None:
    """Apply exact-string replacements, failing loudly on upstream drift.

    Each replacement is ``(old, new)`` or ``(old, new, expected_count)``.
    """
    text = path.read_text()
    for old, new, *rest in replacements:
        expected = rest[0] if rest else 1
        count = text.count(old)
        if count != expected:
            raise SystemExit(
                f"{label}: expected {expected} occurrence(s) of {old!r} in {path}, "
                f"found {count}. Upstream changed; update the pin or the patch."
            )
        text = text.replace(old, new)
    path.write_text(text)
    log(f"patched {path.name}: {len(replacements)} replacement(s) ({label})")


def snapshot_tree(src: Path, dest: Path) -> None:
    """Copy a directory tree, replacing any previous snapshot."""
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    log(f"snapshotted {src} -> {dest}")


def clean_env(**overrides: str) -> dict:
    """Process env without backend-priority leakage, plus explicit overrides."""
    env = os.environ.copy()
    for var in (
        "NETWORKX_BACKEND_PRIORITY",
        "NETWORKX_BACKEND_PRIORITY_ALGOS",
        "NETWORKX_BACKEND_PRIORITY_GENERATORS",
        "NETWORKX_AUTOMATIC_BACKENDS",
    ):
        env.pop(var, None)
    env.update(overrides)
    return env


def asv_result_files(snapshot_dir: Path) -> list[Path]:
    """Per-commit asv result JSONs in a results tree (asv exits 0 even when
    discovery fails, so presence of these files is the real success signal)."""
    if not snapshot_dir.exists():
        return []
    return [
        f for f in snapshot_dir.rglob("*.json") if f.name not in ("benchmarks.json", "machine.json")
    ]


def machine_info() -> dict:
    from importlib.metadata import version

    import networkx
    import rustworkx

    return {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "networkx": networkx.__version__,
        "rustworkx": rustworkx.__version__,
        # nx_rustworkx.__version__ resolves from this same metadata.
        "nx-rustworkx": version("nx-rustworkx"),
    }


def write_json(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")
    log(f"wrote {path}")
