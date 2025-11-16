"""
Modelo de log para webhooks
"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, Integer, String, DateTime, JSON, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class WebhookLog(Base):
    """Log de webhooks recebidos"""
    __tablename__ = "webhook_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    payload = Column(JSON, nullable=False)
    headers = Column(JSON, nullable=True)
    status = Column(String(50), nullable=False, default="received")  # received, processing, completed, failed
    response = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    processing_time = Column(Integer, nullable=True)  # em segundos
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f"<WebhookLog(id={self.id}, event={self.event_type}, status={self.status})>"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type,
            "status": self.status,
            "payload": self.payload,
            "response": self.response,
            "error_message": self.error_message,
            "processing_time": self.processing_time,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }