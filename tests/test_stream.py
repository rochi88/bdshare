# _*_ coding:utf-8 _*_
'''
Tests for bdshare.stream (polling-based WebSocket tick streaming).

Uses a mocked get_current_trade_data() throughout — this module's job is to
poll/diff/broadcast correctly, not to re-verify live DSE data (covered by
tests/test_trading.py).
'''
import asyncio
import json
import unittest
from unittest.mock import patch

import pandas as pd

try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False

from bdshare.stream import _changed_rows, stream_ticks, TickServer
from bdshare.util.helper import BDShareError


def _fake_df(rows):
    return pd.DataFrame(rows)


class TestChangedRows(unittest.TestCase):

    def test_new_symbol_is_changed(self):
        current = {"GP": {"symbol": "GP", "ltp": 250.0}}
        self.assertEqual(_changed_rows({}, current), [current["GP"]])

    def test_unchanged_row_not_included(self):
        row = {"symbol": "GP", "ltp": 250.0}
        self.assertEqual(_changed_rows({"GP": row}, {"GP": dict(row)}), [])

    def test_changed_value_included(self):
        previous = {"GP": {"symbol": "GP", "ltp": 250.0}}
        current = {"GP": {"symbol": "GP", "ltp": 251.0}}
        self.assertEqual(_changed_rows(previous, current), [current["GP"]])


class TestStreamTicks(unittest.IsolatedAsyncioTestCase):

    async def test_first_poll_yields_everything(self):
        rows = [{"symbol": "GP", "ltp": 250.0}, {"symbol": "ACI", "ltp": 200.0}]
        with patch("bdshare.stream.get_current_trade_data", return_value=_fake_df(rows)):
            first = await stream_ticks(interval=0.01).__anext__()
        self.assertEqual({r["symbol"] for r in first}, {"GP", "ACI"})

    async def test_second_poll_only_yields_changes(self):
        calls = iter([
            [{"symbol": "GP", "ltp": 250.0}],
            [{"symbol": "GP", "ltp": 251.0}],
        ])
        with patch("bdshare.stream.get_current_trade_data", side_effect=lambda *a, **k: _fake_df(next(calls))):
            gen = stream_ticks(interval=0.01)
            first = await gen.__anext__()
            second = await gen.__anext__()
        self.assertEqual(first[0]["ltp"], 250.0)
        self.assertEqual(second[0]["ltp"], 251.0)

    async def test_bdshare_error_is_skipped_not_raised(self):
        calls = iter([BDShareError("boom"), [{"symbol": "GP", "ltp": 250.0}]])

        def fake_fetch(*args, **kwargs):
            item = next(calls)
            if isinstance(item, Exception):
                raise item
            return _fake_df(item)

        with patch("bdshare.stream.get_current_trade_data", side_effect=fake_fetch):
            first = await stream_ticks(interval=0.01).__anext__()
        self.assertEqual(first[0]["symbol"], "GP")

    async def test_symbol_filter(self):
        rows = [{"symbol": "GP", "ltp": 250.0}, {"symbol": "ACI", "ltp": 200.0}]
        with patch("bdshare.stream.get_current_trade_data", return_value=_fake_df(rows)):
            first = await stream_ticks(symbols=["gp"], interval=0.01).__anext__()
        self.assertEqual([r["symbol"] for r in first], ["GP"])


@unittest.skipUnless(WEBSOCKETS_AVAILABLE, "websockets is not installed")
class TestTickServer(unittest.IsolatedAsyncioTestCase):

    async def test_client_receives_broadcast_ticks(self):
        calls = iter([
            [{"symbol": "GP", "ltp": 250.0}],
            [{"symbol": "GP", "ltp": 251.0}],
        ])
        with patch("bdshare.stream.get_current_trade_data", side_effect=lambda *a, **k: _fake_df(next(calls))):
            server = TickServer(interval=0.05)
            async with websockets.serve(server._handler, "127.0.0.1", 0) as ws_server:
                port = ws_server.sockets[0].getsockname()[1]
                # Connect before the first poll completes so _latest is still
                # empty at connect time — no snapshot message, ticks only.
                async with websockets.connect(f"ws://127.0.0.1:{port}") as client:
                    broadcast_task = asyncio.create_task(server._broadcast_loop())
                    try:
                        msg1 = json.loads(await asyncio.wait_for(client.recv(), timeout=2))
                        self.assertEqual(msg1["type"], "ticks")
                        self.assertEqual(msg1["data"][0]["ltp"], 250.0)

                        msg2 = json.loads(await asyncio.wait_for(client.recv(), timeout=2))
                        self.assertEqual(msg2["data"][0]["ltp"], 251.0)
                    finally:
                        broadcast_task.cancel()

    async def test_late_client_receives_snapshot_on_connect(self):
        rows = [{"symbol": "GP", "ltp": 250.0}]
        with patch("bdshare.stream.get_current_trade_data", return_value=_fake_df(rows)):
            server = TickServer(interval=0.05)
            async with websockets.serve(server._handler, "127.0.0.1", 0) as ws_server:
                port = ws_server.sockets[0].getsockname()[1]
                broadcast_task = asyncio.create_task(server._broadcast_loop())
                try:
                    # Let at least one poll land in server._latest before connecting.
                    await asyncio.sleep(0.15)
                    async with websockets.connect(f"ws://127.0.0.1:{port}") as client:
                        msg = json.loads(await asyncio.wait_for(client.recv(), timeout=2))
                        self.assertEqual(msg["type"], "snapshot")
                        self.assertEqual(msg["data"][0]["symbol"], "GP")
                finally:
                    broadcast_task.cancel()


if __name__ == "__main__":
    unittest.main(verbosity=2)
