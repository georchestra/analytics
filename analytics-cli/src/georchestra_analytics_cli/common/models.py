from datetime import datetime
from typing import Any, Optional, List

from sqlalchemy import MetaData, String, Integer, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import MappedAsDataclass
from sqlalchemy.orm import mapped_column
from sqlalchemy.types import JSON

# set schema for all tables
# (see https://docs.sqlalchemy.org/en/20/orm/declarative_tables.html#orm-declarative-table-configuration)
metadata_obj = MetaData(schema="analytics")


class Base(DeclarativeBase):
    metadata = metadata_obj
    type_annotation_map = {
        dict[str, Any]: JSON
    }


class OpentelemetryAccessLogRecord(MappedAsDataclass, Base):
    """User class will be converted to a dataclass"""

    __tablename__ = "opentelemetry_buffer"

    timestamp: Mapped[datetime] = mapped_column(init=False, primary_key=True)
    span_id: Mapped[Optional[str]] = mapped_column(init=False, primary_key=True)
    trace_id: Mapped[Optional[str]]
    message: Mapped[str] = mapped_column()
    attributes: Mapped[Optional[dict[str, Any]]]
    resources: Mapped[Optional[dict[str, Any]]]
    scope: Mapped[Optional[dict[str, Any]]]
    source_type: Mapped[Optional[str]] = mapped_column()
    severity_text: Mapped[Optional[str]] = mapped_column()
    severity_number: Mapped[Optional[int]] = mapped_column()
    observed_timestamp: Mapped[Optional[datetime]] = mapped_column()
    flags: Mapped[Optional[int]] = mapped_column()
    dropped_attributes_count: Mapped[Optional[int]] = mapped_column()

    def __repr__(self) -> str:
        return f"OpentelemetryAccessLogRecord(time={self.timestamp!r}, span_id={self.span_id!r}, msg={self.message!r})"


class AccessLogRecord(MappedAsDataclass, Base):
    """User class will be converted to a dataclass"""

    __tablename__ = "access_logs"
    __table_args__ = (
        UniqueConstraint("ts", "id", name="idx_id_timestamp"),
    )

    oid: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    id: Mapped[Optional[str]]
    ts: Mapped[datetime] = mapped_column()
    message: Mapped[str] = mapped_column()
    app_path: Mapped[str] = mapped_column()
    app_name: Mapped[str] = mapped_column()
    user_id: Mapped[str] = mapped_column()
    user_name: Mapped[str] = mapped_column()
    org_id: Mapped[str] = mapped_column()
    org_name: Mapped[str] = mapped_column()
    roles: Mapped[List[str]] = mapped_column(ARRAY(String))
    auth_method: Mapped[str] = mapped_column()
    request_method: Mapped[str] = mapped_column()
    request_path: Mapped[str] = mapped_column()
    request_query_string: Mapped[str] = mapped_column()
    request_details: Mapped[Optional[dict[str, Any]]]
    response_time: Mapped[Optional[int]]
    response_size: Mapped[Optional[int]]
    status_code: Mapped[Optional[int]]
    context_data: Mapped[Optional[dict[str, Any]]]


    def __repr__(self) -> str:
        return f"AccessLogRecord(oid={self.oid!r}, time={self.ts!r}, span_id={self.id!r}, msg={self.message!r})"

# place a unique index on AccessLogRecord ts, id
Index("idx_id_timestamp", AccessLogRecord.ts, AccessLogRecord.id, unique=True)