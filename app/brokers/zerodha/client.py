from kiteconnect import KiteConnect, KiteTicker
import os

KITE_API_KEY = os.getenv("KITE_API_KEY")
KITE_API_SECRET = os.getenv("KITE_API_SECRET")

class ZerodhaClient:
    def __init__(self, access_token: str):
        self.kite = KiteConnect(api_key=KITE_API_KEY)
        self.kite.set_access_token(access_token)

    # ---------- ORDERS ----------
    def place_order(
        self,
        symbol: str,
        side: str,
        qty: int,
        order_type="MARKET",
        product="MIS",
        exchange="NSE",
        price=None,
    ):
        return self.kite.place_order(
            variety=self.kite.VARIETY_REGULAR,
            exchange=exchange,
            tradingsymbol=symbol,
            transaction_type=self.kite.TRANSACTION_TYPE_BUY
            if side == "BUY"
            else self.kite.TRANSACTION_TYPE_SELL,
            quantity=qty,
            order_type=order_type,
            product=product,
            price=price,
        )

    # ---------- POSITIONS ----------
    def positions(self):
        return self.kite.positions()["net"]

    # ---------- ORDERS ----------
    def orders(self):
        return self.kite.orders()
