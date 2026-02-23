"""
Extracción de datos desde Yahoo Finance (yfinance).
Devuelve un DataFrame normalizado para GCS y BigQuery.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd
import yfinance as yf

from src.config import TICKERS

logger = logging.getLogger(__name__)


def extract_stock_data(
    tickers: Optional[list[str]] = None,
    period: str = "1mo",
) -> pd.DataFrame:
    """
    Descarga OHLCV (+ Adj Close) para los tickers indicados.

    Args:
        tickers: Lista de símbolos (default: config.TICKERS).
        period: Rango yfinance: 1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, max.

    Returns:
        DataFrame con columnas: date, symbol, open, high, low, close, adj_close, volume.
    """
    symbols = tickers or TICKERS
    if not symbols:
        logger.warning("No tickers configured")
        return pd.DataFrame()

    all_dfs: list[pd.DataFrame] = []
    for symbol in symbols:
        try:
            df = _download_one(symbol, period)
            if df is not None and not df.empty:
                all_dfs.append(df)
        except Exception as e:
            logger.exception("Error downloading %s: %s", symbol, e)

    if not all_dfs:
        logger.warning("No data downloaded for any ticker")
        return pd.DataFrame()

    result = pd.concat(all_dfs, ignore_index=True)
    return result


def _download_one(symbol: str, period: str) -> Optional[pd.DataFrame]:
    """Descarga un ticker y normaliza a una fila por fecha con columna symbol."""
    data = yf.download(
        symbol,
        period=period,
        progress=False,
        auto_adjust=False,
        threads=False,
    )
    if data is None or data.empty:
        return None

    # yfinance con un solo ticker: columnas Open, High, Low, Close, Adj Close, Volume
    data = data.copy()
    data.index = pd.to_datetime(data.index)
    if data.index.tz is not None:
        data.index = data.index.tz_localize(None)
    data = data.rename(
        columns={
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Adj Close": "adj_close",
            "Volume": "volume",
        }
    )
    data["symbol"] = symbol
    data = data.reset_index().rename(columns={"Date": "date"})
    cols = ["date", "symbol", "open", "high", "low", "close", "adj_close", "volume"]
    data = data[[c for c in cols if c in data.columns]]
    return data
