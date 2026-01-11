"""YAML ruleset loader with integrity verification."""

import hashlib
from pathlib import Path
from typing import Any

import yaml

# Default rulesets directory
RULESETS_DIR = Path(__file__).parent.parent.parent / "rulesets"


def compute_ruleset_hash(content: str) -> str:
    """Compute SHA256 hash of ruleset content.

    Used for audit trail to ensure ruleset hasn't been modified.

    Args:
        content: Raw YAML content string

    Returns:
        SHA256 hex digest
    """
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def load_ruleset(
    filename: str,
    rulesets_dir: Path | None = None,
) -> tuple[dict[str, Any], str]:
    """Load a ruleset YAML file and compute its hash.

    Args:
        filename: Name of the ruleset file (e.g., "uk-private-triage-v1.0.0.yaml")
        rulesets_dir: Directory containing rulesets (defaults to /rulesets)

    Returns:
        Tuple of (parsed ruleset dict, SHA256 hash)

    Raises:
        FileNotFoundError: If ruleset file doesn't exist
        yaml.YAMLError: If YAML is invalid
    """
    if rulesets_dir is None:
        rulesets_dir = RULESETS_DIR

    filepath = rulesets_dir / filename

    if not filepath.exists():
        raise FileNotFoundError(f"Ruleset not found: {filepath}")

    content = filepath.read_text(encoding="utf-8")
    ruleset_hash = compute_ruleset_hash(content)
    ruleset = yaml.safe_load(content)

    return ruleset, ruleset_hash


class RulesetLoader:
    """Stateful ruleset loader with caching."""

    def __init__(self, rulesets_dir: Path | None = None) -> None:
        """Initialize loader.

        Args:
            rulesets_dir: Directory containing rulesets
        """
        self.rulesets_dir = rulesets_dir or RULESETS_DIR
        self._cache: dict[str, tuple[dict[str, Any], str]] = {}

    def load(self, filename: str, use_cache: bool = True) -> tuple[dict[str, Any], str]:
        """Load a ruleset with optional caching.

        Args:
            filename: Ruleset filename
            use_cache: Whether to use cached version if available

        Returns:
            Tuple of (ruleset dict, hash)
        """
        if use_cache and filename in self._cache:
            return self._cache[filename]

        ruleset, ruleset_hash = load_ruleset(filename, self.rulesets_dir)
        self._cache[filename] = (ruleset, ruleset_hash)

        return ruleset, ruleset_hash

    def clear_cache(self) -> None:
        """Clear the ruleset cache."""
        self._cache.clear()

    def list_rulesets(self) -> list[str]:
        """List available ruleset files.

        Returns:
            List of ruleset filenames
        """
        return [f.name for f in self.rulesets_dir.glob("*.yaml")]

    def get_ruleset_info(self, filename: str) -> dict[str, Any]:
        """Get metadata about a ruleset.

        Args:
            filename: Ruleset filename

        Returns:
            Dict with id, version, description, hash
        """
        ruleset, ruleset_hash = self.load(filename)

        return {
            "filename": filename,
            "id": ruleset.get("id", "unknown"),
            "version": ruleset.get("version", "unknown"),
            "description": ruleset.get("description", ""),
            "hash": ruleset_hash,
        }
