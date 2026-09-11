"""Unit tests for bubblewrap CLI compatibility probes."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from energy_core.platform.modules.isolation.sandbox import bwrap_compat


def test_bwrap_supports_no_new_privs_detects_unknown_option():
    with patch.object(bwrap_compat.subprocess, "run", return_value=MagicMock(returncode=1, stderr=b"Unknown option --no-new-privs")):
        bwrap_compat.bwrap_supports_no_new_privs.cache_clear()
        assert bwrap_compat.bwrap_supports_no_new_privs("/usr/bin/bwrap") is False


def test_bwrap_supports_rlimit_detects_unknown_option():
    with patch.object(bwrap_compat.subprocess, "run", return_value=MagicMock(returncode=1, stderr=b"Unknown option --rlimit")):
        bwrap_compat.bwrap_supports_rlimit.cache_clear()
        assert bwrap_compat.bwrap_supports_rlimit("/usr/bin/bwrap") is False


def test_bwrap_supports_no_new_privs_when_option_works():
    with patch.object(bwrap_compat.subprocess, "run", return_value=MagicMock(returncode=0, stderr=b"")):
        bwrap_compat.bwrap_supports_no_new_privs.cache_clear()
        assert bwrap_compat.bwrap_supports_no_new_privs("/usr/bin/bwrap") is True
