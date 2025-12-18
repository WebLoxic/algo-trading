from fastapi import APIRouter
from app.schemas import BacktestRequest, BacktestResult
from app.services.backtest_engine import run_backtest

router = APIRouter(prefix="/backtest", tags=["Backtest"])


@router.post("/run", response_model=BacktestResult)
def run(payload: BacktestRequest):
    result = run_backtest(
        symbol=payload.symbol,
        start=payload.from_date,
        end=payload.to_date,
        slippage_pct=payload.slippage_pct,
        commission=payload.commission,
        dataset=payload.dataset,
    )
    return result




