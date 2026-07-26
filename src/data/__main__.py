"""Import smoke test for the data package."""

from src import __version__


def main() -> None:
    """Print the package version after all package imports succeed."""
    print(f"FormosaNLU data package {__version__}")


if __name__ == "__main__":
    main()
