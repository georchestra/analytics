import logging
import random
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import create_engine, func, desc, asc, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.dialects.postgresql import insert

from georchestra_analytics_cli.access_logs.log_parsers.AbstractLogParser import AbstractLogParser
from georchestra_analytics_cli.access_logs.log_parsers.FakeLogGenerator import FakeLogGenerator
from georchestra_analytics_cli.access_logs.log_parsers.OpentelemetryLogParser import OpentelemetryLogParser
from georchestra_analytics_cli.access_logs.log_parsers.RegexLogParser import RegexLogParser
from georchestra_analytics_cli.common.models import AccessLogRecord, Base, \
    OpentelemetryAccessLogRecord
from georchestra_analytics_cli.config import Config
from georchestra_analytics_cli.config import get_config

logger = logging.getLogger(__name__)


class AccessLogProcessor:
    """
    Main class for processing access log records.
    Supports processing from different input sources:
    - buffer table in database
    - classic access log files (CFL or custom format)
    - generate fake log records for testing purposes
    Writes on a single kind of output: a database table, expected to be a timescaleDB-enabled table.
    """
    config: Config = None
    batch_size: int = None
    db_engine = None
    Session: sessionmaker = None
    log_parser: AbstractLogParser = None
    keys_blacklist: list = []

    def __init__(self):
        self.config = get_config()
        self.batch_size = self.config.get_batch_size()
        self.keys_blacklist = self.config.get_keys_blacklist()

    def process_buffer_table(self):
        """
        Fetch the log records from a database buffer table, process them and insert them in the access_logs table.
        The buffer table's content is expected to come from data collected by an OpenTelemetry collector.
        The process is paginated in batches of self.batch_size.
        """
        self.log_parser = OpentelemetryLogParser(self.config)

        now = datetime.now(timezone.utc)
        with self.get_session() as session:
            offset = 0
            count_rows_stmt = select(func.count(OpentelemetryAccessLogRecord.span_id)).where(OpentelemetryAccessLogRecord.timestamp < now)
            nb_lines = session.scalar(count_rows_stmt)
            logger.debug(
                f"Number accesslog records to process from the buffer table: {nb_lines}"
            )

            while nb_lines > 0:
                processed_log_records = list()
                try:
                    stmt = select(OpentelemetryAccessLogRecord).order_by(desc(OpentelemetryAccessLogRecord.timestamp),
                                                                  asc(OpentelemetryAccessLogRecord.span_id)).slice(offset,
                                                                                                            offset + self.batch_size)
                    for log in session.scalars(stmt):
                        # logger.debug(log)
                        processed_log_records.append(self.log_parser.parse(log))

                    # Remove invalid records
                    processed_log_records = [p for p in processed_log_records if p is not None]
                    if processed_log_records:
                        self.upsert_log_records(session, processed_log_records)
                    # prepare next loop iteration
                    nb_lines -= self.batch_size
                    offset += self.batch_size
                except SQLAlchemyError as e:
                    # For now, a commit error will lead to the loss of the full batch (see self.batch_size)
                    logger.error(f"Error while processing the buffer table: {e}")
                    session.rollback()

            # Drop the processed lines from the buffer
            try:
                session.query(OpentelemetryAccessLogRecord).filter(
                    OpentelemetryAccessLogRecord.timestamp < now).delete(synchronize_session=False)
                session.commit()
            except SQLAlchemyError as e:
                # For now, a commit error will lead to the loss of the full batch (see self.batch_size)
                logger.error(f"Error deleting files from the buffer table: {e}")
                session.rollback()

    def process_file_logs(self, log_file_path, extra_info: dict[str, Any] = None):
        """
        Fetch the log records from a textual log file (e.g., CLF file), process them using a regular expression (set in
        configuration, default is CLF)and insert them in the access_logs table.
        :param log_file_path:
        :return:
        """
        self.log_parser = RegexLogParser(self.config)
        self.log_parser.set_extra_info(extra_info)

        with open(log_file_path, 'r') as logs_data, self.get_session() as session:
            processed_log_records = list()
            try:
                while True:
                    line = logs_data.readline()
                    # if line is empty, end of file is reached
                    if not line:
                        break

                    lr = self.log_parser.parse(line)
                    if self.keys_blacklist:
                        # Cover data_privacy issues by allowing to blacklist (not collect) some sensitive data if necessary
                        for k in self.keys_blacklist:
                            lr.pop(k, None)
                    if lr is not None:
                        lr["context_data"]["source"] = log_file_path
                        processed_log_records.append(lr)


                    if processed_log_records and len(processed_log_records) % self.batch_size == 0:
                        self.upsert_log_records(session, processed_log_records)

                # Last commit at the end of the loop, commit remaining batch
                if len(processed_log_records) > 0:
                    self.upsert_log_records(session, processed_log_records)


            except SQLAlchemyError as e:
                # For now, a commit error will lead to the loss of the full batch (see self.batch_size)
                logger.error(f"Error deleting files from the buffer table: {e}")
                session.rollback()

    def get_session(self)->Session:
        if not self.db_engine:
            self.db_engine = create_engine(self.config.get_db_connection_string() )
            # Base.metadata.create_all(self.db_engine, checkfirst=True)
        if not self.Session:
            self.Session = sessionmaker(self.db_engine)
        return self.Session()

    def upsert_log_records(self, session: Session,  log_records: list[dict[str, Any]]):
        """
        Performs a bulk "upsert" action (leverages the PostgreSQL ON UPDATE DO something clause)
        on a list of AccessLog records (provided as dicts).
        For now, it only supports the "do nothing" action.
        TODO: consider supporting on_conflict_do_update as hinted on  https://stackoverflow.com/a/63189754
        """
        if len(log_records) == 0:
            return
        insert_stmt = insert(AccessLogRecord).values(log_records)
        insert_stmt = insert_stmt.on_conflict_do_nothing(index_elements=["ts", "id"])
        session.execute(insert_stmt)
        session.commit()

    def fake_log_records(self, start_date: datetime, stop_time: datetime, max_rate: int):
        """
        Generates fake log records between specified start and stop times with a given rate.

        This function simulates the creation of log records for testing or analysis. It
        increments the time between records based on the provided rate, generating
        entries in the specified time interval.

        Parameters
        ----------
        start_date : datetime
            The start date and time for the log records.
        stop_time : datetime
            The stop date and time for the log records.
        max_rate : int
            The nb of log records per hour.

        Returns
        -------
        None
        """
        self.log_parser = FakeLogGenerator(self.config)
        start = start_date
        with self.get_session() as session:
            processed_log_records = list()
            try:
                while start <  stop_time:
                    nb_records = random.randint(0, max_rate)
                    for _ in range(nb_records):
                        st = start.astimezone(timezone.utc) + timedelta(seconds = random.randint(0, 3600))
                        record = self.log_parser.parse(st)
                        processed_log_records.append(record)

                        if processed_log_records and len(processed_log_records) % self.batch_size == 0:
                            logger.debug(f"Upserting {len(processed_log_records)} log records")
                            self.upsert_log_records(session, processed_log_records)
                    logger.debug(f"[{start.strftime('%m/%d/%Y, %H:%M %Z')} - {(start + timedelta(hours=1)).strftime('%m/%d/%Y, %H:%M %Z')}] Generated {nb_records} log records")
                    start = start + timedelta(hours=1)

                # Last commit at the end of the loop, commit remaining batch
                if len(processed_log_records) > 0:
                    self.upsert_log_records(session, processed_log_records)
            except SQLAlchemyError as e:
                # For now, a commit error will lead to the loss of the full batch (see self.batch_size)
                logger.error(f"Error loading fake data into the table: {e}")
                session.rollback()
