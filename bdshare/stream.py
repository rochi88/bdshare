"""
bdshare.stream
~~~~~~~~~~~~~~~
Polling-based tick streaming over WebSockets.

DSE has no public push/streaming API — bdshare works by scraping dsebd.org
over HTTP. This module polls get_current_trade_data() on an interval and
broadcasts *changed* rows to connected WebSocket clients, so another program
can subscribe to near-real-time ticks over ws:// instead of polling bdshare
itself and reimplementing the diffing.

Run directly:
    python -m bdshare.stream --symbols GP,ACI --interval 5

Or via the installed console script:
    bdshare-stream --symbols GP,ACI --interval 5

Requires the optional 'stream' extra:
    pip install bdshare[stream]
"""
import argparse
import asyncio
import json
import logging
from typing import AsyncIterator, Dict, Iterable, List, Optional, Set

from bdshare.stock.trading import get_current_trade_data
from bdshare.util.helper import BDShareError

logger = logging.getLogger(__name__)

DEFAULT_INTERVAL = 5.0


def _snapshot(symbols: Optional[Iterable[str]] = None) -> Dict[str, dict]:
    """One live poll of current trade data, keyed by symbol."""
    df = get_current_trade_data()
    if symbols:
        wanted = {s.upper() for s in symbols}
        df = df[df["symbol"].isin(wanted)]
    return {row["symbol"]: row for row in df.to_dict(orient="records")}


def _changed_rows(previous: Dict[str, dict], current: Dict[str, dict]) -> List[dict]:
    """Rows in `current` that are new or differ from `previous`."""
    return [row for symbol, row in current.items() if previous.get(symbol) != row]


async def stream_ticks(
    symbols: Optional[Iterable[str]] = None,
    interval: float = DEFAULT_INTERVAL,
) -> AsyncIterator[List[dict]]:
    """Poll live trade data on an interval, yielding only changed rows each tick.

    Usable directly in any asyncio program, no WebSocket server required::

        async for changed in stream_ticks(symbols=['GP', 'ACI'], interval=5.0):
            print(changed)

    The first poll yields every matched row (there's no "previous" snapshot
    to diff against yet). A transient BDShareError is logged and the poll is
    retried after `interval` rather than raising, so one bad request doesn't
    kill the stream.
    """
    previous: Dict[str, dict] = {}
    while True:
        try:
            current = await asyncio.to_thread(_snapshot, symbols)
        except BDShareError as exc:
            logger.warning("Tick poll failed, will retry: %s", exc)
            await asyncio.sleep(interval)
            continue

        changed = _changed_rows(previous, current)
        previous = current
        if changed:
            yield changed
        await asyncio.sleep(interval)


class TickServer:
    """WebSocket server that broadcasts live DSE ticks to all connected clients.

    Example::

        server = TickServer(symbols=['GP', 'ACI'], interval=5.0)
        await server.serve(host='0.0.0.0', port=8765)

    Each connected client first receives the latest known snapshot
    (``{"type": "snapshot", "data": [...]}``), then a message per poll that
    actually changed anything (``{"type": "ticks", "data": [...]}``).
    """

    def __init__(self, symbols: Optional[Iterable[str]] = None, interval: float = DEFAULT_INTERVAL):
        self.symbols = list(symbols) if symbols else None
        self.interval = interval
        self._clients: Set = set()
        self._latest: Dict[str, dict] = {}

    async def _handler(self, websocket) -> None:
        self._clients.add(websocket)
        logger.info("Client connected (%d total)", len(self._clients))
        try:
            if self._latest:
                await websocket.send(
                    json.dumps({"type": "snapshot", "data": list(self._latest.values())})
                )
            async for _ in websocket:
                pass  # broadcast-only stream; inbound client messages are ignored
        finally:
            self._clients.discard(websocket)
            logger.info("Client disconnected (%d total)", len(self._clients))

    async def _broadcast_loop(self) -> None:
        async for changed in stream_ticks(self.symbols, self.interval):
            for row in changed:
                self._latest[row["symbol"]] = row
            if not self._clients:
                continue
            message = json.dumps({"type": "ticks", "data": changed})
            await asyncio.gather(
                *(client.send(message) for client in list(self._clients)),
                return_exceptions=True,
            )

    async def serve(self, host: str = "0.0.0.0", port: int = 8765) -> None:
        try:
            import websockets
        except ImportError as exc:
            raise ImportError(
                "WebSocket streaming requires the 'websockets' package. "
                "Install it with: pip install bdshare[stream]"
            ) from exc

        async with websockets.serve(self._handler, host, port):
            logger.info("bdshare tick stream listening on ws://%s:%d", host, port)
            await self._broadcast_loop()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Stream live DSE ticks over WebSockets.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument(
        "--interval", type=float, default=DEFAULT_INTERVAL,
        help="Seconds between polls of dsebd.org (default: %(default)s)",
    )
    parser.add_argument(
        "--symbols", default=None,
        help="Comma-separated symbols to filter (default: all instruments)",
    )
    args = parser.parse_args()

    symbols = [s.strip() for s in args.symbols.split(",")] if args.symbols else None
    server = TickServer(symbols=symbols, interval=args.interval)
    asyncio.run(server.serve(host=args.host, port=args.port))


if __name__ == "__main__":
    main()
