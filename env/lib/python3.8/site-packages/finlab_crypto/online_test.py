import unittest
import warnings
from finlab_crypto.strategy import Strategy
from finlab_crypto.indicators import trends
from finlab_crypto import online
from finlab_crypto.online import TradingPortfolio, render_html
import os

warnings.filterwarnings(
    'ignore',
    category=ResourceWarning,
    message='ResourceWarning: unclosed'
)

class TestOnlineMethods(unittest.TestCase):

    def setUp(self):

        @Strategy(name='sma', n1=20, n2=40)
        def trend_strategy(ohlcv):
          name = trend_strategy.name
          n1 = trend_strategy.n1
          n2 = trend_strategy.n2

          filtered1 = trends[name](ohlcv.close, n1)
          filtered2 = trends[name](ohlcv.close, n2)

          entries = (filtered1 > filtered2) & (filtered1.shift() < filtered2.shift())
          exit = (filtered1 < filtered2) & (filtered1.shift() > filtered2.shift())

          figures = {
              'overlaps': {
                  'trend1': filtered1,
                  'trend2': filtered2,
              }
          }
          return entries, exit, figures


        # altcoin strategy
        # --------------------
        # 'XRPBTC', 'ADABTC', 'LINKBTC', 'ETHBTC', 'VETBTC'
        # trend_strategy(ohlcv, variables={'name': 'sma', 'n1', 30, 'n2': 130}, freq='4h')

        from finlab_crypto.online import TradingMethod

        tm1 = TradingMethod(
            symbols=['XRPBTC', 'ADABTC', 'LINKBTC', 'ETHBTC', 'VETBTC', 'ADAUSDT'],
            freq='4h',
            lookback=1000,
            strategy=trend_strategy,
            variables={'name': 'sma', 'n1': 30, 'n2': 130},
            weight_btc=0.01,
            name='altcoin-trend-strategy-2020-10-31',
        )

        # btc strategy
        # --------------------
        # 'BTCUSDT'
        # trend_strategy(ohlcv, variables={'name': 'hullma', 'n1', 70, 'n2': 108}, freq='4h')

        tm2 = TradingMethod(
            symbols=['BTCUSDT'],
            freq='4h',
            lookback=1000,
            strategy=trend_strategy,
            variables={'name': 'hullma', 'n1': 70, 'n2': 108},
            weight_btc=0.05,
            name='btc-trend-strategy-2020-10-31',
        )

        if 'BINANCE_KEY' not in os.environ or 'BINANCE_SECRET' not in os.environ:
            print('please set BINANCE_KEY and BINANCE_SECRET as environment variables')
            exit()
        key = os.environ.get('BINANCE_KEY')
        secret = os.environ.get('BINANCE_SECRET')



        tp = TradingPortfolio(key, secret)
        tp.register(tm1)
        tp.register(tm2)
        tp.register_margin('USDT', 1000)

        self.tp = tp
        self.ohlcvs = tp.get_full_ohlcvs()

    def test_adjust_quote_value(self):

        def trim_time(ohlcvs, time):
            ret = {}
            for key, df in self.ohlcvs.items():
                ret[key] = df.loc[:time]
            return ret

        dates = self.ohlcvs[('ADABTC', '4h')]['2019-01-01':'2019-01-5'].index

        for d1, d2 in zip(dates, dates[1:]):

            ohlcvs_temp = trim_time(self.ohlcvs, d1)
            signal1 = self.tp.get_latest_signals(ohlcvs_temp)

            ohlcvs_temp = trim_time(self.ohlcvs, d2)
            signal2 = self.tp.get_latest_signals(ohlcvs_temp)
            position, position_btc, new_orders = self.tp.calculate_position_size(signal2)
            execute_order_result = self.tp.execute_orders(new_orders, mode='TEST')

            (signal1.latest_signal & signal2.latest_signal).astype(int)

            # assert latest prices are the same as historical data
            same_last_price = (signal2.symbol.map(
                lambda s:ohlcvs_temp[(s, '4h')].close.iloc[-1]) == signal2.latest_price).all()
            self.assertEqual(same_last_price, True)

            # assert weight_btc is adjust as the price change
            last_price_in_quote_asset1 = (signal1.symbol
            .map(self.tp.ticker_info.get_base_asset)
            .map(lambda s: self.ohlcvs[(s+self.tp.quote_asset, '4h')].close[d1] if s != self.tp.quote_asset else 1))

            last_price_in_quote_asset2 = (signal2.symbol
                .map(self.tp.ticker_info.get_base_asset)
                .map(lambda s: self.ohlcvs[(s+self.tp.quote_asset, '4h')].close[d2] if s != self.tp.quote_asset else 1))

            error = ((last_price_in_quote_asset2 / last_price_in_quote_asset1) / (signal2.value_in_btc / signal1.value_in_btc) - 1)
            activate = signal1.latest_signal & signal2.latest_signal
            adjust_value_in_btc = ((error < 0.01) | (~activate)).all()
            self.assertEqual(adjust_value_in_btc, True)

