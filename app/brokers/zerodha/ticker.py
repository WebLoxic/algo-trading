from kiteconnect import KiteTicker
from app.services.market_updater import update_ltp

class ZerodhaTicker:
    def __init__(self, api_key, access_token):
        self.ticker = KiteTicker(api_key, access_token)

        self.ticker.on_ticks = self.on_ticks
        self.ticker.on_connect = self.on_connect

    def on_ticks(self, ws, ticks):
        for t in ticks:
            symbol = t["tradingsymbol"]
            ltp = t["last_price"]
            update_ltp(symbol, ltp)

    def on_connect(self, ws, response):
        ws.subscribe(ws.subscribed_tokens)
        ws.set_mode(ws.MODE_LTP, ws.subscribed_tokens)

    def connect(self):
        self.ticker.connect(threaded=True)
