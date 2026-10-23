"""Compatibility entry point for deployments that import ``JobS``."""

from app import app

__all__ = ["app"]


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
