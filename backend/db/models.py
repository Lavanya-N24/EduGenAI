"""
EduGenAI - SQLAlchemy ORM Models
Defines tables for users, adaptive quizzes, topic statistics, video generation records, and share links.
"""
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    JSON,
    Text,
)
from sqlalchemy.orm import relationship
from db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String(128), primary_key=True)  # Firebase UID or local identifier
    email = Column(String(255), nullable=True)
    display_name = Column(String(255), nullable=True)
    current_difficulty = Column(String(32), default="medium")
    total_quizzes = Column(Integer, default=0)
    total_correct = Column(Integer, default=0)
    total_questions = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    quiz_attempts = relationship("QuizAttempt", back_populates="user", cascade="all, delete-orphan")
    topic_stats = relationship("TopicStat", back_populates="user", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "email": self.email,
            "display_name": self.display_name,
            "current_difficulty": self.current_difficulty,
            "total_quizzes": self.total_quizzes,
            "total_correct": self.total_correct,
            "total_questions": self.total_questions,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(128), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    topic = Column(String(255), nullable=False, index=True)
    correct = Column(Integer, default=0)
    total = Column(Integer, default=0)
    score = Column(Float, default=0.0)
    difficulty = Column(String(32), default="medium")
    question_details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="quiz_attempts")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "topic": self.topic,
            "correct": self.correct,
            "total": self.total,
            "score": self.score,
            "difficulty": self.difficulty,
            "question_details": self.question_details,
            "timestamp": self.created_at.isoformat() if self.created_at else None,
        }


class TopicStat(Base):
    __tablename__ = "topic_stats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(128), ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    topic = Column(String(255), nullable=False, index=True)
    avg_score = Column(Float, default=0.0)
    attempts = Column(Integer, default=0)
    last_difficulty = Column(String(32), default="medium")
    recent_scores = Column(JSON, default=list)  # List of last 10 scores
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="topic_stats")

    def to_dict(self) -> dict:
        return {
            "topic": self.topic,
            "avg_score": self.avg_score,
            "attempts": self.attempts,
            "last_difficulty": self.last_difficulty,
            "recent_scores": self.recent_scores or [],
        }


class VideoRecord(Base):
    __tablename__ = "video_records"

    id = Column(String(64), primary_key=True)
    user_id = Column(String(128), index=True, nullable=False)
    filename = Column(String(255), unique=True, index=True, nullable=False)
    title = Column(String(255), nullable=False)
    duration = Column(Float, default=0.0)
    scenes = Column(Integer, default=1)
    language = Column(String(32), default="en")
    learning_mode = Column(String(32), default="beginner")
    render_time = Column(Float, default=0.0)
    video_url = Column(String(512), nullable=False)
    share_token = Column(String(64), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "filename": self.filename,
            "title": self.title,
            "duration": self.duration,
            "scenes": self.scenes,
            "language": self.language,
            "learning_mode": self.learning_mode,
            "render_time": self.render_time,
            "video_url": self.video_url,
            "share_token": self.share_token,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ShareLink(Base):
    __tablename__ = "share_links"

    token = Column(String(64), primary_key=True)
    user_id = Column(String(128), index=True, nullable=False)
    filename = Column(String(255), index=True, nullable=False)
    title = Column(String(255), nullable=False)
    duration = Column(Float, default=0.0)
    views = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    def to_dict(self) -> dict:
        return {
            "token": self.token,
            "user_id": self.user_id,
            "filename": self.filename,
            "title": self.title,
            "duration": self.duration,
            "views": self.views,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
