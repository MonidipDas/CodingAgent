"""Unit tests for layers/orchestrator.py — the master agent loop.

The orchestrator depends on Docker + Groq API, so these tests mock both.
"""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

from layers.orchestrator import run_agent


@pytest.fixture
def workspace(tmp_path):
    """Create a minimal workspace with one file."""
    (tmp_path / "hello.py").write_text("print('hello')\n")
    return tmp_path


@pytest.fixture
def mock_env(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key-not-real")
    monkeypatch.setenv("AGENT_MODEL", "test-model")


class TestRunAgent:
    def test_missing_api_key_raises(self, workspace, monkeypatch):
        monkeypatch.delenv("GROQ_API_KEY", raising=False)
        with pytest.raises(EnvironmentError, match="GROQ_API_KEY"):
            run_agent(workspace, "do something")

    def test_invalid_workspace_raises(self, tmp_path, mock_env):
        fake = tmp_path / "nonexistent"
        with pytest.raises((ValueError, FileNotFoundError)):
            run_agent(fake, "do something")

    def test_invalid_steps_raises(self, workspace, mock_env):
        with pytest.raises(ValueError, match="steps"):
            run_agent(workspace, "do something", steps=0)

    @patch("layers.orchestrator.docker")
    @patch("layers.orchestrator.OpenAI")
    def test_agent_completes_on_final(self, MockOpenAI, mock_docker, workspace, mock_env, capsys):
        # Mock the LLM to immediately return a "final" response
        mock_llm = MockOpenAI.return_value
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({"final": "Task completed successfully."})
        mock_llm.chat.completions.create.return_value = mock_response

        # Mock Docker
        mock_docker.from_env.return_value.ping.return_value = True

        run_agent(workspace, "say hello", steps=5)

        captured = capsys.readouterr()
        assert "Task completed successfully" in captured.out

    @patch("layers.orchestrator.docker")
    @patch("layers.orchestrator.OpenAI")
    @patch("layers.orchestrator.execute")
    def test_agent_executes_command(self, mock_execute, MockOpenAI, mock_docker, workspace, mock_env, capsys):
        mock_llm = MockOpenAI.return_value

        # First call: return a command. Second call: return final.
        resp_cmd = MagicMock()
        resp_cmd.choices = [MagicMock()]
        resp_cmd.choices[0].message.content = json.dumps({"command": "echo hello"})

        resp_final = MagicMock()
        resp_final.choices = [MagicMock()]
        resp_final.choices[0].message.content = json.dumps({"final": "Done after running echo."})

        mock_llm.chat.completions.create.side_effect = [resp_cmd, resp_final]
        mock_execute.return_value = {"exit_code": 0, "output": "hello\n"}
        mock_docker.from_env.return_value.ping.return_value = True

        run_agent(workspace, "run echo", steps=5)

        mock_execute.assert_called_once()
        captured = capsys.readouterr()
        assert "Done after running echo" in captured.out
