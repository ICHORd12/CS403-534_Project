from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"

# Ensure src-layout imports work during unittest discovery in VS Code.
if str(SRC_DIR) not in sys.path:
	sys.path.insert(0, str(SRC_DIR))
