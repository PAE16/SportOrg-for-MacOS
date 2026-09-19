import subprocess
import sys
from pathlib import Path

import builder


def test_builder_requires_command():
    repo_root = Path(__file__).resolve().parents[1]

    completed = subprocess.run(
        [sys.executable, "builder.py"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    combined_output = (completed.stdout + completed.stderr).lower()
    assert "no build command supplied" in combined_output
    assert "python builder.py build" in combined_output


def test_macos_icon_resolver_uses_existing_icns(monkeypatch, tmp_path):
    icon_dir = tmp_path / "icon"
    icon_dir.mkdir()
    expected = icon_dir / "sportorg.icns"
    expected.write_bytes(b"stub")

    monkeypatch.setattr(builder.config, "ICON_DIR", str(icon_dir))

    assert builder.resolve_macos_icon() == str(expected)
