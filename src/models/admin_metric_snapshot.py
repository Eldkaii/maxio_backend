from sqlalchemy import Column, Date, Integer, JSON, UniqueConstraint

from src.database import Base


class AdminMetricSnapshot(Base):
    """Daily aggregate measurements for the administration dashboard."""

    __tablename__ = "admin_metric_snapshots"
    __table_args__ = (UniqueConstraint("snapshot_date", name="uq_admin_metric_snapshot_date"),)

    id = Column(Integer, primary_key=True)
    snapshot_date = Column(Date, nullable=False, index=True)
    metrics = Column(JSON, nullable=False)
