from sqlalchemy import Column, Integer, String, BigInteger, UniqueConstraint, Index
from db import Base

class ImageItem(Base):
    __tablename__ = "images"

    id = Column(Integer, primary_key=True, autoincrement=True)
    image_id = Column(String, nullable=False, unique=True)  # stable ID (relative path)
    subset = Column(String, nullable=False)                 # train/valid/test/unknown
    image_relpath = Column(String, nullable=False)
    image_path = Column(String, nullable=True)              # local path for dev / disk-host
    image_url = Column(String, nullable=True)               # for S3/R2/Supabase storage


class Rating(Base):
    __tablename__ = "ratings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False)
    image_id = Column(String, nullable=False)
    subset = Column(String, nullable=False)

    erythema = Column(Integer)
    induration = Column(Integer)
    scaling = Column(Integer)
    overall_pga = Column(Integer)

    created_at = Column(BigInteger, nullable=False)

    __table_args__ = (
        UniqueConstraint("username", "image_id", name="uq_user_image"),
        Index("idx_ratings_image_id", "image_id"),
        Index("idx_ratings_username", "username"),
    )