from sqlalchemy import Column, Integer, String, DateTime, UniqueConstraint, Table, ForeignKey
from sqlalchemy.orm import declarative_base, object_session, relationship
from datetime import datetime

Base = declarative_base()

# Association table for many-to-many relationship
user_tracked_products = Table(
    'user_tracked_products', Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('product_id', Integer, ForeignKey('products.id'), primary_key=True)
)

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    tracked_products = relationship(
        'Product',
        secondary=user_tracked_products,
        back_populates='users'
    )

class Product(Base):
    __tablename__ = 'products'
    id = Column(Integer, primary_key=True)
    product_id = Column(String, unique=True, nullable=False)  # ASIN or Flipkart product ID
    product_url = Column(String, nullable=False)
    last_known_price = Column(String)
    last_checked = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    users = relationship(
        'User',
        secondary=user_tracked_products,
        back_populates='tracked_products'
    )
