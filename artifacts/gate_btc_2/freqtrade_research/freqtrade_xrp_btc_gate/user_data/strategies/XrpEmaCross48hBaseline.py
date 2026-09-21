# RESEARCH_ONLY=true
# SHADOW_ONLY=true

from datetime import datetime, timedelta

import talib.abstract as ta
from pandas import DataFrame

from freqtrade.persistence import Trade
from freqtrade.strategy import IStrategy


class XrpEmaCross48hBaseline(IStrategy):
    INTERFACE_VERSION = 3
    timeframe = "1h"
    startup_candle_count = 60
    can_short = False

    minimal_roi = {"0": 100.0}
    stoploss = -0.99
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    process_only_new_candles = True

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema20"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["ema50"] = ta.EMA(dataframe, timeperiod=50)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        cross = (dataframe["ema20"] > dataframe["ema50"]) & (
            dataframe["ema20"].shift(1) <= dataframe["ema50"].shift(1)
        )
        dataframe.loc[cross & (dataframe["volume"] > 0), "enter_long"] = 1
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe.loc[:, "exit_long"] = 0
        return dataframe

    def custom_exit(
        self,
        pair: str,
        trade: Trade,
        current_time: datetime,
        current_rate: float,
        current_profit: float,
        **kwargs,
    ):
        if current_time >= trade.open_date_utc + timedelta(hours=48):
            return "time_exit_48h"
        return None
