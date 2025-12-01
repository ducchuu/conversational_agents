import sys
from sic_framework.services.eis.eiscomponent import EISConnector
import time

import sys
import signal

def signal_handler(signum, frame):
    """Handle termination signals and clean up."""
    print("Shutting down EISComponent...")
    if eis:
        eis.close()
    sys.exit(0)

def main():
    global eis
    eis = EISConnector()
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    # Keep the component running
    while True:
        time.sleep(1)

if __name__ == "__main__":
    main()
