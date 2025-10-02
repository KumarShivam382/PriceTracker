from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    products = relationship("TrackedProduct", back_populates="user")

class TrackedProduct(Base):
    __tablename__ = 'tracked_products'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    product_id = Column(String, nullable=False)  # ASIN or Flipkart product ID
    product_url = Column(String, nullable=False) # Original/cleaned URL
    last_known_price = Column(String)
    last_checked = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="products")
    __table_args__ = (UniqueConstraint('user_id', 'product_id', name='_user_product_uc'),)
