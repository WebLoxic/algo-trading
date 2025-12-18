import random
import time

class ZerodhaService:
    """
    Later: real kiteconnect logic
    Abhi: live-like mock
    """

    def get_positions(self, user_id):
        # Empty = "You have no active positions"
        return []

    def get_orders(self, user_id):
        return []

    def place_order(self, data):
        return {
            "order_id": f"ORD-{int(time.time())}",
            "status": "SUCCESS"
        }

    def get_ltp(self, symbol):
        return round(random.uniform(100, 2500), 2)
