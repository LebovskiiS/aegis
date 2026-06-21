"""Container control plane: drive the Aegis engine image via the `docker` CLI.

The heavy engine (FastAPI + embeddings + vault) ships as a container image. This
thin CLI only *orchestrates* it — pull / run / inspect / logs — and never imports it.
It shells out to `docker` (no SDK) so the CLI's dependency surface stays tiny, which
is what lets it ship through Homebrew / pipx as a lightweight control plane.

Defaults are overridable via env (AEGIS_IMAGE, AEGIS_CONTAINER) or CLI flags.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys

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


def _inspect(docker: str, name: str) -> dict | None:
    """`docker inspect` one container as a dict, or None if it doesn't exist."""
    r = subprocess.run([docker, "inspect", name], capture_output=True, text=True)
    if r.returncode != 0:
        return None
    try:
        return json.loads(r.stdout)[0]
    except (json.JSONDecodeError, IndexError):
        return None


def _ports(inspect: dict) -> list[str]:
    """Human-readable published port maps, e.g. '127.0.0.1:8080→8080/tcp'."""
    out: list[str] = []
    for cport, binds in (inspect.get("NetworkSettings", {}).get("Ports") or {}).items():
        for b in binds or []:
            host = b.get("HostIp") or "0.0.0.0"
            out.append(f"{host}:{b['HostPort']}→{cport}")
        if not binds:
            out.append(f"{cport} (not published)")
    return out


def up(
    image: str = IMAGE,
    name: str = NAME,
    port: int = 8080,
    bind: str = "127.0.0.1",
    mem: str = "1g",
    cpus: str = "1",
    pull: bool = True,
) -> None:
    """Pull (optional) and run the engine container, detached, with a forwarded port."""
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
            "-p", f"{bind}:{port}:8080",      # forward host {bind}:{port} → container 8080
            "--memory", mem, "--memory-swap", mem,  # hard RAM cap, no swap blow-up
            "--cpus", cpus,
            "--restart", "unless-stopped",
            image,
        ],
        check=True,
    )
    where = f"http://{bind}:{port}" if bind not in ("0.0.0.0", "::") else f"http://<host>:{port}"
    if bind in ("0.0.0.0", "::"):
        print(f"⚠  bound to {bind} — reachable off-host; put auth + TLS in front (breaks air-gap).")
    print(f"🛡  aegis up → {where}  (container '{name}', {bind}:{port}→8080)")
    print('   try: aegis status   |   aegis locate "how do I stream a response" --lib fastapi')


def down(name: str = NAME) -> None:
    """Stop and remove the engine container."""
    docker = _require_docker()
    r = subprocess.run([docker, "rm", "-f", name], capture_output=True, text=True)
    if r.returncode == 0:
        print(f"✓ stopped + removed container '{name}'")
    else:
        print(f"no container '{name}' to stop ({r.stderr.strip()})")


def restart(name: str = NAME) -> None:
    """Restart the engine container in place (keeps the same config + vault)."""
    docker = _require_docker()
    r = subprocess.run([docker, "restart", name], capture_output=True, text=True)
    if r.returncode == 0:
        print(f"✓ restarted '{name}'")
    else:
        print(f"cannot restart '{name}': {r.stderr.strip()} — try `aegis up`")


def status(name: str = NAME) -> None:
    """Show the engine container's state, health, image and forwarded ports."""
    docker = _require_docker()
    data = _inspect(docker, name)
    if not data:
        print(f"container '{name}' not found — run `aegis up`")
        return
    state = data.get("State", {})
    health = state.get("Health", {}).get("Status")
    ports = _ports(data)
    line = state.get("Status", "?")
    if health:
        line += f"  (health: {health})"
    print(f"name     {data.get('Name', name).lstrip('/')}")
    print(f"state    {line}")
    print(f"image    {data.get('Config', {}).get('Image', '?')}")
    print(f"ports    {', '.join(ports) if ports else '(none published)'}")
    print(f"started  {state.get('StartedAt', '?')}")


def logs(name: str = NAME, follow: bool = False, tail: str = "50") -> None:
    """Stream the engine container's logs."""
    docker = _require_docker()
    args = ["logs", "--tail", tail]
    if follow:
        args.append("-f")
    args.append(name)
    subprocess.run([docker, *args])


def stats(name: str = NAME) -> None:
    """One-shot CPU / memory / net usage for the engine container."""
    docker = _require_docker()
    subprocess.run([docker, "stats", "--no-stream", name])


def exec_(name: str = NAME, cmd: list[str] | None = None) -> None:
    """Run a command inside the engine container (default: an interactive shell).

    Allocate a TTY only when actually attached to one, so piped/non-interactive
    use (`aegis exec ls`) doesn't fail with "the input device is not a TTY".
    """
    docker = _require_docker()
    flags = ["-i"]
    if sys.stdin.isatty() and sys.stdout.isatty():
        flags.append("-t")
    subprocess.run([docker, "exec", *flags, name, *(cmd or ["sh"])])


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
