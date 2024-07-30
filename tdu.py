from lumibot.brokers import Alpaca
from lumibot.backtesting import YahooDataBacktesting
from lumibot.strategies.strategy import Strategy
from lumibot.traders import Trader
from datetime import datetime
from alpaca_trade_api import REST
from finbert_utils import estimate_sentiment
from datetime import timedelta

API_KEY = "PKT9T7KDZXYLX6QACLBN"
API_SECRET = "AIUiLsyICIxd2q4Zf14NKQDlMG5VLcO8lsOWhWjY"
BASE_URL = "https://paper-api.alpaca.markets"

ALPACA_CREDS = {
    "API_KEY": API_KEY,
    "API_SECRET": API_SECRET,
    "PAPER": True
}

class MultiSymbolMLTrader(Strategy):
    def initialize(self, symbols, cash_at_risk=0.5):
        self.symbols = symbols
        self.sleeptime = "24H"
        self.last_trade = {symbol: None for symbol in symbols}
        self.cash_at_risk = cash_at_risk
        self.api = REST(base_url=BASE_URL, key_id=API_KEY, secret_key=API_SECRET)

    def position_sizing(self, symbol):
        cash = self.get_cash()
        last_price = self.get_last_price(symbol)
        quantity = round(cash * self.cash_at_risk / last_price, 0)
        return cash, last_price, quantity

    def get_dates(self):
        today = self.get_datetime()
        three_days_prior = today - timedelta(days=3)
        return today.strftime('%Y-%m-%d'), three_days_prior.strftime('%Y-%m-%d')

    def get_sentiment(self, symbol):
        today, three_days_prior = self.get_dates()
        news = self.api.get_news(symbol=symbol,
                                 start=three_days_prior,
                                 end=today)
        news = [ev.__dict__["_raw"]["headline"] for ev in news]
        probability, sentiment = estimate_sentiment(news)
        return probability, sentiment

    def on_trading_iteration(self):
        for symbol in self.symbols:
            cash, last_price, quantity = self.position_sizing(symbol)
            probability, sentiment = self.get_sentiment(symbol)

            if cash > last_price:
                if sentiment == "positive" and probability > 0.999:
                    if self.last_trade[symbol] == "sell":
                        self.sell_all(symbol)
                    order = self.create_order(
                        symbol,
                        quantity,
                        "buy",
                        type="bracket",
                        take_profit_price=last_price * 1.20,
                        stop_loss_price=last_price * 0.95
                    )
                    self.submit_order(order)
                    self.last_trade[symbol] = "buy"
                elif sentiment == "negative" and probability > 0.999:
                    if self.last_trade[symbol] == "buy":
                        self.sell_all(symbol)
                    order = self.create_order(
                        symbol,
                        quantity,
                        "sell",
                        type="bracket",
                        take_profit_price=last_price * 0.8,
                        stop_loss_price=last_price * 1.05
                    )
                    self.submit_order(order)
                    self.last_trade[symbol] = "sell"

symbols_to_trade = ["AAPL", "GOOGL", "MSFT", "AMZN", "SP3Y", "TSLA"]
symbols_to_initialize = ["AAPL", "GOOGL", "MSFT", "AMZN", "SPY", "TSLA"]

start_date = datetime(2020, 1, 1)
end_date = datetime(2023, 12, 31)
broker = Alpaca(ALPACA_CREDS)
strategy = MultiSymbolMLTrader(name='multisymbolmlstrat', broker=broker,
                               parameters={"symbols": symbols_to_trade,
                                           "cash_at_risk": 0.5})
strategy.backtest(
    YahooDataBacktesting,
    start_date,
    end_date,
    parameters={"symbols": symbols_to_trade, "cash_at_risk": 0.5}
)
