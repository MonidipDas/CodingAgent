"""Unit tests for layers/safety.py — the permission gating layer."""
import pytest
from layers.safety import is_command_safe, assert_safe


class TestIsCommandSafe:
    """Commands that should be BLOCKED."""

    @pytest.mark.parametrize("cmd", [
        "rm -rf /",
        "rm  -rf  /",
        "sudo rm -rf /home",
        "shutdown -h now",
        "reboot",
        "mkfs.ext4 /dev/sda1",
        "dd if=/dev/zero of=/dev/sda bs=1M",
    ])
    def test_dangerous_commands_blocked(self, cmd):
        assert is_command_safe(cmd) is False

    """Commands that should be ALLOWED."""

    @pytest.mark.parametrize("cmd", [
        "python -m pytest",
        "cat main.py",
        "ls -la",
        "echo hello",
        "grep -r 'TODO' .",
        "git status",
        "pip install requests",
        "rm file.txt",           # single file rm is fine
        "sed -i 's/old/new/g' file.py",
    ])
    def test_safe_commands_allowed(self, cmd):
        assert is_command_safe(cmd) is True


class TestAssertSafe:
    def test_raises_on_dangerous(self):
        with pytest.raises(ValueError, match="safety policy"):
            assert_safe("rm -rf /")

    def test_passes_on_safe(self):
        assert_safe("python -m pytest")  # should not raise
