"""CardConfig ORM model."""

from datetime import datetime, timezone

from sqlalchemy import Integer, String, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class CardConfig(Base):
    __tablename__ = "card_configs"
    __table_args__ = (
        UniqueConstraint(
            "student_id", "unit_id", "attribute_type",
            name="uq_card_config_student_unit_attr",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    student_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("students.id"), nullable=False
    )
    unit_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("units.id"), nullable=False
    )
    attribute_type: Mapped[str] = mapped_column(String, nullable=False)
    attribute_value: Mapped[str] = mapped_column(String, nullable=False)
    available_options: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    student: Mapped["Student"] = relationship("Student", back_populates="card_configs")
    unit: Mapped["Unit"] = relationship("Unit", back_populates="card_configs")
