"""
Metrics and performance tracking models
"""
from sqlalchemy import Column, String, ForeignKey, Integer, DECIMAL, DateTime, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from app.models.base import BaseModel


class ResponseTimeMetric(BaseModel):
    """Response time metrics model"""
    __tablename__ = "response_time_metrics"
    
    request_id = Column(UUID(as_uuid=True), ForeignKey("panic_requests.id"), nullable=False)
    firm_id = Column(UUID(as_uuid=True), ForeignKey("security_firms.id"), nullable=False)
    service_type = Column(String(20), nullable=False)
    zone_name = Column(String(255), nullable=False)
    
    # Time measurements in seconds
    response_time = Column(Integer, nullable=True)  # Time from request to acceptance
    arrival_time = Column(Integer, nullable=True)   # Time from acceptance to arrival
    total_time = Column(Integer, nullable=True)     # Total time from request to arrival
    
    # Location for zone analysis
    request_location = Column(Geometry("POINT", srid=4326), nullable=False)
    
    # Relationships
    request = relationship("PanicRequest")
    firm = relationship("SecurityFirm")


class PerformanceAlert(BaseModel):
    """Performance alert model"""
    __tablename__ = "performance_alerts"
    
    firm_id = Column(UUID(as_uuid=True), ForeignKey("security_firms.id"), nullable=False)
    alert_type = Column(String(50), nullable=False)  # slow_response, high_prank_rate, etc.
    severity = Column(String(20), nullable=False)    # low, medium, high, critical
    zone_name = Column(String(255), nullable=True)
    service_type = Column(String(20), nullable=True)
    message = Column(Text, nullable=False)
    metric_value = Column(DECIMAL(10, 2), nullable=True)
    threshold_value = Column(DECIMAL(10, 2), nullable=True)
    is_resolved = Column(Boolean, default=False, nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    firm = relationship("SecurityFirm")


class ZonePerformanceReport(BaseModel):
    """Zone performance report model"""
    __tablename__ = "zone_performance_reports"
    
    firm_id = Column(UUID(as_uuid=True), ForeignKey("security_firms.id"), nullable=False)
    zone_name = Column(String(255), nullable=False)
    service_type = Column(String(20), nullable=False)
    report_date = Column(DateTime(timezone=True), nullable=False)
    
    # Metrics
    total_requests = Column(Integer, default=0, nullable=False)
    avg_response_time = Column(DECIMAL(10, 2), nullable=True)
    min_response_time = Column(Integer, nullable=True)
    max_response_time = Column(Integer, nullable=True)
    avg_arrival_time = Column(DECIMAL(10, 2), nullable=True)
    prank_count = Column(Integer, default=0, nullable=False)
    prank_percentage = Column(DECIMAL(5, 2), nullable=True)
    
    # Relationships
    firm = relationship("SecurityFirm")