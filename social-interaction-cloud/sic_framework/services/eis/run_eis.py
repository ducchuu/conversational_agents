import sys
import time
import signal
import argparse

from sic_framework.services.eis.eiscomponent import EISConnector, EISConf

def signal_handler(signum, frame):
    """Handle termination signals and clean up."""
    print("Shutting down EISComponent...")
    if eis:
        eis.close()
    sys.exit(0)

def main():
    global eis
    parser = argparse.ArgumentParser(description="Run EIS component")
    parser.add_argument("--use-nlu", default=False, action="store_true", help="Force NLU path (non-Dialogflow)")
    parser.add_argument("--use-whisper", default=False, action="store_true", help="Force Whisper instead of Google STT")
    parser.add_argument("--no-espeak", default=False, action="store_true", help="Use cloud TTS instead of espeak")
    # Parse args so the flags are available in sys.argv for EISComponent
    args = parser.parse_args()

    eis_conf = EISConf(
        use_whisper=args.use_whisper,
        nlu=args.use_nlu,
        use_espeak=not args.no_espeak,
    )

    eis = EISConnector(conf=eis_conf)
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    # Keep the component running
    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
