import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

from src.data.tushare_client import TushareClient


class TushareClientTests(unittest.TestCase):
    def test_get_daily_posts_tushare_payload_and_returns_dataframe(self) -> None:
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "code": 0,
            "msg": None,
            "data": {
                "fields": ["ts_code", "trade_date", "open", "high", "low", "close", "vol", "amount", "suspend_type"],
                "items": [["000001.SZ", "20240102", 10, 11, 9, 10.5, 900, 1800, None]],
            },
        }

        with patch("src.data.tushare_client.requests.post", return_value=response) as mock_post:
            client = TushareClient(http_url="http://example.com", token="abc")
            df = client.get_daily("000001.SZ", "20240101", "20240131")

        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 1)
        self.assertEqual(df.iloc[0]["ts_code"], "000001.SZ")
        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["api_name"], "daily")
        self.assertEqual(payload["token"], "abc")
        self.assertEqual(payload["params"]["ts_code"], "000001.SZ")
        self.assertIn("suspend_type", payload["fields"])

    def test_get_daily_raises_on_nonzero_code(self) -> None:
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"code": 2002, "msg": "token invalid", "data": None}

        with patch("src.data.tushare_client.requests.post", return_value=response):
            client = TushareClient(http_url="http://example.com", token="abc")
            with self.assertRaises(ValueError):
                client.get_daily("000001.SZ", "20240101", "20240131")

    def test_get_daily_returns_suspend_type_column_for_tradability(self) -> None:
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "code": 0,
            "msg": None,
            "data": {
                "fields": ["ts_code", "trade_date", "open", "high", "low", "close", "vol", "amount", "suspend_type"],
                "items": [["000001.SZ", "20240102", 10, 11, 9, 10.5, 900, 1800, "S"]],
            },
        }

        with patch("src.data.tushare_client.requests.post", return_value=response):
            client = TushareClient(http_url="http://example.com", token="abc")
            df = client.get_daily("000001.SZ", "20240101", "20240131")

        self.assertEqual(df.iloc[0]["suspend_type"], "S")

    def test_get_index_components_returns_distinct_ts_codes(self) -> None:
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "code": 0,
            "msg": None,
            "data": {
                "fields": ["index_code", "con_code", "trade_date"],
                "items": [
                    ["000300.SH", "000001.SZ", "20240131"],
                    ["000300.SH", "600000.SH", "20240131"],
                    ["000300.SH", "000001.SZ", "20240130"],
                ],
            },
        }

        with patch("src.data.tushare_client.requests.post", return_value=response) as mock_post:
            client = TushareClient(http_url="http://example.com", token="abc")
            codes = client.get_index_components("000300.SH")

        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["api_name"], "index_weight")
        self.assertEqual(payload["params"]["index_code"], "000300.SH")
        self.assertEqual(codes, ["000001.SZ", "600000.SH"])

    def test_get_index_components_history_returns_normalized_component_rows(self) -> None:
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "code": 0,
            "msg": None,
            "data": {
                "fields": ["index_code", "con_code", "trade_date", "weight"],
                "items": [
                    ["000300.SH", "000001.SZ", "20240131", 0.12],
                    ["000300.SH", "600000.SH", "20240229", 0.08],
                ],
            },
        }

        with patch("src.data.tushare_client.requests.post", return_value=response) as mock_post:
            client = TushareClient(http_url="http://example.com", token="abc")
            df = client.get_index_components_history("000300.SH", "20240101", "20240229")

        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["params"]["start_date"], "20240101")
        self.assertEqual(payload["params"]["end_date"], "20240229")
        self.assertEqual(df.iloc[0]["ticker"], "sz000001")
        self.assertEqual(df.iloc[1]["ticker"], "sh600000")
        self.assertEqual(df.iloc[0]["date"].strftime("%Y-%m-%d"), "2024-01-31")

    def test_get_stock_basic_returns_name_metadata(self) -> None:
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "code": 0,
            "msg": None,
            "data": {
                "fields": ["ts_code", "name"],
                "items": [
                    ["000001.SZ", "平安银行"],
                    ["300001.SZ", "特锐德"],
                    ["688001.SH", "华兴源创"],
                    ["430001.BJ", "北交样本"],
                    ["600145.SH", "*ST新亿"],
                ],
            },
        }

        with patch("src.data.tushare_client.requests.post", return_value=response) as mock_post:
            client = TushareClient(http_url="http://example.com", token="abc")
            df = client.get_stock_basic()

        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["api_name"], "stock_basic")
        self.assertEqual(payload["params"], {"list_status": "L", "market": "主板"})
        self.assertIn("sz000001", df["ticker"].tolist())
        self.assertEqual(df.loc[df["ticker"] == "sh600145", "name"].iloc[0], "*ST新亿")

    def test_filter_excluded_tickers_removes_non_mainboard_and_st(self) -> None:
        client = TushareClient(http_url="http://example.com", token="abc")
        meta = pd.DataFrame(
            [
                {"ticker": "sz000001", "name": "平安银行"},
                {"ticker": "sh600145", "name": "*ST新亿"},
            ]
        )

        filtered = client.filter_excluded_tickers(["sz000001", "sz300001", "sh688001", "bj430001", "sh600145"], meta)

        self.assertEqual(filtered, ["sz000001"])


if __name__ == "__main__":
    unittest.main()
