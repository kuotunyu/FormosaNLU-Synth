"""Launch or validate the local FormosaNLU Gradio comparison demo."""

from __future__ import annotations

import argparse

from src.inference.demo import build_demo


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mock", action="store_true", help="Use deterministic model-free outputs")
    parser.add_argument(
        "--no-launch",
        action="store_true",
        help="Build the Blocks graph and exit without starting a server",
    )
    parser.add_argument("--share", action="store_true", help="Create a temporary Gradio share link")
    parser.add_argument("--port", type=int, default=7860)
    args = parser.parse_args()

    demo = build_demo(mock=args.mock)
    if args.no_launch:
        print("M11 demo graph built successfully")
        return 0
    demo.queue(default_concurrency_limit=1).launch(
        server_name="127.0.0.1",
        server_port=args.port,
        share=args.share,
        show_error=True,
        theme=demo.formosa_theme,
        css=demo.formosa_css,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
