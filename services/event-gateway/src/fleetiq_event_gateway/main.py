"""Gateway process entry point."""

import os

from .config import GatewaySettings
from .handler import EventHandler
from .transport import PahoTransport


def main() -> None:
    settings = GatewaySettings.from_environment(os.environ)
    transport: PahoTransport
    handler: EventHandler
    transport = PahoTransport(settings, lambda topic, payload: handler.handle(topic, payload))
    handler = EventHandler(transport)
    transport.connect()
    handler.publish_status("online")
    try:
        transport.loop_forever()
    finally:
        try:
            handler.publish_status("offline")
        finally:
            transport.disconnect()


if __name__ == "__main__":
    main()
