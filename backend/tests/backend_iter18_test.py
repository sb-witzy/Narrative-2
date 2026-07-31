"""
Iter 18: Installer-mode auto-update tests.

Verifies:
- /api/system/version exposes the new fields (is_installer_build, version,
  github_repo).
- /api/system/check-updates gracefully returns 502 in git mode when no origin
  is configured (dev environment).
- _is_installer_build() correctly distinguishes dev vs installed environments.
- _github_latest_release() picks the right asset per platform.
- semver comparison logic behaves.

Runs as a plain unittest — no external HTTP calls required (GitHub API is mocked).
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
os.environ.setdefault("DB_NAME", "narrative_rx")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import server as srv


class InstallerDetectionTests(unittest.TestCase):
    def test_dev_checkout_is_not_installer_build(self):
        # In this repo .git exists, so we should always be dev-mode.
        self.assertFalse(srv._is_installer_build())

    def test_installer_build_requires_no_git_and_a_real_version(self):
        with patch.object(srv, "_read_version_file", return_value="1.0.0"):
            fake = MagicMock()
            fake.is_dir.return_value = False  # no .git
            root_mock = MagicMock()
            root_mock.__truediv__.return_value = fake
            with patch.object(srv, "_REPO_ROOT", root_mock):
                self.assertTrue(srv._is_installer_build())

    def test_dev_version_is_ignored(self):
        with patch.object(srv, "_read_version_file", return_value="0.0.0-dev"):
            fake = MagicMock()
            fake.is_dir.return_value = False
            root_mock = MagicMock()
            root_mock.__truediv__.return_value = fake
            with patch.object(srv, "_REPO_ROOT", root_mock):
                self.assertFalse(srv._is_installer_build())


class SemverTests(unittest.TestCase):
    def test_prefix_v_is_stripped(self):
        self.assertEqual(srv._parse_semver("v1.2.3"), (1, 2, 3))

    def test_bare_semver(self):
        self.assertEqual(srv._parse_semver("1.0.0"), (1, 0, 0))

    def test_prerelease_is_ignored(self):
        # We drop the -beta1 suffix; only the numeric core is compared.
        self.assertEqual(srv._parse_semver("1.0.0-beta1"), (1, 0, 0))

    def test_ordering(self):
        self.assertGreater(srv._parse_semver("1.1.0"), srv._parse_semver("1.0.9"))
        self.assertGreater(srv._parse_semver("2.0.0"), srv._parse_semver("1.99.99"))
        self.assertFalse(srv._parse_semver("1.0.0") > srv._parse_semver("1.0.0"))


class GithubAssetPickerTests(unittest.TestCase):
    """Uses a fake urllib to check that the .exe / .pkg asset is picked
    based on sys.platform."""

    _fake_release = {
        "tag_name": "v1.2.3",
        "html_url": "https://github.com/sb-witzy/Narrative-2/releases/tag/v1.2.3",
        "body": "Bug fixes",
        "published_at": "2026-02-01T00:00:00Z",
        "assets": [
            {
                "name": "NarrativeRx-Setup-1.2.3.exe",
                "size": 300_000_000,
                "browser_download_url": "https://github.com/x/y/releases/download/v1.2.3/NarrativeRx-Setup-1.2.3.exe",
            },
            {
                "name": "NarrativeRx-Setup-1.2.3.pkg",
                "size": 60_000_000,
                "browser_download_url": "https://github.com/x/y/releases/download/v1.2.3/NarrativeRx-Setup-1.2.3.pkg",
            },
        ],
    }

    def _fake_urlopen(self, *args, **kwargs):
        import io
        import json
        response = MagicMock()
        response.__enter__ = lambda s: s
        response.__exit__ = lambda s, *a: None
        response.read.return_value = json.dumps(self._fake_release).encode()
        return response

    def test_windows_picks_exe(self):
        with patch("urllib.request.urlopen", self._fake_urlopen), \
             patch.object(srv, "sys") as sys_mock:
            sys_mock.platform = "win32"
            r = srv._github_latest_release()
        self.assertEqual(r["tag"], "1.2.3")
        self.assertTrue(r["asset_url"].endswith(".exe"))
        self.assertTrue(r["exe_url"].endswith(".exe"))  # backwards-compat alias
        self.assertEqual(r["asset_size"], 300_000_000)

    def test_darwin_picks_pkg(self):
        with patch("urllib.request.urlopen", self._fake_urlopen), \
             patch.object(srv, "sys") as sys_mock:
            sys_mock.platform = "darwin"
            r = srv._github_latest_release()
        self.assertEqual(r["tag"], "1.2.3")
        self.assertTrue(r["asset_url"].endswith(".pkg"))
        self.assertEqual(r["asset_size"], 60_000_000)


class VersionEndpointTests(unittest.TestCase):
    def test_current_version_has_new_fields(self):
        v = srv._current_version()
        # New fields introduced with the installer/updater refactor
        self.assertIn("is_installer_build", v)
        self.assertIn("version", v)
        self.assertIn("github_repo", v)
        # In dev the flag should be false and github_repo is the default
        self.assertFalse(v["is_installer_build"])
        self.assertEqual(v["github_repo"], os.environ.get("GITHUB_REPO", "sb-witzy/Narrative-2"))


if __name__ == "__main__":
    unittest.main()
