# discover_jobs.py
"""CLI entry point for a job discovery run.

Usage:
    uv run python discover_jobs.py                 # full run
    uv run python discover_jobs.py --limit 5       # try a handful first
    uv run python discover_jobs.py --no-scoring    # skip the LLM scoring step
    uv run python discover_jobs.py --config path/to/criteria.json
"""

import sys
import argparse

from src.jobs.discovery import run


def _force_utf8_output() -> None:
    """Windows consoles default to cp1252, which can't encode the status emoji."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


def main() -> int:
    _force_utf8_output()
    parser = argparse.ArgumentParser(description="Discover job postings matching your criteria.")
    parser.add_argument("--config", default=None, help="Path to a criteria JSON file.")
    parser.add_argument("--limit", type=int, default=None, help="Only process N new postings.")
    parser.add_argument("--no-scoring", action="store_true", help="Skip LLM relevance scoring.")
    args = parser.parse_args()

    try:
        run(criteria_path=args.config, skip_scoring=args.no_scoring, limit=args.limit)
    except FileNotFoundError as e:
        print(e)
        return 1
    except ValueError as e:
        print(e)
        return 1
    except KeyboardInterrupt:
        print("\n\nInterrupted. Progress from completed stages was not saved.")
        return 130

    print("\nNext: run `uv run streamlit run app.py` and open the Job Discovery page.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
