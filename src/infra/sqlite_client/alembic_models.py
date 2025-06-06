"""
SQLAlchemy models for Alembic migrations
"""
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'user'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    discussion_structures = relationship("DiscussionStructure", back_populates="user", cascade="all, delete-orphan")
    user_chat_positions = relationship("UserChatPosition", back_populates="user", cascade="all, delete-orphan")


class DiscussionStructure(Base):
    __tablename__ = 'discussionstructure'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(String(255), unique=True, nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    serialized_structure = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="discussion_structures")
    messages = relationship("Message", back_populates="discussion_structure", cascade="all, delete-orphan")
    user_chat_positions = relationship("UserChatPosition", back_populates="discussion_structure", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_discussion_user', 'user_id'),
    )


class Message(Base):
    __tablename__ = 'message'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(String(255), unique=True, nullable=False)
    discussion_structure_id = Column(Integer, ForeignKey('discussionstructure.id'), nullable=False)
    content = Column(Text, nullable=False)
    role = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    discussion_structure = relationship("DiscussionStructure", back_populates="messages")
    llm_details = relationship("LLMDetails", back_populates="message", uselist=False, cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_message_discussion', 'discussion_structure_id'),
    )


class LLMDetails(Base):
    __tablename__ = 'llmdetails'
    
    id = Column(Integer, primary_key=True)
    message_id = Column(Integer, ForeignKey('message.id'), unique=True, nullable=False)
    model = Column(String(255))
    provider = Column(String(255))
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)
    total_tokens = Column(Integer)
    
    # Relationships
    message = relationship("Message", back_populates="llm_details")


class UserChatPosition(Base):
    __tablename__ = 'userchatposition'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id'), nullable=False)
    discussion_structure_id = Column(Integer, ForeignKey('discussionstructure.id'), nullable=False)
    last_position = Column(String(255), nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="user_chat_positions")
    discussion_structure = relationship("DiscussionStructure", back_populates="user_chat_positions")
    
    # Indexes
    __table_args__ = (
        Index('idx_position_user_discussion', 'user_id', 'discussion_structure_id', unique=True),
    )