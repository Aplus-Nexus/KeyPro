"""KeyPro desktop workflow studio.

Qt is the primary UI so macOS and Windows render the same dark editor surface.
The older Tk implementation remains in app_tk.py as a dependency-light fallback.
"""
from __future__ import annotations

try:
    from app_qt import main
except ImportError as exc:
    raise SystemExit("KeyPro needs PySide6. Install dependencies with: python -m pip install -r requirements.txt") from exc

if __name__ == "__main__":
    main()
