from sqlalchemy import Integer
from sqlalchemy.orm import mapped_column
from app.db.base import Base


class Providers(Base):
    """Betting providers/bookmakers table"""

    __tablename__ = "providers"

    id = mapped_column(Integer, primary_key=True)


class Fixtures(Base):
    """Sports events/fixtures table"""

    __tablename__ = "fixtures"

    id = mapped_column(Integer, primary_key=True)


class Markets(Base):
    """Betting markets table"""

    __tablename__ = "markets"

    id = mapped_column(Integer, primary_key=True)


class OddsSnapshots(Base):
    """Historical odds snapshots from providers"""

    __tablename__ = "odds_snapshots"

    id = mapped_column(Integer, primary_key=True)


class PolyPrices(Base):
    """Polymarket prices table"""

    __tablename__ = "poly_prices"

    id = mapped_column(Integer, primary_key=True)


class Recommendations(Base):
    """Betting recommendations table"""

    __tablename__ = "recommendations"

    id = mapped_column(Integer, primary_key=True)


class ProviderMetrics(Base):
    """Metrics about providers performance"""

    __tablename__ = "provider_metrics"

    id = mapped_column(Integer, primary_key=True)
