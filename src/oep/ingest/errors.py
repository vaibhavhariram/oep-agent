"""Typed exceptions for manifest and packet verification."""

from __future__ import annotations


class ManifestError(Exception):
    """Base for all manifest verification errors."""


class ClaimNotFoundError(ManifestError):
    """Claim ID not present in dataset_index.json."""


class MissingFileError(ManifestError):
    """A registered document file is not present on disk."""


class ExtraFileError(ManifestError):
    """An unregistered file exists in the claim directory."""


class HashMismatchError(ManifestError):
    """SHA-256 of file on disk does not match the index entry."""


class PathTraversalError(ManifestError):
    """A document path contains traversal sequences (e.g. ``..``)."""


class FileUnreadableError(ManifestError):
    """File exists but cannot be opened for reading."""
