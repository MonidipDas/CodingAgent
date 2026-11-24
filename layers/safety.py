"""Safety and permission gating utilities for the coding agent.
The purpose of this layer is to enforce simple safety policies before any
shell command is executed inside the sandbox. It mirrors the *Input &
Safety / Permission Layer* described in the Claude Code system design.
"""
import re

# Simple blacklist of disallowed command patterns. Extend as needed.
_BLACKLIST_PATTERNS = [
    r"rm\s+-rf\s+/",       # destructive recursive delete of root
    r"\bshutdown\b",
    r"\breboot\b",
    r":\(\)\{.*\}",         # fork bomb pattern
    r"\bmkfs\b",            # format filesystem
    r"\bdd\s+if=.+of=/dev", # raw device writes
]


def is_command_safe(command: str) -> bool:
    """Return True if the command does not match any black-list pattern.

    Args:
        command: The shell command string about to be executed.
    """
    for pat in _BLACKLIST_PATTERNS:
        if re.search(pat, command):
            return False
    return True


def assert_safe(command: str) -> None:
    """Raise a ValueError if the command is unsafe."""
    if not is_command_safe(command):
        raise ValueError("Command violates safety policy and is blocked")
