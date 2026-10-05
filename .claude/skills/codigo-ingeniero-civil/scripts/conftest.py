"""Permite `import civil` al correr pytest desde cualquier carpeta."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
