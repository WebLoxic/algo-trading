from app.services.trading_engine import execute_order

def execute_rebalance(user_id: int, actions: list[dict], access_token: str | None):
    order_ids = []

    for a in actions:
        oid = execute_order(
            user_id=user_id,
            symbol=a["symbol"],
            side=a["side"],
            qty=a["qty"],
            access_token=access_token
        )
        order_ids.append(oid)

    return order_ids
