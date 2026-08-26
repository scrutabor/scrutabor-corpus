"""Append new reader-edition identities to the tracked registries."""

from pathlib import Path

from build_reader.emit import update_registry


def main() -> None:
    corpus = Path(__file__).resolve().parent.parent
    changes = update_registry(corpus)
    summary = " ".join(f"{name}=+{count}" for name, count in changes.items())
    print(f"READER REGISTRY {summary}")


if __name__ == "__main__":
    main()
