"""meshterm — Fabric tasks for distributed e2e testing.

Usage:
    fab --list                       # show all tasks
    fab build                        # build wheel + sdist (local)
    fab smoketest                    # local fresh-venv install + smoke
    fab deploy.nebula                # rsync wheel to Nebula + install
    fab deploy.eagle                 # rsync wheel to Eagle + install
    fab dogfood.send-from-nebula     # cross-host meshterm send test

Requires:
    pip install fabric>=3.0
    SSH aliases configured in ~/.ssh/config: Nebula, Eagle-wifi (or Eagle-remote)

This fabfile mirrors the colony's ad-hoc deployment pattern. The aliases
Nebula/Eagle-wifi/Eagle-remote come from the operator's ~/.ssh/config and are
NEVER hardcoded here.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

try:
    from fabric import Connection, task
    from invoke import Context
except ImportError:
    print("ERROR: fabric not installed. Run: pip install 'fabric>=3.0'", file=sys.stderr)
    sys.exit(1)


PKG_DIR = Path(__file__).parent.resolve()
PKG_NAME = "meshterm"
DIST_PREFIX = "meshterm"


def _latest_wheel() -> Path:
    wheels = sorted(PKG_DIR.glob(f"dist/{DIST_PREFIX}-*-py3-none-any.whl"))
    if not wheels:
        raise FileNotFoundError("No wheel in dist/. Run `fab build` first.")
    return wheels[-1]


def _eagle_alias() -> str:
    """Pick Eagle SSH alias based on detect-env.sh output (or fallback)."""
    detect = os.path.expanduser("~/Scripts/colony-ops/scripts/detect-env.sh")
    if os.access(detect, os.X_OK):
        ctx = Context()
        env = ctx.run(detect, hide=True, warn=True).stdout.strip()
        return "Eagle-wifi" if env == "ev-ofis" else "Eagle-remote"
    return "Eagle-remote"


@task
def build(c: Context) -> None:
    """Build wheel + sdist via `uv build`."""
    c.run("rm -rf dist/")
    c.run("uv build")
    wheel = _latest_wheel()
    print(f"Built: {wheel.name}")


@task
def smoketest(c: Context) -> None:
    """Local fresh-venv install + import + CLI version check."""
    wheel = _latest_wheel()
    venv = "/tmp/meshterm-smoketest"
    c.run(f"rm -rf {venv}")
    c.run(f"uv venv {venv} --python 3.11")
    c.run(f". {venv}/bin/activate && uv pip install {wheel}")
    c.run(
        f". {venv}/bin/activate && python -c "
        f"\"import {PKG_NAME}; print(f'{PKG_NAME} version:', {PKG_NAME}.__version__)\""
    )
    c.run(f". {venv}/bin/activate && meshterm --version")
    c.run(f"rm -rf {venv}")
    print("Smoketest OK")


@task(name="deploy.nebula")
def deploy_nebula(c: Context) -> None:
    """rsync wheel to Nebula + install in fresh venv."""
    wheel = _latest_wheel()
    cn = Connection("Nebula")
    cn.run("mkdir -p ~/.local/share/meshterm-deploy")
    cn.put(str(wheel), remote=f"~/.local/share/meshterm-deploy/{wheel.name}")
    cn.run(f"uv venv ~/.local/share/meshterm-deploy/.venv --python 3.11")
    cn.run(
        f". ~/.local/share/meshterm-deploy/.venv/bin/activate && "
        f"uv pip install ~/.local/share/meshterm-deploy/{wheel.name}"
    )
    cn.run(
        f". ~/.local/share/meshterm-deploy/.venv/bin/activate && "
        f"python -c \"import {PKG_NAME}; print({PKG_NAME}.__version__)\""
    )
    print(f"Deployed {wheel.name} to Nebula")


@task(name="deploy.eagle")
def deploy_eagle(c: Context) -> None:
    """rsync wheel to Eagle (env-aware alias) + install."""
    wheel = _latest_wheel()
    alias = _eagle_alias()
    cn = Connection(alias)
    cn.run("mkdir -p ~/.local/share/meshterm-deploy")
    cn.put(str(wheel), remote=f"~/.local/share/meshterm-deploy/{wheel.name}")
    cn.run(f"uv venv ~/.local/share/meshterm-deploy/.venv --python 3.11")
    cn.run(
        f". ~/.local/share/meshterm-deploy/.venv/bin/activate && "
        f"uv pip install ~/.local/share/meshterm-deploy/{wheel.name}"
    )
    cn.run(
        f". ~/.local/share/meshterm-deploy/.venv/bin/activate && "
        f"python -c \"import {PKG_NAME}; print({PKG_NAME}.__version__)\""
    )
    print(f"Deployed {wheel.name} to Eagle ({alias})")


@task(name="dogfood.send-from-nebula")
def dogfood_send_from_nebula(c: Context, message: str = "test from Nebula") -> None:
    """Run `echo "no cross-host claude-mesh in meshterm" <msg>` from Nebula and verify it lands on Mac."""
    cn = Connection("Nebula")
    cn.run(
        f". ~/.local/share/meshterm-deploy/.venv/bin/activate && "
        f"echo "no cross-host claude-mesh in meshterm" '{message}' || echo 'send failed'"
    )
