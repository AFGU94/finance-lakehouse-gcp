"""
Extracción de datos desde Yahoo Finance (yfinance).
Devuelve un DataFrame normalizado para GCS y BigQuery.
Soporta carga incremental por ventana de fechas (start/end) o backfill por period.
"""
import logging
from datetime import date, datetime, timedelta
from typing import Optional

import pandas as pd
import yfinance as yf

from src.config import TICKERS

logger = logging.getLogger(__name__)

# Días atrás para carga incremental diaria (cubre fines de semana y festivos)
INCREMENTAL_DAYS = 2


def extract_stock_data(
    tickers: Optional[list[str]] = None,
    period: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    incremental: bool = True,
) -> pd.DataFrame:
    """
    Descarga OHLCV (+ Adj Close) para los tickers indicados.

    Args:
        tickers: Lista de símbolos (default: config.TICKERS).
        period: Rango yfinance (solo si incremental=False): 1d, 5d, 1mo, 3mo, 6mo, 1y, max.
        start_date: Inicio de ventana (carga incremental).
        end_date: Fin de ventana (carga incremental).
        incremental: Si True (default), ignora period y usa ventana (end_date - INCREMENTAL_DAYS, end_date).

    Returns:
        DataFrame con columnas: date, symbol, open, high, low, close, adj_close, volume.
    """
    symbols = tickers or TICKERS
    if not symbols:
        logger.warning("No tickers configured")
        return pd.DataFrame()

    if incremental:
        end = end_date or date.today()
        start = start_date or (end - timedelta(days=INCREMENTAL_DAYS))
        period_arg = None
        start_end = (start, end)
    else:
        period_arg = period or "5d"
        start_end = None

    all_dfs: list[pd.DataFrame] = []
    for symbol in symbols:
        try:
            df = _download_one(symbol, period=period_arg, start_end=start_end)
            if df is not None and not df.empty:
                all_dfs.append(df)
        except Exception as e:
            logger.exception("Error downloading %s: %s", symbol, e)

    if not all_dfs:
        logger.warning("No data downloaded for any ticker")
        return pd.DataFrame()

    result = pd.concat(all_dfs, ignore_index=True)
    return result


def _download_one(
    symbol: str,
    period: Optional[str] = None,
    start_end: Optional[tuple[date, date]] = None,
) -> Optional[pd.DataFrame]:
    """Descarga un ticker y normaliza a una fila por fecha con columna symbol."""
    try:
        ticker = yf.Ticker(symbol)
        if start_end is not None:
            start_d, end_d = start_end
            # yfinance acepta datetime o string YYYY-MM-DD
            data = ticker.history(
                start=datetime.combine(start_d, datetime.min.time()),
                end=datetime.combine(end_d, datetime.min.time()),
                auto_adjust=False,
            )
        else:
            data = ticker.history(period=period or "5d", auto_adjust=False)
    except Exception as e:
        logger.debug("Ticker.history failed for %s: %s", symbol, e)
        data = None

    if data is None or data.empty:
        return None

    data = data.copy()
    data.index = pd.to_datetime(data.index)
    if data.index.tz is not None:
        data.index = data.index.tz_localize(None)

    # history() devuelve columnas simples (Open, High, ...) o a veces MultiIndex; aplanar
    data.columns = [_flatten_col(c) for c in data.columns]
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
    # Si no hay Adj Close (común con history()), usar Close
    if "adj_close" not in data.columns and "close" in data.columns:
        data["adj_close"] = data["close"]

    data["symbol"] = symbol
    data = data.reset_index()
    data.columns = [_flatten_col(c) for c in data.columns]
    data = data.rename(columns={"Date": "date"} if "Date" in data.columns else {})
    cols = ["date", "symbol", "open", "high", "low", "close", "adj_close", "volume"]
    data = data[[c for c in cols if c in data.columns]]
    # Limitar precios a 2 decimales
    price_cols = [c for c in ("open", "high", "low", "close", "adj_close") if c in data.columns]
    if price_cols:
        data[price_cols] = data[price_cols].round(2)
    return data


def _flatten_col(c) -> str:
    """
    Convierte nombre de columna a string (evita tuplas que BigQuery rechaza).
    yfinance devuelve MultiIndex (Price, Ticker), ej: ('Open', 'AAPL'), ('Adj Close', 'AAPL').
    Usamos el primer elemento (nombre del precio) para que el rename a 'open', etc. haga match.
    """
    if isinstance(c, tuple):
        parts = [str(x).strip() for x in c if x]
        return parts[0] if parts else "col"
    return str(c)
