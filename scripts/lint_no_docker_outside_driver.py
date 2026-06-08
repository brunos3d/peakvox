"""lint_no_docker_outside_driver.py — AST-based lint check (2B.5).

Per ADR-0017 §5 and the 2B architecture review guardrail, the
``DockerRuntimeDriver`` is the only component in the backend that
may import the docker SDK. The runtime manager, the adapter, the
PeakVoxRuntime bridge, and every other backend module must
remain Docker-free.

This script performs a static AST scan over the backend source
tree and fails (exit code 1) if any of the following appear
outside ``backend/app/services/drivers/``:

  - ``import docker``
  - ``from docker import ...``
  - ``subprocess`` calls to ``docker``, ``docker-compose``,
    ``podman``, ``nerdctl``, or ``kubectl``

The lint is intentionally conservative: any docker-shaped
subprocess is forbidden outside the driver package, because the
subprocess could bypass the driver protocol and reach into Docker
directly.

Usage:
  python scripts/lint_no_docker_outside_driver.py

Exit codes:
  0 — clean
  1 — violations found
  2 — internal error
"""

from __future__ import annotations

import ast
import os
import sys
from pathlib import Path
from typing import Iterable, List, Tuple


BACKEND_ROOT = Path(__file__).resolve().parent.parent / "backend"
FORBIDDEN_SUBSTRATES = ("docker", "docker-compose", "podman", "nerdctl", "kubectl")


def _driver_package() -> Path:
    """Return the driver package directory. Computed at call time
    so tests can monkeypatch ``BACKEND_ROOT``."""
    return BACKEND_ROOT / "app" / "services" / "drivers"


def _is_subprocess_docker_call(node: ast.Call) -> bool:
    """Detect ``subprocess.run([..., 'docker', ...])`` or similar."""
    # Pattern: subprocess.run([..., 'docker', ...])
    func = node.func
    if not isinstance(func, ast.Attribute):
        return False
    if not (isinstance(func.value, ast.Name) and func.value.id == "subprocess"):
        return False
    if func.attr not in ("run", "call", "Popen", "check_output", "check_call"):
        return False
    # Check the first positional argument (a list literal) for any
    # docker-shaped entry.
    if not node.args:
        return False
    first = node.args[0]
    if isinstance(first, ast.List):
        for elt in first.elts:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                if any(s in elt.value for s in FORBIDDEN_SUBSTRATES):
                    return True
    return False


def _is_docker_import(node: ast.stmt) -> bool:
    """Detect ``import docker`` or ``from docker import ...``."""
    if isinstance(node, ast.Import):
        return any(
            (isinstance(alias, ast.alias) and alias.name.split(".")[0] == "docker")
            for alias in node.names
        )
    if isinstance(node, ast.ImportFrom):
        return (node.module or "").split(".")[0] == "docker"
    return False


def _scan_file(path: Path) -> List[Tuple[int, str]]:
    """Return a list of (line, message) for each violation in the file."""
    try:
        text = path.read_text()
    except (OSError, UnicodeDecodeError):
        return []
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError:
        return []
    violations: List[Tuple[int, str]] = []
    for node in ast.walk(tree):
        if _is_docker_import(node):
            line = getattr(node, "lineno", 0)
            violations.append(
                (line, f"{path.relative_to(BACKEND_ROOT)}:{line}: forbidden `docker` import "
                       f"outside the driver package")
            )
        if isinstance(node, ast.Call) and _is_subprocess_docker_call(node):
            line = getattr(node, "lineno", 0)
            violations.append(
                (line, f"{path.relative_to(BACKEND_ROOT)}:{line}: forbidden subprocess call "
                       f"to a docker-shaped binary outside the driver package")
            )
    return violations


def _is_in_driver_package(path: Path) -> bool:
    """True if the file is inside the driver package (or its sub-packages)."""
    try:
        path.relative_to(_driver_package())
        return True
    except ValueError:
        return False


def _python_files(root: Path) -> Iterable[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        # Skip hidden directories and common non-source dirs.
        dirnames[:] = [
            d for d in dirnames
            if not d.startswith(".") and d not in ("__pycache__", "node_modules", ".venv-test", "dev-venv", ".venv_tmp", ".ruff_cache")
        ]
        for name in filenames:
            if name.endswith(".py"):
                yield Path(dirpath) / name


def main() -> int:
    if not BACKEND_ROOT.exists():
        print(f"ERROR: backend root not found: {BACKEND_ROOT}", file=sys.stderr)
        return 2

    violations: List[Tuple[int, str]] = []
    for path in _python_files(BACKEND_ROOT):
        # The driver package and its sub-modules are allowed to
        # import docker and to call docker-shaped subprocesses.
        if _is_in_driver_package(path):
            continue
        violations.extend(_scan_file(path))

    if violations:
        print("lint_no_docker_outside_driver.py: violations found:")
        for line, msg in violations:
            print(f"  {msg}")
        return 1
    print("lint_no_docker_outside_driver.py: clean (no docker imports outside the driver package)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
