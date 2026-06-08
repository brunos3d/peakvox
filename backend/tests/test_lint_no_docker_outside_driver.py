"""TDD: scripts/lint_no_docker_outside_driver.py (2B.5).

The lint is a static AST scan that fails when any Python file
under ``backend/`` (outside the driver package) imports ``docker``
or calls a docker-shaped subprocess.

These tests assert:
- A clean tree produces no violations.
- An import of `docker` outside the driver package is flagged.
- A subprocess call to `docker` outside the driver package is
  flagged.
- An import of `docker` INSIDE the driver package is allowed
  (the driver is the only allowed consumer).
- The script exits 0 on a clean tree and 1 on violations.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "lint_no_docker_outside_driver.py"


def _load_script_module():
    spec = importlib.util.spec_from_file_location("lint_script", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _make_temp_py(tmp_path: Path, name: str, body: str) -> Path:
    p = tmp_path / name
    p.write_text(body)
    return p


def test_lint_module_loads() -> None:
    mod = _load_script_module()
    assert mod is not None


def test_clean_tree_has_no_violations(tmp_path: Path) -> None:
    # Build a minimal clean tree mirroring the project layout.
    backend = tmp_path / "backend"
    drivers = backend / "app" / "services" / "drivers"
    other = backend / "app" / "services" / "runtime_types.py"
    drivers.mkdir(parents=True)
    drivers.joinpath("docker_runtime_driver.py").write_text(
        "import docker  # allowed inside the driver package\n"
    )
    other.write_text("from typing import Any\n")
    mod = _load_script_module()
    # Patch the BACKEND_ROOT to the temp dir.
    mod.BACKEND_ROOT = backend
    assert mod.main() == 0


def test_import_docker_outside_driver_is_flagged(tmp_path: Path) -> None:
    backend = tmp_path / "backend"
    drivers = backend / "app" / "services" / "drivers"
    drivers.mkdir(parents=True)
    drivers.joinpath("__init__.py").write_text("")
    drivers.joinpath("docker_runtime_driver.py").write_text("import docker\n")
    bad = backend / "app" / "services" / "runtime_manager.py"
    bad.write_text("import docker\n")
    mod = _load_script_module()
    mod.BACKEND_ROOT = backend
    rc = mod.main()
    assert rc == 1


def test_from_docker_import_outside_driver_is_flagged(tmp_path: Path) -> None:
    backend = tmp_path / "backend"
    drivers = backend / "app" / "services" / "drivers"
    drivers.mkdir(parents=True)
    drivers.joinpath("__init__.py").write_text("")
    drivers.joinpath("docker_runtime_driver.py").write_text("from docker import errors\n")
    bad = backend / "app" / "services" / "runtime_manager.py"
    bad.write_text("from docker import errors\n")
    mod = _load_script_module()
    mod.BACKEND_ROOT = backend
    assert mod.main() == 1


def test_subprocess_run_docker_outside_driver_is_flagged(tmp_path: Path) -> None:
    backend = tmp_path / "backend"
    drivers = backend / "app" / "services" / "drivers"
    drivers.mkdir(parents=True)
    drivers.joinpath("__init__.py").write_text("")
    drivers.joinpath("docker_runtime_driver.py").write_text("")
    bad = backend / "app" / "services" / "runtime_manager.py"
    bad.write_text(
        "import subprocess\n"
        "subprocess.run(['docker', 'ps'])\n"
    )
    mod = _load_script_module()
    mod.BACKEND_ROOT = backend
    assert mod.main() == 1


def test_subprocess_run_docker_inside_driver_is_allowed(tmp_path: Path) -> None:
    """The driver is allowed to use docker. The lint only flags
    docker usage OUTSIDE the driver package."""
    backend = tmp_path / "backend"
    drivers = backend / "app" / "services" / "drivers"
    drivers.mkdir(parents=True)
    drivers.joinpath("__init__.py").write_text("")
    drivers.joinpath("docker_runtime_driver.py").write_text(
        "import subprocess\n"
        "subprocess.run(['docker', 'ps'])\n"
    )
    mod = _load_script_module()
    mod.BACKEND_ROOT = backend
    assert mod.main() == 0


def test_real_backend_tree_is_clean() -> None:
    """The current backend tree must pass the lint: no docker
    imports outside the driver package."""
    backend = REPO_ROOT / "backend"
    if not backend.exists():
        pytest.skip("backend tree not present")
    mod = _load_script_module()
    mod.BACKEND_ROOT = backend
    assert mod.main() == 0, (
        "Backend tree violates the no-docker-outside-driver rule. "
        "Docker imports are confined to backend/app/services/drivers/."
    )


def test_real_script_exits_zero_on_clean_tree() -> None:
    """End-to-end: invoke the script as a subprocess on the real
    backend and assert exit 0. This catches any path-handling
    bugs in the CLI mode."""
    backend = REPO_ROOT / "backend"
    if not backend.exists():
        pytest.skip("backend tree not present")
    # Run the script in a cwd that allows the BACKEND_ROOT relative
    # computation to land on the real backend.
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, (
        f"lint script failed (rc={result.returncode}):\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )
    assert "clean" in result.stdout
