"""Unit ORM model."""

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Unit(Base):
    __tablename__ = "units"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    week_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    week_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    unlock_attribute: Mapped[str] = mapped_column(String, nullable=False)
    sort_order: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    learning_records: Mapped[list["LearningRecord"]] = relationship(
        "LearningRecord", back_populates="unit"
    )
    card_configs: Mapped[list["CardConfig"]] = relationship(
        "CardConfig", back_populates="unit"
    )
