"""
api package - Exposes the Modrinth API client globally.
"""

from .modrith import ModrinthAPIConfig  # The singleton instance

__all__ = ["ModrinthAPIConfig"]