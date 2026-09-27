from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from backend.database.connection import Base

# ==========================================
# 1. CÁC MODEL THỊ TRƯỜNG THẾ GIỚI
# ==========================================

class MarketPrice(Base):
    __tablename__ = "market_prices"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), index=True, nullable=False)  # GC=F (Vàng) hoặc CL=F (Dầu)
    timeframe = Column(String(10), default="1d")             # 1h, 4h, 1d
    timestamp = Column(DateTime, index=True, nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)

    indicators = relationship("TechnicalIndicator", back_populates="market_price", uselist=False, cascade="all, delete-orphan")


class TechnicalIndicator(Base):
    __tablename__ = "technical_indicators"

    id = Column(Integer, primary_key=True, index=True)
    market_price_id = Column(Integer, ForeignKey("market_prices.id"), nullable=False)
    rsi = Column(Float)
    macd = Column(Float)
    macd_signal = Column(Float)
    macd_hist = Column(Float)
    ema20 = Column(Float)
    ema50 = Column(Float)
    ema200 = Column(Float)
    atr = Column(Float)
    bb_upper = Column(Float)
    bb_middle = Column(Float)
    bb_lower = Column(Float)

    market_price = relationship("MarketPrice", back_populates="indicators")


class News(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(Text, nullable=False)
    content = Column(Text)
    source = Column(String(100))
    url = Column(Text, unique=True, nullable=False)
    published_at = Column(DateTime, index=True)
    topic = Column(String(100))                      # Military Action, Sanctions, OPEC...
    gold_impact_score = Column(Float)               # Trích xuất từ Gemini (-1.0 đến 1.0)
    oil_supply_threat_score = Column(Float)          # Trích xuất từ Gemini (0.0 đến 1.0)
    confidence_score = Column(Float)                # Độ tin cậy tin tức
    created_at = Column(DateTime, default=datetime.utcnow)


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), index=True, nullable=False)  # GC=F hoặc CL=F
    prediction_time = Column(DateTime, default=datetime.utcnow, index=True)
    target_horizon = Column(String(20))                       # 24h, 48h, 72h
    trend_signal = Column(Integer)                            # 1 (Tăng), 0 (Đi ngang), -1 (Giảm)
    probability = Column(Float)                               # Độ tin cậy của model (0.0 -> 1.0)
    price_min = Column(Float)                                 # Vùng giá dự báo thấp nhất
    price_max = Column(Float)                                 # Vùng giá dự báo cao nhất
    model_version = Column(String(50))                        # VD: LightGBM_v1.0
    created_at = Column(DateTime, default=datetime.utcnow)


# ==========================================
# 2. CÁC MODEL THỊ TRƯỜNG VIỆT NAM
# ==========================================

class VNCommodityPrice(Base):
    """Lưu trữ bảng giá Vàng, Xăng dầu tại Việt Nam"""
    __tablename__ = "vn_commodity_prices"

    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), index=True, nullable=False)  # 'GOLD_SJC', 'GOLD_RING_PNJ', 'GAS_RON95'...
    buy_price = Column(Float, nullable=True)                    # Giá mua vào (VNĐ)
    sell_price = Column(Float, nullable=True)                   # Giá bán ra (VNĐ)
    recorded_at = Column(DateTime, default=datetime.utcnow, index=True)


class VNSectorImpactForecast(Base):
    """Lưu trữ phân tích tác động nhóm ngành từ Gemini AI"""
    __tablename__ = "vn_sector_impact_forecast"

    id = Column(Integer, primary_key=True, index=True)
    sector_name = Column(String(100), index=True, nullable=False) # 'GOLD_JEWELRY_RETAIL', 'OIL_GAS_DOWNSTREAM'...
    sentiment_score = Column(Float, nullable=False)                # -1.0 (Tiêu cực) đến +1.0 (Tích cực)
    forecast_horizon = Column(String(20), default="1_WEEK")       # '1_WEEK', 'NEXT_PRICE_ADJUSTMENT'
    summary = Column(Text, nullable=True)                          # Lý do / Tóm tắt giải thích từ Gemini AI
    created_at = Column(DateTime, default=datetime.utcnow)


class VNMarketNews(Base):
    """Lưu trữ tin tức, nghị định, chính sách kinh tế / vàng / xăng dầu tại Việt Nam"""
    __tablename__ = "vn_market_news"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(Text, nullable=False)
    content = Column(Text, nullable=True)
    source = Column(String(200), nullable=True)         # VnExpress, CafeF, Báo Công Thương, PNJ...
    url = Column(Text, unique=True, nullable=False)
    published_at = Column(DateTime, index=True, nullable=True)
    category = Column(String(50), nullable=True)        # 'GOLD', 'FUEL', 'POLICY', 'MACRO'
    sentiment_score = Column(Float, nullable=True)     # Điểm đánh giá từ Gemini (-1.0 đến +1.0)
    summary = Column(Text, nullable=True)              # Tóm tắt tin từ Gemini
    created_at = Column(DateTime, default=datetime.utcnow)