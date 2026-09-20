from pandas import DataFrame
from freqtrade.strategy import IStrategy
import talib.abstract as ta


class StandaloneEmaReference(IStrategy):
    """Transparent engine-validation strategy, not an alpha claim."""

    timeframe = "1h"
    can_short = False
    startup_candle_count = 60
    process_only_new_candles = True

    minimal_roi = {"0": 100.0}
    stoploss = -0.15
    trailing_stop = False
    use_exit_signal = True
    exit_profit_only = False

    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        dataframe["ema_fast"] = ta.EMA(dataframe, timeperiod=20)
        dataframe["ema_slow"] = ta.EMA(dataframe, timeperiod=50)
        return dataframe

    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        crossed_up = (
            (dataframe["ema_fast"] > dataframe["ema_slow"])
            & (dataframe["ema_fast"].shift(1) <= dataframe["ema_slow"].shift(1))
        )
        dataframe.loc[crossed_up & (dataframe["volume"] > 0), "enter_long"] = 1
        dataframe.loc[crossed_up & (dataframe["volume"] > 0), "enter_tag"] = "ema20_cross_up_ema50"
        return dataframe

    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        crossed_down = (
            (dataframe["ema_fast"] < dataframe["ema_slow"])
            & (dataframe["ema_fast"].shift(1) >= dataframe["ema_slow"].shift(1))
        )
        dataframe.loc[crossed_down & (dataframe["volume"] > 0), "exit_long"] = 1
        dataframe.loc[crossed_down & (dataframe["volume"] > 0), "exit_tag"] = "ema20_cross_down_ema50"
        return dataframe
