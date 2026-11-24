"""Execution and sandbox dispatch layer for the coding agent.
Provides a thin wrapper around Docker to run shell commands in a restricted
environment, mirroring the original `execute` function from `agent.py`.
"""
import time
import docker
from pathlib import Path

def execute(client: docker.DockerClient, workspace: Path, command: str, image: str, timeout: int = 60) -> dict:
    """Run a command inside a sandboxed Docker container.

    Args:
        client: Docker client instance.
        workspace: Path to the writable workspace mounted inside the container.
        command: Shell command to execute.
        image: Docker image name for the sandbox.
        timeout: Maximum seconds to allow the command to run.
    Returns:
        A dictionary with either `exit_code` and `output` or an `error` key.
    """
    container = client.containers.run(
        image,
        ["sh", "-lc", command],
        detach=True,
        working_dir="/workspace",
        user="65534:65534",
        volumes={str(workspace): {"bind": "/workspace", "mode": "rw"}},
        network_disabled=True,
        read_only=True,
        cap_drop=["ALL"],
        security_opt=["no-new-privileges:true"],
        mem_limit="512m",
        nano_cpus=1_000_000_000,
        pids_limit=128,
        tmpfs={"/tmp": "rw,nosuid,nodev,size=128m,mode=1777"},
        log_config=docker.types.LogConfig(type="json-file", config={"max-size": "1m", "max-file": "1"}),
    )
    try:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            container.reload()
            if container.status == "exited":
                return {
                    "exit_code": container.attrs["State"]["ExitCode"],
                    "output": container.logs(tail=200).decode(errors="replace")[-12000:],
                }
            time.sleep(0.5)
        container.kill()
        return {"error": "Command exceeded time limit", "output": container.logs(tail=100).decode(errors="replace")[-6000:]}
    finally:
        container.remove(force=True)
