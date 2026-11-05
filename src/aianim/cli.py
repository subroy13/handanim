"""Simplified CLI for aianim.

Two primary modes:
1. Interactive Assistant: For human users with AWS Bedrock seeking full control and visibility.
   Usage: `aianim` (or `handanim-ai`)
2. MCP Server: For agentic systems (Claude Desktop, Claude Code, Cursor, Gemini) to generate,
   inspect, and see animations directly.
   Usage: `aianim mcp`
"""

import argparse

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from .interactive import InteractiveSession
from .mcp_server import HandanimMCPServer
from .models import get_model


def main():
    parser = argparse.ArgumentParser(
        prog="aianim",
        description="aianim: AI Agentic Studio combining whiteboard drawing (handanim) and voice synthesis (voiceanim).",
    )
    subparsers = parser.add_subparsers(dest="command")

    # 1. interactive (default mode)
    interactive_parser = subparsers.add_parser(
        "interactive",
        aliases=["chat"],
        help="Launch the interactive Bedrock animation assistant (default).",
    )
    interactive_parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Bedrock model or inference profile ID (defaults to .env AWS_BEDROCK_MODEL_ID)",
    )
    interactive_parser.add_argument(
        "-o",
        "--output-dir",
        type=str,
        default=".",
        help="Directory to save rendered animations (default: current directory)",
    )
    interactive_parser.add_argument(
        "--no-verbose",
        action="store_true",
        help="Disable under-the-hood prompt printing during the session",
    )

    # 2. mcp server
    subparsers.add_parser(
        "mcp",
        help="Launch the MCP (Model Context Protocol) stdio server for Claude/Cursor/Gemini.",
    )

    args = parser.parse_args()

    # Route commands:
    if args.command == "mcp":
        server = HandanimMCPServer()
        server.run()
    else:
        # Default to interactive Bedrock assistant
        model_id = getattr(args, "model", None)
        output_dir = getattr(args, "output_dir", ".")
        verbose = not getattr(args, "no_verbose", False)

        model = get_model(provider="bedrock", model_name=model_id)
        session = InteractiveSession(model=model, verbose=verbose, output_dir=output_dir)
        session.run()


if __name__ == "__main__":
    main()
