"""Run directly from a checkout, or install the artwork-music entry point."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))
from artwork_music.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())

