"""Unit tests for layers/execution.py — the Docker sandbox layer.

These tests require Docker to be running. They are marked with
``pytest.mark.docker`` so you can skip them on machines without Docker:

    pytest -m "not docker"
"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Try importing docker; skip the whole module gracefully if unavailable.
docker = pytest.importorskip("docker", reason="docker SDK not installed")

from layers.execution import execute


@pytest.fixture
def mock_docker_client():
    """Return a mocked Docker client for unit testing without a real daemon."""
    client = MagicMock(spec=docker.DockerClient)
    container = MagicMock()
    container.status = "exited"
    container.attrs = {"State": {"ExitCode": 0}}
    container.logs.return_value = b"hello world\n"
    client.containers.run.return_value = container
    return client


class TestExecuteMocked:
    """Tests using a mocked Docker client (no real Docker needed)."""

    def test_successful_command(self, mock_docker_client, tmp_path):
        result = execute(mock_docker_client, tmp_path, "echo hello", "coding-sandbox:local")
        assert result["exit_code"] == 0
        assert "hello world" in result["output"]

    def test_container_is_removed(self, mock_docker_client, tmp_path):
        execute(mock_docker_client, tmp_path, "echo hello", "coding-sandbox:local")
        mock_docker_client.containers.run.return_value.remove.assert_called_once_with(force=True)

    def test_timeout_kills_container(self, mock_docker_client, tmp_path):
        container = mock_docker_client.containers.run.return_value
        container.status = "running"  # never exits
        container.logs.return_value = b"still running..."
        result = execute(mock_docker_client, tmp_path, "sleep 999", "coding-sandbox:local", timeout=1)
        assert "error" in result
        container.kill.assert_called_once()


@pytest.mark.docker
class TestExecuteReal:
    """Integration tests that require a running Docker daemon and the sandbox image.

    Run with: pytest -m docker
    Build the image first: docker build -f Dockerfile.sandbox -t coding-sandbox:local .
    """

    @pytest.fixture
    def docker_client(self):
        try:
            client = docker.from_env()
            client.ping()
            return client
        except Exception:
            pytest.skip("Docker daemon not available")

    def test_echo(self, docker_client, tmp_path):
        result = execute(docker_client, tmp_path, "echo integration-test", "coding-sandbox:local")
        assert result["exit_code"] == 0
        assert "integration-test" in result["output"]

    def test_nonzero_exit(self, docker_client, tmp_path):
        result = execute(docker_client, tmp_path, "exit 42", "coding-sandbox:local")
        assert result["exit_code"] == 42
