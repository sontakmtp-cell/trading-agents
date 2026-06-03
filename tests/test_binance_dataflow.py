import copy
import unittest
from unittest import mock

import pandas as pd

from tradingagents.dataflows import binance, interface
from tradingagents.dataflows.config import set_config
from tradingagents.dataflows.symbol_utils import NoMarketDataError
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.graph.trading_graph import TradingAgentsGraph


class BinanceDataflowTests(unittest.TestCase):
    def setUp(self):
        set_config(copy.deepcopy(DEFAULT_CONFIG))

    def test_normalizes_common_pair_spellings(self):
        self.assertEqual(binance.normalize_binance_symbol("btc-usdt"), "BTCUSDT")
        self.assertEqual(binance.normalize_binance_symbol("BTC/USDT"), "BTCUSDT")
        self.assertEqual(binance.normalize_binance_symbol("BTCUSDT"), "BTCUSDT")
        self.assertEqual(binance.normalize_binance_symbol("BTC-USD"), "BTCUSDT")

    def test_parse_klines_filters_after_analysis_date(self):
        klines = [
            [1767139200000, "100", "110", "90", "105", "12"],
            [1767225600000, "105", "120", "101", "115", "15"],
        ]

        data = binance.parse_klines(klines, curr_date="2025-12-31")

        self.assertEqual(list(data.columns), ["Date", "Open", "High", "Low", "Close", "Volume"])
        self.assertEqual(len(data), 1)
        self.assertEqual(data.iloc[0]["Date"], pd.Timestamp("2025-12-31"))
        self.assertEqual(data.iloc[0]["Close"], 105)

    def test_binance_only_route_does_not_fallback_to_yahoo(self):
        set_config(
            {
                "data_vendors": {
                    "core_stock_apis": "binance",
                    "technical_indicators": "binance",
                }
            }
        )

        def raises_no_data(symbol, *args, **kwargs):
            raise NoMarketDataError(symbol, "FAKEUSDT", "symbol not found")

        def yahoo_should_not_run(*args, **kwargs):
            raise AssertionError("Yahoo fallback should not run in Binance mode")

        patched = {
            "get_stock_data": {
                "binance": raises_no_data,
                "yfinance": yahoo_should_not_run,
            }
        }
        with mock.patch.dict(interface.VENDOR_METHODS, patched, clear=False):
            result = interface.route_to_vendor(
                "get_stock_data", "FAKEUSDT", "2026-01-01", "2026-01-10"
            )

        self.assertIn("NO_DATA_AVAILABLE", result)
        self.assertIn("FAKEUSDT", result)
        self.assertNotIn("yfinance", result)

    def test_binance_returns_use_binance_ohlcv(self):
        btc = pd.DataFrame(
            {
                "Date": pd.to_datetime(
                    ["2026-01-01", "2026-01-02", "2026-01-03"]
                ),
                "Close": [100.0, 110.0, 121.0],
            }
        )
        eth = pd.DataFrame(
            {
                "Date": pd.to_datetime(
                    ["2026-01-01", "2026-01-02", "2026-01-03"]
                ),
                "Close": [50.0, 55.0, 60.5],
            }
        )

        def fake_load_ohlcv(symbol, curr_date):
            return btc if symbol == "BTCUSDT" else eth

        graph = mock.Mock()
        with mock.patch("tradingagents.dataflows.binance.load_ohlcv", side_effect=fake_load_ohlcv):
            raw, alpha, days = TradingAgentsGraph._fetch_binance_returns(
                graph, "ETHUSDT", "2026-01-01", holding_days=2, benchmark="BTCUSDT"
            )

        self.assertEqual(days, 2)
        self.assertAlmostEqual(raw, 0.21)
        self.assertAlmostEqual(alpha, 0.0)


if __name__ == "__main__":
    unittest.main()
