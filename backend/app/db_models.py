"""SQLAlchemy ORM table definitions for the fitness evaluation platform.

Four tables:
- ``coaches``          — registered coach accounts
- ``clients``          — clients owned by a coach (strict per-coach isolation)
- ``body_measurements``— timestamped measurement snapshots per client
- ``assessments``      — timestamped assessment result blobs per client

Import this module before calling ``database.create_tables()`` so all models
are registered with ``Base.metadata``.
"""

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Coach(Base):
    """A registered fitness coach account."""

    __tablename__ = "coaches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    clients: Mapped[list["Client"]] = relationship(
        "Client", back_populates="coach", cascade="all, delete-orphan"
    )


class Client(Base):
    """A client belonging to a coach.

    The ``(coach_id, name)`` UNIQUE constraint enforces strict per-coach
    client isolation — two coaches may have clients with the same name.
    ``height_cm`` is stored here (static); weight/waist/hip/neck live in
    ``body_measurements`` as time-series snapshots.
    """

    __tablename__ = "clients"
    __table_args__ = (
        UniqueConstraint("coach_id", "name", name="uq_client_coach_name"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    coach_id: Mapped[int] = mapped_column(
        ForeignKey("coaches.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    gender: Mapped[str] = mapped_column(String(8), nullable=False)
    goals: Mapped[str] = mapped_column(Text, default="[]")          # JSON list[str]
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    preferred_activities: Mapped[str] = mapped_column(Text, default="[]")  # JSON list[str]
    equipment_available: Mapped[str] = mapped_column(Text, default="[]")   # JSON list[str]
    saved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    coach: Mapped["Coach"] = relationship("Coach", back_populates="clients")
    measurements: Mapped[list["BodyMeasurement"]] = relationship(
        "BodyMeasurement", back_populates="client", cascade="all, delete-orphan"
    )
    assessments: Mapped[list["Assessment"]] = relationship(
        "Assessment", back_populates="client", cascade="all, delete-orphan"
    )


class BodyMeasurement(Base):
    """A timestamped body-composition measurement snapshot for a client.

    Computed fields (``bmi``, ``body_fat_pct``, ``fat_mass_kg``,
    ``lean_mass_kg``) are populated by the service layer, not stored as
    raw inputs.
    """

    __tablename__ = "body_measurements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    measured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    waist_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    hip_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    neck_cm: Mapped[float | None] = mapped_column(Float, nullable=True)
    bmi: Mapped[float | None] = mapped_column(Float, nullable=True)
    body_fat_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    body_fat_rating: Mapped[str | None] = mapped_column(String(32), nullable=True)
    fat_mass_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    lean_mass_kg: Mapped[float | None] = mapped_column(Float, nullable=True)

    client: Mapped["Client"] = relationship("Client", back_populates="measurements")


class Assessment(Base):
    """A single timestamped assessment snapshot for a client.

    ``results_json`` stores the full ``list[MetricResult]`` as a JSON
    blob, preserving the existing Pydantic shape without a complex
    per-metric table.
    """

    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"), nullable=False
    )
    assessed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    results_json: Mapped[str] = mapped_column(Text, nullable=False)

    client: Mapped["Client"] = relationship("Client", back_populates="assessments")
