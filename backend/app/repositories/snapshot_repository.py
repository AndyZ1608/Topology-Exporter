"""SQLAlchemy repository for cached, non-authoritative topology snapshots."""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, JSON, String, create_engine, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from app.schemas.topology import TopologyResponse


class Base(DeclarativeBase):
    pass


class InventorySnapshot(Base):
    """A point-in-time normalized graph; OpenStack remains the source of truth."""

    __tablename__ = "inventory_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    status: Mapped[str] = mapped_column(String(16), default="success")
    topology: Mapped[dict] = mapped_column(JSON)


class SnapshotRepository:
    """Store and retrieve the latest normalized topology snapshot."""

    def __init__(self, database_url: str):
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        self._engine = create_engine(
            database_url,
            pool_pre_ping=True,
            connect_args=connect_args,
        )
        self._initialized = False

    def _initialize(self) -> None:
        if not self._initialized:
            Base.metadata.create_all(self._engine)
            self._initialized = True

    def save(self, topology: TopologyResponse, status: str = "success") -> None:
        self._initialize()
        now = datetime.now(timezone.utc)
        snapshot = InventorySnapshot(
            discovered_at=topology.timestamp,
            last_seen_at=now,
            status=status,
            topology=topology.model_dump(mode="json"),
        )
        with Session(self._engine) as session:
            session.add(snapshot)
            session.commit()

    def load_latest(self) -> TopologyResponse | None:
        self._initialize()
        statement = select(InventorySnapshot).order_by(InventorySnapshot.id.desc()).limit(1)
        with Session(self._engine) as session:
            snapshot = session.scalar(statement)
            if snapshot is None:
                return None
            return TopologyResponse.model_validate(snapshot.topology)
