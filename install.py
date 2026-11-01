#!/usr/bin/env python3
"""Install the portable Parler skill and its Codex integrations."""
from pathlib import Path
import runpy

runpy.run_path(str(Path(__file__).parent / "skills/parler-use/scripts/install.py"), run_name="__main__")
