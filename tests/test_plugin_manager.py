"""Hermes PluginManager integration tests for the installed distribution path."""

import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.integration
class TestHermesPluginManager:
    def test_entry_point_discovers_and_registers_read_only_surface(self, tmp_path):
        wheel_dir = tmp_path / "wheel"
        site_dir = tmp_path / "site"
        wheel_dir.mkdir()
        subprocess.run(
            [sys.executable, "-m", "pip", "wheel", "--no-deps", ".", "-w", str(wheel_dir)],
            check=True,
            text=True,
            capture_output=True,
        )

        script = tmp_path / "plugin_smoke.py"
        script.write_text(
            """
from hermes_cli.plugins import PluginManager

manager = PluginManager()
manager.discover_and_load()
plugins = {plugin["name"]: plugin for plugin in manager.list_plugins()}
plugin = plugins["hermes-pmxt"]
assert plugin["enabled"] is True
assert plugin["tools"] == 7
assert manager.list_plugin_skills("hermes-pmxt") == ["pmxt"]
assert manager.find_plugin_skill("hermes-pmxt:pmxt").is_file()
print("plugin-manager smoke OK")
""".strip()
        )
        hermes_home = tmp_path / "hermes-home"
        hermes_home.mkdir()
        (hermes_home / "config.yaml").write_text("plugins:\n  enabled: [hermes-pmxt]\n")
        env = os.environ | {
            "HERMES_HOME": str(hermes_home),
            "PYTHONPATH": str(site_dir),
        }
        hermes_python = Path.home() / ".hermes/hermes-agent/venv/bin/python"
        if not hermes_python.exists():
            pytest.skip("Hermes runtime venv is unavailable")

        subprocess.run(
            [str(hermes_python), "-m", "pip", "install", "--no-deps", "--target", str(site_dir), *wheel_dir.glob("*.whl")],
            check=True,
            text=True,
            capture_output=True,
        )

        completed = subprocess.run(
            [str(hermes_python), str(script)],
            env=env,
            text=True,
            capture_output=True,
            timeout=30,
        )

        assert completed.returncode == 0, completed.stderr
        assert "plugin-manager smoke OK" in completed.stdout
