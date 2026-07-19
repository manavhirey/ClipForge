import argparse
import sys
from pathlib import Path

import anthropic
from dotenv import find_dotenv, load_dotenv

from clipforge.clients import ElevenLabsTTSClient
from clipforge.config import load_config
from clipforge.pipeline import Clients, run_pipeline

DEFAULT_OUTPUT_ROOT = Path("output")
DEFAULT_GAMEPLAY_LIBRARY = Path("assets/gameplay")


def main(argv=None) -> int:
    load_dotenv(find_dotenv(usecwd=True))
    parser = argparse.ArgumentParser(prog="clipforge")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run_parser = subparsers.add_parser("run", help="Generate a video from a Reddit post URL")
    run_parser.add_argument("url")
    run_parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    if args.command == "run":
        try:
            config = load_config()
            llm_client = anthropic.Anthropic(api_key=config.anthropic_api_key)
            tts_client = ElevenLabsTTSClient(api_key=config.elevenlabs_api_key)
            clients = Clients(llm=llm_client, tts=tts_client, voice_id=config.elevenlabs_voice_id)
            final_path = run_pipeline(
                args.url, DEFAULT_OUTPUT_ROOT, DEFAULT_GAMEPLAY_LIBRARY, clients, force=args.force
            )
        except Exception as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1
        print(f"Done: {final_path}")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
