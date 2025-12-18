import asyncio
from datetime import datetime
from app.db import SessionLocal
from sqlalchemy import text
from app.services.auto_order_engine import execute_auto_order

# Optional: import Zerodha token store / broker credentials
from app.services.user_service import get_user_zerodha_token

# Check interval (seconds)
CHECK_INTERVAL = 1

async def auto_order_worker():
    while True:
        db = SessionLocal()
        try:
            # Fetch all users with auto-order enabled
            rows = db.execute(
                text("SELECT * FROM auto_order_settings WHERE enabled=TRUE")
            ).fetchall()

            for row in rows:
                user_id = row.user_id
                # fetch zerodha token for this user
                token = get_user_zerodha_token(user_id)
                if not token:
                    continue  # skip if no broker token

                # Fetch live positions / drift logic
                positions = db.execute(
                    text("SELECT symbol, quantity, avg_price, ltp FROM positions WHERE user_id=:uid"),
                    {"uid": user_id}
                ).fetchall()

                for pos in positions:
                    symbol = pos.symbol
                    qty = pos.quantity
                    avg_price = float(pos.avg_price)
                    ltp = float(pos.ltp)

                    # Drift detection: simple threshold for example
                    threshold = 0.01  # 1% drift
                    target_price = avg_price * (1 + threshold)
                    if ltp >= target_price:
                        # SELL to rebalance
                        execute_auto_order(
                            user_id=user_id,
                            symbol=symbol,
                            side="SELL",
                            qty=qty,
                            access_token=token,
                            settings=dict(
                                default_sl_pct=row.default_sl_pct,
                                default_tp_pct=row.default_tp_pct,
                                slippage_pct=row.slippage_pct,
                                transaction_cost=row.transaction_cost
                            )
                        )
                    elif ltp <= avg_price * (1 - threshold):
                        # BUY to rebalance
                        execute_auto_order(
                            user_id=user_id,
                            symbol=symbol,
                            side="BUY",
                            qty=qty,
                            access_token=token,
                            settings=dict(
                                default_sl_pct=row.default_sl_pct,
                                default_tp_pct=row.default_tp_pct,
                                slippage_pct=row.slippage_pct,
                                transaction_cost=row.transaction_cost
                            )
                        )

            await asyncio.sleep(CHECK_INTERVAL)

        except Exception as e:
            print("Auto order scheduler error:", e)
            await asyncio.sleep(CHECK_INTERVAL)
        finally:
            db.close()

# Start scheduler (fire-and-forget)
def start_auto_order_scheduler(loop=None):
    loop = loop or asyncio.get_event_loop()
    loop.create_task(auto_order_worker())
