

# # app/schemas.py
# from pydantic import BaseModel, EmailStr, Field
# from typing import Optional, List, Any, Dict
# from datetime import datetime

# # =====================================================
# # AUTH / USER SCHEMAS
# # =====================================================
# class UserCreate(BaseModel):
#     full_name: Optional[str] = Field(None, max_length=255)
#     email: EmailStr
#     password: str


# class LoginPayload(BaseModel):
#     email: EmailStr
#     password: str


# class UserOut(BaseModel):
#     id: int
#     full_name: Optional[str] = None
#     email: EmailStr
#     is_active: bool = True
#     is_superuser: bool = False
#     created_at: datetime

#     class Config:
#         orm_mode = True


# class Token(BaseModel):
#     access_token: str
#     token_type: str = "bearer"


# class TokenData(BaseModel):
#     sub: Optional[str] = None
#     exp: Optional[int] = None


# class ForgotPasswordRequest(BaseModel):
#     email: EmailStr


# class ResetPasswordPayload(BaseModel):
#     token: str
#     new_password: str


# # =====================================================
# # ADMIN / REPORTING
# # =====================================================
# class SubscriptionOut(BaseModel):
#     id: int
#     user_id: Optional[int] = None
#     plan_name: str
#     price: float
#     currency: Optional[str] = "INR"
#     interval: str
#     start_date: Optional[datetime] = None
#     end_date: Optional[datetime] = None
#     is_active: bool
#     meta: Optional[Dict[str, Any]] = None
#     created_at: datetime

#     class Config:
#         orm_mode = True


# class PaymentTransactionOut(BaseModel):
#     id: int
#     user_id: Optional[int] = None
#     order_id: Optional[str] = None
#     payment_id: Optional[str] = None
#     amount: float
#     currency: str = "INR"
#     gateway: Optional[str] = None
#     status: Optional[str] = None
#     provider_response: Optional[Dict[str, Any]] = None
#     created_at: datetime

#     class Config:
#         orm_mode = True


# class CredentialHistoryOut(BaseModel):
#     id: int
#     user_id: Optional[int] = None
#     action: str
#     detail: Optional[Dict[str, Any]] = None
#     created_at: datetime

#     class Config:
#         orm_mode = True


# class PaginatedResponse(BaseModel):
#     total: int
#     skip: int
#     limit: int
#     items: List[Any]


# # =====================================================
# # BROKER / CONNECTIVITY
# # =====================================================
# class BrokerConnectRequest(BaseModel):
#     provider: str
#     callback_url: Optional[str] = None


# class BrokerStatusResponse(BaseModel):
#     provider: str
#     connected: bool
#     account_info: Optional[Dict[str, Any]] = None


# class BrokerAccountOut(BaseModel):
#     id: int
#     user_id: Optional[int] = None
#     provider: str
#     account_name: Optional[str] = None
#     client_id: Optional[str] = None
#     created_at: Optional[datetime] = None

#     class Config:
#         orm_mode = True


# # =====================================================
# # 🔥 LIVE TRADING / UI / WEBSOCKET SCHEMAS (NEW)
# # =====================================================
# class SimpleOrderCreate(BaseModel):
#     """
#     Used by:
#     - Trading popup (screenshot)
#     - WebSocket driven UI
#     - Quick BUY / SELL
#     """
#     symbol: str
#     qty: int
#     side: str  # BUY / SELL
#     order_type: str = "MARKET"


# class PositionOut(BaseModel):
#     """
#     Portfolio / Open Positions (WS + REST)
#     """
#     symbol: str
#     qty: int
#     avg_price: float
#     ltp: float
#     pnl: float


# # =====================================================
# # ADVANCED ORDERS / TRADING (EXISTING – UNTOUCHED)
# # =====================================================
# class OrderCreate(BaseModel):
#     symbol: str
#     quantity: float
#     price: Optional[float] = None
#     order_type: str = "market"
#     product: Optional[str] = "regular"
#     side: str = "buy"
#     tif: Optional[str] = "DAY"


# class OrderResponse(BaseModel):
#     id: int
#     broker_order_id: Optional[str] = None
#     user_id: Optional[int] = None
#     symbol: str
#     quantity: float
#     price: Optional[float] = None
#     order_type: str
#     side: str
#     status: str
#     filled_qty: Optional[float] = 0.0
#     avg_price: Optional[float] = None
#     created_at: Optional[datetime] = None
#     meta: Optional[Dict[str, Any]] = None

#     class Config:
#         orm_mode = True


# class CancelOrderResponse(BaseModel):
#     ok: bool
#     message: Optional[str] = None


# class OrderHistoryItem(BaseModel):
#     id: int
#     symbol: str
#     side: str
#     quantity: float
#     price: Optional[float] = None
#     status: str
#     created_at: datetime

#     class Config:
#         orm_mode = True


# # =====================================================
# # MARKET / TICKS
# # =====================================================
# class Tick(BaseModel):
#     symbol: str
#     ltp: float
#     ts: float
#     raw: Optional[Dict[str, Any]] = None


# class MarketTickOut(BaseModel):
#     id: int
#     instrument_token: Optional[str] = None
#     tradingsymbol: str
#     ts: datetime
#     ltp: float
#     raw: Optional[Dict[str, Any]] = None

#     class Config:
#         orm_mode = True


# # Backtest Request / Response

# class BacktestRequest(BaseModel):
#     symbol: str
#     dataset: str = "tick-demo"
#     from_date: datetime
#     to_date: datetime
#     slippage_pct: float = 0.05
#     commission: float = 0.1


# class BacktestResult(BaseModel):
#     trades: int
#     pnl: float
#     win_rate: float
#     max_drawdown: float

# class CandleBacktestRequest(BaseModel):
#     symbol: str
#     interval: str = "5m"
#     from_date: datetime
#     to_date: datetime
#     slippage_pct: float = 0.05
#     commission: float = 0.1


# class CandleBacktestResult(BaseModel):
#     trades: int
#     pnl: float
#     win_rate: float
#     max_drawdown: float

# # =====================================================
# # (REST OF YOUR FILE – STRATEGY, BILLING, WALLET, ETC.)
# # 👉 100% UNCHANGED
# # =====================================================
# # (Everything below remains exactly same as you sent)







# # app/schemas.py
# from pydantic import BaseModel, EmailStr, Field
# from typing import Optional, List, Any, Dict
# from datetime import datetime

# # =====================================================
# # AUTH / USER SCHEMAS
# # =====================================================
# class UserCreate(BaseModel):
#     full_name: Optional[str] = Field(None, max_length=255)
#     email: EmailStr
#     password: str


# class LoginPayload(BaseModel):
#     email: EmailStr
#     password: str


# class UserOut(BaseModel):
#     id: int
#     full_name: Optional[str] = None
#     email: EmailStr
#     is_active: bool = True
#     is_superuser: bool = False
#     created_at: datetime

#     class Config:
#         orm_mode = True


# class Token(BaseModel):
#     access_token: str
#     token_type: str = "bearer"


# class TokenData(BaseModel):
#     sub: Optional[str] = None
#     exp: Optional[int] = None


# class ForgotPasswordRequest(BaseModel):
#     email: EmailStr


# class ResetPasswordPayload(BaseModel):
#     token: str
#     new_password: str


# # =====================================================
# # ADMIN / REPORTING
# # =====================================================
# class SubscriptionOut(BaseModel):
#     id: int
#     user_id: Optional[int] = None
#     plan_name: str
#     price: float
#     currency: Optional[str] = "INR"
#     interval: str
#     start_date: Optional[datetime] = None
#     end_date: Optional[datetime] = None
#     is_active: bool
#     meta: Optional[Dict[str, Any]] = None
#     created_at: datetime

#     class Config:
#         orm_mode = True


# class PaymentTransactionOut(BaseModel):
#     id: int
#     user_id: Optional[int] = None
#     order_id: Optional[str] = None
#     payment_id: Optional[str] = None
#     amount: float
#     currency: str = "INR"
#     gateway: Optional[str] = None
#     status: Optional[str] = None
#     provider_response: Optional[Dict[str, Any]] = None
#     created_at: datetime

#     class Config:
#         orm_mode = True


# class CredentialHistoryOut(BaseModel):
#     id: int
#     user_id: Optional[int] = None
#     action: str
#     detail: Optional[Dict[str, Any]] = None
#     created_at: datetime

#     class Config:
#         orm_mode = True


# class PaginatedResponse(BaseModel):
#     total: int
#     skip: int
#     limit: int
#     items: List[Any]


# # =====================================================
# # BROKER / CONNECTIVITY
# # =====================================================
# class BrokerConnectRequest(BaseModel):
#     provider: str
#     callback_url: Optional[str] = None


# class BrokerStatusResponse(BaseModel):
#     provider: str
#     connected: bool
#     account_info: Optional[Dict[str, Any]] = None


# class BrokerAccountOut(BaseModel):
#     id: int
#     user_id: Optional[int] = None
#     provider: str
#     account_name: Optional[str] = None
#     client_id: Optional[str] = None
#     created_at: Optional[datetime] = None

#     class Config:
#         orm_mode = True


# # =====================================================
# # 🔥 LIVE TRADING / UI / WEBSOCKET SCHEMAS (NEW)
# # =====================================================
# class SimpleOrderCreate(BaseModel):
#     """
#     Used by:
#     - Trading popup (screenshot)
#     - WebSocket driven UI
#     - Quick BUY / SELL
#     """
#     symbol: str
#     qty: int
#     side: str  # BUY / SELL
#     order_type: str = "MARKET"


# class PositionOut(BaseModel):
#     """
#     Portfolio / Open Positions (WS + REST)
#     """
#     symbol: str
#     qty: int
#     avg_price: float
#     ltp: float
#     pnl: float


# # =====================================================
# # ADVANCED ORDERS / TRADING (EXISTING – UNTOUCHED)
# # =====================================================
# class OrderCreate(BaseModel):
#     symbol: str
#     quantity: float
#     price: Optional[float] = None
#     order_type: str = "market"
#     product: Optional[str] = "regular"
#     side: str = "buy"
#     tif: Optional[str] = "DAY"


# class OrderResponse(BaseModel):
#     id: int
#     broker_order_id: Optional[str] = None
#     user_id: Optional[int] = None
#     symbol: str
#     quantity: float
#     price: Optional[float] = None
#     order_type: str
#     side: str
#     status: str
#     filled_qty: Optional[float] = 0.0
#     avg_price: Optional[float] = None
#     created_at: Optional[datetime] = None
#     meta: Optional[Dict[str, Any]] = None

#     class Config:
#         orm_mode = True


# class CancelOrderResponse(BaseModel):
#     ok: bool
#     message: Optional[str] = None


# class OrderHistoryItem(BaseModel):
#     id: int
#     symbol: str
#     side: str
#     quantity: float
#     price: Optional[float] = None
#     status: str
#     created_at: datetime

#     class Config:
#         orm_mode = True


# # =====================================================
# # MARKET / TICKS
# # =====================================================
# class Tick(BaseModel):
#     symbol: str
#     ltp: float
#     ts: float
#     raw: Optional[Dict[str, Any]] = None


# class MarketTickOut(BaseModel):
#     id: int
#     instrument_token: Optional[str] = None
#     tradingsymbol: str
#     ts: datetime
#     ltp: float
#     raw: Optional[Dict[str, Any]] = None

#     class Config:
#         orm_mode = True


# # =====================================================
# # BACKTEST REQUEST / RESPONSE
# # =====================================================
# class BacktestRequest(BaseModel):
#     symbol: str
#     dataset: str = "tick-demo"
#     from_date: datetime
#     to_date: datetime
#     slippage_pct: float = 0.05
#     commission: float = 0.1


# class BacktestResult(BaseModel):
#     trades: int
#     pnl: float
#     win_rate: float
#     max_drawdown: float


# class CandleBacktestRequest(BaseModel):
#     symbol: str
#     interval: str = "5m"
#     from_date: datetime
#     to_date: datetime
#     slippage_pct: float = 0.05
#     commission: float = 0.1


# class CandleBacktestResult(BaseModel):
#     trades: int
#     pnl: float
#     win_rate: float
#     max_drawdown: float


# # =====================================================
# # 🔹 REWARDS SCHEMAS (NEW)
# # =====================================================
# class RewardOut(BaseModel):
#     id: int
#     name: str
#     reward_type: str
#     description: Optional[str]
#     amount: float
#     expires_at: Optional[datetime]
#     active: bool

#     class Config:
#         orm_mode = True


# class UserRewardOut(BaseModel):
#     id: int
#     user_id: int
#     reward: RewardOut
#     claimed: bool
#     claimed_at: Optional[datetime]

#     class Config:
#         orm_mode = True


# # =====================================================
# # (REST OF YOUR FILE – STRATEGY, BILLING, WALLET, ETC.)
# # 👉 100% UNCHANGED
# # =====================================================
# # Everything else remains as before





# # app/schemas.py
# from pydantic import BaseModel, EmailStr, Field
# from typing import Optional, List, Any, Dict
# from datetime import datetime

# # =====================================================
# # AUTH / USER SCHEMAS
# # =====================================================
# class UserCreate(BaseModel):
#     full_name: Optional[str] = Field(None, max_length=255)
#     email: EmailStr
#     password: str


# class LoginPayload(BaseModel):
#     email: EmailStr
#     password: str


# class UserOut(BaseModel):
#     id: int
#     full_name: Optional[str] = None
#     email: EmailStr
#     is_active: bool = True
#     is_superuser: bool = False
#     created_at: datetime

#     class Config:
#         orm_mode = True


# class Token(BaseModel):
#     access_token: str
#     token_type: str = "bearer"


# class TokenData(BaseModel):
#     sub: Optional[str] = None
#     exp: Optional[int] = None


# class ForgotPasswordRequest(BaseModel):
#     email: EmailStr


# class ResetPasswordPayload(BaseModel):
#     token: str
#     new_password: str


# # =====================================================
# # ADMIN / REPORTING
# # =====================================================
# class SubscriptionOut(BaseModel):
#     id: int
#     user_id: Optional[int] = None
#     plan_name: str
#     price: float
#     currency: Optional[str] = "INR"
#     interval: str
#     start_date: Optional[datetime] = None
#     end_date: Optional[datetime] = None
#     is_active: bool
#     meta: Optional[Dict[str, Any]] = None
#     created_at: datetime

#     class Config:
#         orm_mode = True


# class PaymentTransactionOut(BaseModel):
#     id: int
#     user_id: Optional[int] = None
#     order_id: Optional[str] = None
#     payment_id: Optional[str] = None
#     amount: float
#     currency: str = "INR"
#     gateway: Optional[str] = None
#     status: Optional[str] = None
#     provider_response: Optional[Dict[str, Any]] = None
#     created_at: datetime

#     class Config:
#         orm_mode = True


# class CredentialHistoryOut(BaseModel):
#     id: int
#     user_id: Optional[int] = None
#     action: str
#     detail: Optional[Dict[str, Any]] = None
#     created_at: datetime

#     class Config:
#         orm_mode = True


# class PaginatedResponse(BaseModel):
#     total: int
#     skip: int
#     limit: int
#     items: List[Any]


# # =====================================================
# # BROKER / CONNECTIVITY
# # =====================================================
# class BrokerConnectRequest(BaseModel):
#     provider: str
#     callback_url: Optional[str] = None


# class BrokerStatusResponse(BaseModel):
#     provider: str
#     connected: bool
#     account_info: Optional[Dict[str, Any]] = None


# class BrokerAccountOut(BaseModel):
#     id: int
#     user_id: Optional[int] = None
#     provider: str
#     account_name: Optional[str] = None
#     client_id: Optional[str] = None
#     created_at: Optional[datetime] = None

#     class Config:
#         orm_mode = True


# # =====================================================
# # 🔥 LIVE TRADING / UI / WEBSOCKET SCHEMAS (NEW)
# # =====================================================
# class SimpleOrderCreate(BaseModel):
#     """
#     Used by:
#     - Trading popup (screenshot)
#     - WebSocket driven UI
#     - Quick BUY / SELL
#     """
#     symbol: str
#     qty: int
#     side: str  # BUY / SELL
#     order_type: str = "MARKET"


# class PositionOut(BaseModel):
#     """
#     Portfolio / Open Positions (WS + REST)
#     """
#     symbol: str
#     qty: int
#     avg_price: float
#     ltp: float
#     pnl: float


# # =====================================================
# # ADVANCED ORDERS / TRADING (EXISTING – UNTOUCHED)
# # =====================================================
# class OrderCreate(BaseModel):
#     symbol: str
#     quantity: float
#     price: Optional[float] = None
#     order_type: str = "market"
#     product: Optional[str] = "regular"
#     side: str = "buy"
#     tif: Optional[str] = "DAY"


# class OrderResponse(BaseModel):
#     id: int
#     broker_order_id: Optional[str] = None
#     user_id: Optional[int] = None
#     symbol: str
#     quantity: float
#     price: Optional[float] = None
#     order_type: str
#     side: str
#     status: str
#     filled_qty: Optional[float] = 0.0
#     avg_price: Optional[float] = None
#     created_at: Optional[datetime] = None
#     meta: Optional[Dict[str, Any]] = None

#     class Config:
#         orm_mode = True


# class CancelOrderResponse(BaseModel):
#     ok: bool
#     message: Optional[str] = None


# class OrderHistoryItem(BaseModel):
#     id: int
#     symbol: str
#     side: str
#     quantity: float
#     price: Optional[float] = None
#     status: str
#     created_at: datetime

#     class Config:
#         orm_mode = True


# # =====================================================
# # MARKET / TICKS
# # =====================================================
# class Tick(BaseModel):
#     symbol: str
#     ltp: float
#     ts: float
#     raw: Optional[Dict[str, Any]] = None


# class MarketTickOut(BaseModel):
#     id: int
#     instrument_token: Optional[str] = None
#     tradingsymbol: str
#     ts: datetime
#     ltp: float
#     raw: Optional[Dict[str, Any]] = None

#     class Config:
#         orm_mode = True


# # =====================================================
# # BACKTEST REQUEST / RESPONSE
# # =====================================================
# class BacktestRequest(BaseModel):
#     symbol: str
#     dataset: str = "tick-demo"
#     from_date: datetime
#     to_date: datetime
#     slippage_pct: float = 0.05
#     commission: float = 0.1


# class BacktestResult(BaseModel):
#     trades: int
#     pnl: float
#     win_rate: float
#     max_drawdown: float


# class CandleBacktestRequest(BaseModel):
#     symbol: str
#     interval: str = "5m"
#     from_date: datetime
#     to_date: datetime
#     slippage_pct: float = 0.05
#     commission: float = 0.1


# class CandleBacktestResult(BaseModel):
#     trades: int
#     pnl: float
#     win_rate: float
#     max_drawdown: float


# # =====================================================
# # 🔹 REWARDS SCHEMAS (NEW)
# # =====================================================
# class RewardOut(BaseModel):
#     id: int
#     name: str
#     reward_type: str
#     description: Optional[str]
#     amount: float
#     expires_at: Optional[datetime]
#     active: bool

#     class Config:
#         orm_mode = True


# class UserRewardOut(BaseModel):
#     id: int
#     user_id: int
#     reward: RewardOut
#     claimed: bool
#     claimed_at: Optional[datetime]

#     class Config:
#         orm_mode = True


# # =====================================================
# # (REST OF YOUR FILE – STRATEGY, BILLING, WALLET, ETC.)
# # 👉 100% UNCHANGED
# # =====================================================
# # Everything else remains exactly same as before






# # app/schemas.py
# from pydantic import BaseModel, EmailStr, Field
# from typing import Optional, List, Any, Dict
# from datetime import datetime

# # =====================================================
# # AUTH / USER SCHEMAS
# # =====================================================
# class UserCreate(BaseModel):
#     full_name: Optional[str] = Field(None, max_length=255)
#     email: EmailStr
#     password: str


# class LoginPayload(BaseModel):
#     email: EmailStr
#     password: str


# class UserOut(BaseModel):
#     id: int
#     full_name: Optional[str] = None
#     email: EmailStr
#     is_active: bool = True
#     is_superuser: bool = False
#     created_at: datetime

#     class Config:
#         orm_mode = True


# class Token(BaseModel):
#     access_token: str
#     token_type: str = "bearer"


# class TokenData(BaseModel):
#     sub: Optional[str] = None
#     exp: Optional[int] = None


# class ForgotPasswordRequest(BaseModel):
#     email: EmailStr


# class ResetPasswordPayload(BaseModel):
#     token: str
#     new_password: str


# # =====================================================
# # ADMIN / REPORTING
# # =====================================================
# class SubscriptionOut(BaseModel):
#     id: int
#     user_id: Optional[int] = None
#     plan_name: str
#     price: float
#     currency: Optional[str] = "INR"
#     interval: str
#     start_date: Optional[datetime] = None
#     end_date: Optional[datetime] = None
#     is_active: bool
#     meta: Optional[Dict[str, Any]] = None
#     created_at: datetime

#     class Config:
#         orm_mode = True


# class PaymentTransactionOut(BaseModel):
#     id: int
#     user_id: Optional[int] = None
#     order_id: Optional[str] = None
#     payment_id: Optional[str] = None
#     amount: float
#     currency: str = "INR"
#     gateway: Optional[str] = None
#     status: Optional[str] = None
#     provider_response: Optional[Dict[str, Any]] = None
#     created_at: datetime

#     class Config:
#         orm_mode = True


# class CredentialHistoryOut(BaseModel):
#     id: int
#     user_id: Optional[int] = None
#     action: str
#     detail: Optional[Dict[str, Any]] = None
#     created_at: datetime

#     class Config:
#         orm_mode = True


# class PaginatedResponse(BaseModel):
#     total: int
#     skip: int
#     limit: int
#     items: List[Any]


# # =====================================================
# # BROKER / CONNECTIVITY
# # =====================================================
# class BrokerConnectRequest(BaseModel):
#     provider: str
#     callback_url: Optional[str] = None


# class BrokerStatusResponse(BaseModel):
#     provider: str
#     connected: bool
#     account_info: Optional[Dict[str, Any]] = None


# class BrokerAccountOut(BaseModel):
#     id: int
#     user_id: Optional[int] = None
#     provider: str
#     account_name: Optional[str] = None
#     client_id: Optional[str] = None
#     created_at: Optional[datetime] = None

#     class Config:
#         orm_mode = True


# # =====================================================
# # 🔥 LIVE TRADING / UI / WEBSOCKET SCHEMAS (NEW)
# # =====================================================
# class SimpleOrderCreate(BaseModel):
#     symbol: str
#     qty: int
#     side: str  # BUY / SELL
#     order_type: str = "MARKET"


# class PositionOut(BaseModel):
#     symbol: str
#     qty: int
#     avg_price: float
#     ltp: float
#     pnl: float


# # =====================================================
# # ADVANCED ORDERS / TRADING
# # =====================================================
# class OrderCreate(BaseModel):
#     symbol: str
#     quantity: float
#     price: Optional[float] = None
#     order_type: str = "market"
#     product: Optional[str] = "regular"
#     side: str = "buy"
#     tif: Optional[str] = "DAY"


# class OrderResponse(BaseModel):
#     id: int
#     broker_order_id: Optional[str] = None
#     user_id: Optional[int] = None
#     symbol: str
#     quantity: float
#     price: Optional[float] = None
#     order_type: str
#     side: str
#     status: str
#     filled_qty: Optional[float] = 0.0
#     avg_price: Optional[float] = None
#     created_at: Optional[datetime] = None
#     meta: Optional[Dict[str, Any]] = None

#     class Config:
#         orm_mode = True


# class CancelOrderResponse(BaseModel):
#     ok: bool
#     message: Optional[str] = None


# class OrderHistoryItem(BaseModel):
#     id: int
#     symbol: str
#     side: str
#     quantity: float
#     price: Optional[float] = None
#     status: str
#     created_at: datetime

#     class Config:
#         orm_mode = True


# # =====================================================
# # MARKET / TICKS
# # =====================================================
# class Tick(BaseModel):
#     symbol: str
#     ltp: float
#     ts: float
#     raw: Optional[Dict[str, Any]] = None


# class MarketTickOut(BaseModel):
#     id: int
#     instrument_token: Optional[str] = None
#     tradingsymbol: str
#     ts: datetime
#     ltp: float
#     raw: Optional[Dict[str, Any]] = None

#     class Config:
#         orm_mode = True


# # =====================================================
# # BACKTEST REQUEST / RESPONSE
# # =====================================================
# class BacktestRequest(BaseModel):
#     symbol: str
#     dataset: str = "tick-demo"
#     from_date: datetime
#     to_date: datetime
#     slippage_pct: float = 0.05
#     commission: float = 0.1


# class BacktestResult(BaseModel):
#     trades: int
#     pnl: float
#     win_rate: float
#     max_drawdown: float


# class CandleBacktestRequest(BaseModel):
#     symbol: str
#     interval: str = "5m"
#     from_date: datetime
#     to_date: datetime
#     slippage_pct: float = 0.05
#     commission: float = 0.1


# class CandleBacktestResult(BaseModel):
#     trades: int
#     pnl: float
#     win_rate: float
#     max_drawdown: float


# # =====================================================
# # REWARDS SCHEMAS
# # =====================================================
# class RewardOut(BaseModel):
#     id: int
#     name: str
#     reward_type: str
#     description: Optional[str]
#     amount: float
#     expires_at: Optional[datetime]
#     active: bool

#     class Config:
#         orm_mode = True


# class UserRewardOut(BaseModel):
#     id: int
#     user_id: int
#     reward: RewardOut
#     claimed: bool
#     claimed_at: Optional[datetime]

#     class Config:
#         orm_mode = True


# # =====================================================
# # HELP / SUPPORT SCHEMAS (NEW)
# # =====================================================
# class HelpCategoryOut(BaseModel):
#     id: int
#     name: str
#     description: Optional[str]
#     created_at: datetime
#     updated_at: datetime

#     class Config:
#         orm_mode = True


# class HelpArticleOut(BaseModel):
#     id: int
#     category_id: int
#     title: str
#     content: Optional[str]
#     is_active: bool
#     created_at: datetime
#     updated_at: datetime

#     class Config:
#         orm_mode = True


# # =====================================================
# # (REST OF YOUR FILE – STRATEGY, BILLING, WALLET, ETC.)
# # =====================================================
# # Everything else remains unchanged





# # app/schemas.py

# from pydantic import BaseModel, EmailStr, Field
# from typing import Optional, List, Any, Dict
# from datetime import datetime


# # =====================================================
# # AUTH / USER SCHEMAS
# # =====================================================
# class UserCreate(BaseModel):
#     full_name: Optional[str] = Field(None, max_length=255)
#     email: EmailStr
#     password: str


# class LoginPayload(BaseModel):
#     email: EmailStr
#     password: str


# class UserOut(BaseModel):
#     id: int
#     full_name: Optional[str] = None
#     email: EmailStr
#     is_active: bool = True
#     is_superuser: bool = False
#     created_at: datetime

#     class Config:
#         from_attributes = True


# class Token(BaseModel):
#     access_token: str
#     token_type: str = "bearer"


# class TokenData(BaseModel):
#     sub: Optional[str] = None
#     exp: Optional[int] = None


# class ForgotPasswordRequest(BaseModel):
#     email: EmailStr


# class ResetPasswordPayload(BaseModel):
#     token: str
#     new_password: str


# # =====================================================
# # ADMIN / REPORTING
# # =====================================================
# class SubscriptionOut(BaseModel):
#     id: int
#     user_id: Optional[int] = None
#     plan_name: str
#     price: float
#     currency: Optional[str] = "INR"
#     interval: str
#     start_date: Optional[datetime] = None
#     end_date: Optional[datetime] = None
#     is_active: bool
#     meta: Optional[Dict[str, Any]] = None
#     created_at: datetime

#     class Config:
#         from_attributes = True


# class PaymentTransactionOut(BaseModel):
#     id: int
#     user_id: Optional[int] = None
#     order_id: Optional[str] = None
#     payment_id: Optional[str] = None
#     amount: float
#     currency: str = "INR"
#     gateway: Optional[str] = None
#     status: Optional[str] = None
#     provider_response: Optional[Dict[str, Any]] = None
#     created_at: datetime

#     class Config:
#         from_attributes = True


# class CredentialHistoryOut(BaseModel):
#     id: int
#     user_id: Optional[int] = None
#     action: str
#     detail: Optional[Dict[str, Any]] = None
#     created_at: datetime

#     class Config:
#         from_attributes = True


# class PaginatedResponse(BaseModel):
#     total: int
#     skip: int
#     limit: int
#     items: List[Any]


# # =====================================================
# # BROKER / CONNECTIVITY
# # =====================================================
# class BrokerConnectRequest(BaseModel):
#     provider: str
#     callback_url: Optional[str] = None


# class BrokerStatusResponse(BaseModel):
#     provider: str
#     connected: bool
#     account_info: Optional[Dict[str, Any]] = None


# class BrokerAccountOut(BaseModel):
#     id: int
#     user_id: Optional[int] = None
#     provider: str
#     account_name: Optional[str] = None
#     client_id: Optional[str] = None
#     created_at: Optional[datetime] = None

#     class Config:
#         from_attributes = True


# # =====================================================
# # LIVE TRADING / UI
# # =====================================================
# class SimpleOrderCreate(BaseModel):
#     symbol: str
#     qty: int
#     side: str  # BUY / SELL
#     order_type: str = "MARKET"


# class PositionOut(BaseModel):
#     symbol: str
#     qty: int
#     avg_price: float
#     ltp: float
#     pnl: float


# # =====================================================
# # ADVANCED ORDERS
# # =====================================================
# class OrderCreate(BaseModel):
#     symbol: str
#     quantity: float
#     price: Optional[float] = None
#     order_type: str = "market"
#     product: Optional[str] = "regular"
#     side: str = "buy"
#     tif: Optional[str] = "DAY"


# class OrderResponse(BaseModel):
#     id: int
#     broker_order_id: Optional[str] = None
#     user_id: Optional[int] = None
#     symbol: str
#     quantity: float
#     price: Optional[float] = None
#     order_type: str
#     side: str
#     status: str
#     filled_qty: Optional[float] = 0.0
#     avg_price: Optional[float] = None
#     created_at: Optional[datetime] = None
#     meta: Optional[Dict[str, Any]] = None

#     class Config:
#         from_attributes = True


# class CancelOrderResponse(BaseModel):
#     ok: bool
#     message: Optional[str] = None


# class OrderHistoryItem(BaseModel):
#     id: int
#     symbol: str
#     side: str
#     quantity: float
#     price: Optional[float] = None
#     status: str
#     created_at: datetime

#     class Config:
#         from_attributes = True


# # =====================================================
# # MARKET / TICKS
# # =====================================================
# class Tick(BaseModel):
#     symbol: str
#     ltp: float
#     ts: float
#     raw: Optional[Dict[str, Any]] = None


# class MarketTickOut(BaseModel):
#     id: int
#     instrument_token: Optional[str] = None
#     tradingsymbol: str
#     ts: datetime
#     ltp: float
#     raw: Optional[Dict[str, Any]] = None

#     class Config:
#         from_attributes = True


# # =====================================================
# # BACKTEST
# # =====================================================
# class BacktestRequest(BaseModel):
#     symbol: str
#     dataset: str = "tick-demo"
#     from_date: datetime
#     to_date: datetime
#     slippage_pct: float = 0.05
#     commission: float = 0.1


# class BacktestResult(BaseModel):
#     trades: int
#     pnl: float
#     win_rate: float
#     max_drawdown: float


# class CandleBacktestRequest(BaseModel):
#     symbol: str
#     interval: str = "5m"
#     from_date: datetime
#     to_date: datetime
#     slippage_pct: float = 0.05
#     commission: float = 0.1


# class CandleBacktestResult(BaseModel):
#     trades: int
#     pnl: float
#     win_rate: float
#     max_drawdown: float


# # =====================================================
# # REWARDS
# # =====================================================
# class RewardOut(BaseModel):
#     id: int
#     name: str
#     reward_type: str
#     description: Optional[str]
#     amount: float
#     expires_at: Optional[datetime]
#     active: bool

#     class Config:
#         from_attributes = True


# class UserRewardOut(BaseModel):
#     id: int
#     user_id: int
#     reward: RewardOut
#     claimed: bool
#     claimed_at: Optional[datetime]

#     class Config:
#         from_attributes = True


# # =====================================================
# # HELP / SUPPORT
# # =====================================================
# class HelpCategoryOut(BaseModel):
#     id: int
#     name: str
#     description: Optional[str]
#     created_at: datetime
#     updated_at: datetime

#     class Config:
#         from_attributes = True


# class HelpArticleOut(BaseModel):
#     id: int
#     category_id: int
#     title: str
#     content: Optional[str]
#     is_active: bool
#     created_at: datetime
#     updated_at: datetime

#     class Config:
#         from_attributes = True




# app/schemas.py

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Any, Dict
from datetime import datetime

# =====================================================
# AUTH / USER
# =====================================================

class UserCreate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=255)
    email: EmailStr
    password: str


class LoginPayload(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    full_name: Optional[str]
    email: EmailStr
    is_active: bool
    is_superuser: bool
    created_at: datetime

    class Config:
        orm_mode = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    sub: Optional[str]
    exp: Optional[int]


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordPayload(BaseModel):
    token: str
    new_password: str


# =====================================================
# ADMIN / AUDIT / REPORTING
# =====================================================

class CredentialHistoryOut(BaseModel):
    id: int
    user_id: int
    action: str
    detail: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        orm_mode = True


class PaginatedResponse(BaseModel):
    total: int
    skip: int
    limit: int
    items: List[Any]


# =====================================================
# BILLING / SUBSCRIPTION
# =====================================================

class PlanOut(BaseModel):
    id: int
    name: str
    price: float
    currency: str
    interval: str
    features: Optional[Dict[str, Any]]
    is_active: bool

    class Config:
        orm_mode = True


class SubscribeIn(BaseModel):
    plan_id: int
    billing_cycle: str
    meta: Optional[Dict[str, Any]]


class SubscriptionOut(BaseModel):
    id: int
    user_id: int
    plan_name: str
    price: float
    currency: str
    interval: str
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    is_active: bool
    meta: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        orm_mode = True


class PaymentTransactionOut(BaseModel):
    id: int
    user_id: int
    order_id: Optional[str]
    payment_id: Optional[str]
    amount: float
    currency: str
    gateway: Optional[str]
    status: Optional[str]
    provider_response: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        orm_mode = True


# =====================================================
# WALLET
# =====================================================

class WalletOut(BaseModel):
    user_id: int
    balance: float
    withdrawable_balance: float
    updated_at: datetime

    class Config:
        orm_mode = True


class WalletTransactionOut(BaseModel):
    id: int
    user_id: int
    amount: float
    txn_type: str
    reference: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True


# =====================================================
# BROKER
# =====================================================

class BrokerConnectRequest(BaseModel):
    provider: str
    callback_url: Optional[str]


class BrokerStatusResponse(BaseModel):
    provider: str
    connected: bool
    account_info: Optional[Dict[str, Any]]


class BrokerAccountOut(BaseModel):
    id: int
    user_id: int
    provider: str
    account_name: Optional[str]
    client_id: Optional[str]
    created_at: datetime

    class Config:
        orm_mode = True


# =====================================================
# ORDERS / TRADES
# =====================================================

class SimpleOrderCreate(BaseModel):
    symbol: str
    qty: int
    side: str
    order_type: str = "MARKET"


class OrderCreate(BaseModel):
    symbol: str
    quantity: float
    price: Optional[float]
    order_type: str
    product: Optional[str]
    side: str
    tif: Optional[str]


class OrderResponse(BaseModel):
    id: int
    broker_order_id: Optional[str]
    user_id: int
    symbol: str
    quantity: float
    price: Optional[float]
    side: str
    status: str
    filled_qty: float
    avg_price: Optional[float]
    created_at: datetime
    meta: Optional[Dict[str, Any]]

    class Config:
        orm_mode = True


class CancelOrderResponse(BaseModel):
    ok: bool
    message: Optional[str]


class OrderHistoryItem(BaseModel):
    id: int
    symbol: str
    side: str
    quantity: float
    price: Optional[float]
    status: str
    created_at: datetime

    class Config:
        orm_mode = True


# =====================================================
# PORTFOLIO
# =====================================================

class PositionOut(BaseModel):
    symbol: str
    qty: int
    avg_price: float
    ltp: float
    pnl: float


# =====================================================
# STRATEGY
# =====================================================

class StrategyCreate(BaseModel):
    name: str
    description: Optional[str]
    config: Dict[str, Any]


class StrategyOut(BaseModel):
    id: int
    user_id: int
    name: str
    description: Optional[str]
    config: Dict[str, Any]
    is_active: bool
    created_at: datetime

    class Config:
        orm_mode = True


# =====================================================
# MARKET / TICKS
# =====================================================

class Tick(BaseModel):
    symbol: str
    ltp: float
    ts: float
    raw: Optional[Dict[str, Any]]


class MarketTickOut(BaseModel):
    id: int
    tradingsymbol: str
    ts: datetime
    ltp: float
    raw: Optional[Dict[str, Any]]

    class Config:
        orm_mode = True


# =====================================================
# BACKTEST
# =====================================================

class BacktestRequest(BaseModel):
    symbol: str
    dataset: str
    from_date: datetime
    to_date: datetime
    slippage_pct: float
    commission: float


class BacktestResult(BaseModel):
    trades: int
    pnl: float
    win_rate: float
    max_drawdown: float


class CandleBacktestRequest(BaseModel):
    symbol: str
    interval: str
    from_date: datetime
    to_date: datetime
    slippage_pct: float
    commission: float


class CandleBacktestResult(BaseModel):
    trades: int
    pnl: float
    win_rate: float
    max_drawdown: float


# =====================================================
# REWARDS
# =====================================================

class RewardOut(BaseModel):
    id: int
    name: str
    reward_type: str
    description: Optional[str]
    amount: float
    expires_at: Optional[datetime]
    active: bool

    class Config:
        orm_mode = True


class UserRewardOut(BaseModel):
    id: int
    user_id: int
    reward: RewardOut
    claimed: bool
    claimed_at: Optional[datetime]

    class Config:
        orm_mode = True


# =====================================================
# HELP / SUPPORT / NOTIFICATION
# =====================================================

class HelpCategoryOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class HelpArticleOut(BaseModel):
    id: int
    category_id: int
    title: str
    content: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class NotificationOut(BaseModel):
    id: int
    user_id: int
    title: str
    message: str
    is_read: bool
    created_at: datetime

    class Config:
        orm_mode = True
