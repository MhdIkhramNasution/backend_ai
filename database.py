from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    ForeignKey
)

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# ================= DATABASE URL =================

DATABASE_URL = "sqlite:///./users.db"

# ================= ENGINE =================

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# ================= SESSION =================

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# ================= BASE =================

Base = declarative_base()

# ================= USERS TABLE =================

class User(Base):

    __tablename__ = "users"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    username = Column(
        String,
        unique=True
    )

    email = Column(
        String,
        unique=True
    )

    phone = Column(String)

    password = Column(String)

# ================= ITEMS TABLE =================

class Item(Base):

    __tablename__ = "items"

    item_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id")
    )

    item_name = Column(String)

    stock = Column(Integer)

    image = Column(String)

    expiry_days = Column(Integer)

    status = Column(String)

# ================= CREATE TABLE =================
class ScanResult(Base):

    __tablename__ = "scan_results"

    scan_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id")
    )

    image = Column(String)

    prediction = Column(String)

    confidence = Column(String)

    scanned_at = Column(String)

# ================= CREATE USER POINT =================

class UserPoint(Base):

    __tablename__ = "user_points"

    point_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id")
    )

    points = Column(
        Integer,
        default=0
    )

class RewardHistory(Base):

    __tablename__ = "reward_history"

    reward_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id")
    )

    reward_name = Column(String)

    points_used = Column(Integer)

    redeemed_at = Column(String)


class Voucher(Base):

    __tablename__ = "vouchers"

    voucher_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    title = Column(String)

    description = Column(String)

    points_required = Column(Integer)

    image = Column(String)

    status = Column(
        String,
        default="available"
    )


class RedeemHistory(Base):

    __tablename__ = "redeem_history"

    redeem_id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id")
    )

    voucher_id = Column(
        Integer,
        ForeignKey("vouchers.voucher_id")
    )

    redeemed_at = Column(String)

    status = Column(
        String,
        default="available"
    )

Base.metadata.create_all(bind=engine)