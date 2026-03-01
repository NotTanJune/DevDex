import os
import sys
import warnings

warnings.filterwarnings("ignore", message=".*doesn't match a supported version.*")

_pkg_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _pkg_root not in sys.path:
    sys.path.insert(0, _pkg_root)

from devdex.cli import app


def main():
    app()


if __name__ == "__main__":
    main()
