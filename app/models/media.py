import uuid

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Media(Base):
    __tablename__ = "media_content"

    id: Mapped[str] = mapped_column(
        primary_key=True, default=lambda: str(uuid.uuid4()), unique=True
    )
    title: Mapped[str] = mapped_column(index=True)
    file_type: Mapped[str] = mapped_column()
    file_size: Mapped[int] = mapped_column(default=0)
    file_path: Mapped[str] = mapped_column()
