"""Unit tests for layers/knowledge.py — the retrieval / context layer."""
import os
import pytest
from pathlib import Path

from layers.knowledge import retrieve


@pytest.fixture
def sample_workspace(tmp_path):
    """Create a small mock workspace with a few Python files."""
    (tmp_path / "main.py").write_text(
        "def greet(name):\n    return f'Hello, {name}!'\n\nif __name__ == '__main__':\n    print(greet('World'))\n"
    )
    (tmp_path / "utils.py").write_text(
        "import math\n\ndef circle_area(radius):\n    return math.pi * radius ** 2\n"
    )
    (tmp_path / "README.md").write_text("# Sample Project\nA demo project for testing retrieval.\n")
    (tmp_path / "data.json").write_text('{"key": "value"}')  # unsupported extension
    # hidden dir — should be skipped
    hidden = tmp_path / ".git"
    hidden.mkdir()
    (hidden / "config").write_text("bare = false")
    return tmp_path


class TestRetrieve:
    def test_returns_string(self, sample_workspace):
        result = retrieve(sample_workspace, "greet function")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_finds_relevant_content(self, sample_workspace):
        result = retrieve(sample_workspace, "greet name hello")
        # The retrieved context should contain something from main.py
        assert "main.py" in result

    def test_skips_hidden_dirs(self, sample_workspace):
        result = retrieve(sample_workspace, "git config")
        assert ".git" not in result

    def test_skips_unsupported_extensions(self, sample_workspace):
        result = retrieve(sample_workspace, "key value json")
        assert "data.json" not in result

    def test_empty_workspace(self, tmp_path):
        result = retrieve(tmp_path, "anything")
        assert result == "Repository has no indexed source files."

    def test_respects_max_length(self, sample_workspace):
        result = retrieve(sample_workspace, "circle area radius")
        assert len(result) <= 16000
