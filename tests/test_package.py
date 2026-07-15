from pathlib import Path

import aioscrapy


def test_package_version_matches_version_file():
    version_file = Path(__file__).parents[1] / "aioscrapy" / "VERSION"

    assert aioscrapy.__version__ == version_file.read_text(encoding="ascii").strip()

