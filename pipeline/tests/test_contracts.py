"""contracts/ is the one place shared schemas live (AGENTS.md)."""

from pathlib import Path

CONTRACTS = Path(__file__).resolve().parents[2] / "contracts"


def test_contracts_dir_is_documented() -> None:
    assert (CONTRACTS / "README.md").read_text().strip()
