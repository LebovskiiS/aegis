"""Container control plane: drive the Aegis engine image via the `docker` CLI.

The heavy engine (FastAPI + embeddings + vault) ships as a container image. This
thin CLI only *orchestrates* it — pull / run / stop / logs — and never imports it.
It shells out to `docker` (no SDK) so the CLI's dependency surface stays tiny, which
is what lets it ship through Homebrew / pipx as a lightweight control plane.

Defaults are overridable via env (AEGIS_IMAGE, AEGIS_CONTAINER) or CLI flags.
"""
from __future__ import annotations

import os
import shutil
import subprocess

# Public engine image on Docker Hub; override with --image or AEGIS_IMAGE.
IMAGE = os.getenv("AEGIS_IMAGE", "lebovskiis/aegis:latest")
NAME = os.getenv("AEGIS_CONTAINER", "aegis")


def docker_path() -> str | None:
    """Path to the `docker` executable, or None if it isn't installed."""
    return shutil.which("docker")


def _require_docker() -> str:
    exe = docker_path()
    if not exe:
        raise SystemExit(
            "docker not found. Aegis runs its engine in a container; install Docker "
            "first (https://docs.docker.com/get-docker/), then run `aegis doctor`."
        )
    return exe


def up(
    image: str = IMAGE,
    name: str = NAME,
    port: int = 8080,
    mem: str = "1g",
    cpus: str = "1",
    pull: bool = True,
) -> None:
    """Pull (optional) and run the engine container, detached, on loopback only."""
    docker = _require_docker()
    if pull:
        print(f"→ pulling {image}")
        subprocess.run([docker, "pull", image], check=True)
    # Replace any stale container with the same name (ignore "not found").
    subprocess.run([docker, "rm", "-f", name], capture_output=True, text=True)
    subprocess.run(
        [
            docker, "run", "-d",
            "--name", name,
            "-p", f"127.0.0.1:{port}:8080",   # loopback only — never expose publicly
            "--memory", mem, "--memory-swap", mem,  # hard RAM cap, no swap blow-up
            "--cpus", cpus,
            "--restart", "unless-stopped",
            image,
        ],
        check=True,
    )
    print(f"🛡  aegis up → http://127.0.0.1:{port}  (container '{name}')")
    print('   try: aegis health   |   aegis locate "how do I stream a response" --lib fastapi')


def down(name: str = NAME) -> None:
    """Stop and remove the engine container."""
    docker = _require_docker()
    r = subprocess.run([docker, "rm", "-f", name], capture_output=True, text=True)
    if r.returncode == 0:
        print(f"✓ stopped + removed container '{name}'")
    else:
        print(f"no container '{name}' to stop ({r.stderr.strip()})")


def status(name: str = NAME) -> None:
    """Show the engine container's state (running / exited / absent)."""
    docker = _require_docker()
    r = subprocess.run(
        [docker, "ps", "-a", "--filter", f"name=^{name}$",
         "--format", "{{.Names}}\t{{.Status}}\t{{.Ports}}"],
        capture_output=True, text=True,
    )
    out = r.stdout.strip()
    print(out if out else f"container '{name}' not found — run `aegis up`")


def logs(name: str = NAME, follow: bool = False, tail: str = "50") -> None:
    """Stream the engine container's logs."""
    docker = _require_docker()
    args = ["logs", "--tail", tail]
    if follow:
        args.append("-f")
    args.append(name)
    subprocess.run([docker, *args])


def doctor(image: str = IMAGE, name: str = NAME) -> None:
    """Preflight: is Docker installed, is the daemon up, is the image present?"""
    ok = True
    exe = docker_path()
    if exe:
        print(f"✓ docker          {exe}")
        info = subprocess.run([exe, "info"], capture_output=True, text=True)
        if info.returncode == 0:
            print("✓ docker daemon   running")
        else:
            print("✗ docker daemon   not running → start Docker Desktop / the daemon")
            ok = False
        img = subprocess.run([exe, "image", "inspect", image], capture_output=True, text=True)
        if img.returncode == 0:
            print(f"✓ image           {image}")
        else:
            print(f"· image           not pulled yet — `aegis up` will fetch it ({image})")
    else:
        print("✗ docker          not found → https://docs.docker.com/get-docker/")
        ok = False
    print("\n" + ("ready — run `aegis up`" if ok else "fix the ✗ items above, then re-run `aegis doctor`"))
    raise SystemExit(0 if ok else 1)
