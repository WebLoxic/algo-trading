from fastapi import APIRouter
from app.schemas import CandleBacktestRequest, CandleBacktestResult
from app.services.candle_backtest_engine import run_candle_backtest

router = APIRouter(prefix="/backtest/candle", tags=["Candle Backtest"])


@router.post("/run", response_model=CandleBacktestResult)
def run(payload: CandleBacktestRequest):
    return run_candle_backtest(
        symbol=payload.symbol,
        interval=payload.interval,
        start=payload.from_date,
        end=payload.to_date,
        slippage_pct=payload.slippage_pct,
        commission=payload.commission,
    )
