#!/usr/bin/python3
import time

import click
import logging
from logging.config import fileConfig
import psycopg2

from georchestra_analytics import log_processors

# Configure logging
fileConfig("logging_config.ini")


# if __name__ == '__main__':
#   logging.info("running")
#   core.process_log_file("../sample_data/sp_sample_gs_logs.log")
#   core.process_log_file("../sample_data/sp_sample_gn_logs.log")


@click.group()
def cli():
    pass


@cli.command()
@click.option('--log_format', help='regexp string to parse the logs', default=log_processors.core.logformat_default)
@click.option('--pghost', help='target timescaleDB hostname')
@click.option('--pgport', help='target timescaleDB port')
@click.option('--pgname', help='target timescaleDB name')
@click.option('--pgtable', help='target timescaleDB table (with schema)')
@click.option('--pguser', help='target timescaleDB user')
@click.option('--pgpassword', help='target timescaleDB user')
@click.argument('source_file')
def process_logs(log_format:str, pghost: str, pgport: str, pgname: str, pgtable: str, pguser: str, pgpassword: str,
                 source_file: str):
    """
    Read logs, process them and extract relevant information for analytics. Publish to DB if connexion info is provided
    The logs will be parsed using the log_format string. It uses a sensible default, but this might not match your config.
    See https://httpd.apache.org/docs/current/mod/mod_log_config.html for how to adapt it to your needs
    """
    starttime = time.time()

    db_conn_string = f"postgresql://{pguser}:{pgpassword}@{pghost}:{pgport}/{pgname}"
    nb, csv = log_processors.process_log_file(source_file, log_format)
    logging.info(f"written {nb} log lines to file {csv}")

    logging.info(f"{time.time() - starttime } since startup")
    # publish to DB using copy_from which seems to be among the most performant flows according to
    #       https://naysan.ca/2020/05/09/pandas-to-postgresql-using-psycopg2-bulk-insert-performance-benchmark/
    conn=None
    try:
        # connect to the PostgreSQL server
        logging.debug('Connecting to the PostgreSQL database...')
        conn = psycopg2.connect(db_conn_string)

        # create a cursor
        cur = conn.cursor()

        # write the csv file to DB
        # taken from https://www.laurivan.com/load-a-csv-file-with-header-in-postgres-via-psycopg/
        SQL_STATEMENT = """
            COPY %s FROM STDIN WITH
                CSV
                HEADER
                DELIMITER AS ';'
            """
        f = open(csv, 'r')
        cur.copy_expert(sql=SQL_STATEMENT % pgtable, file=f)
        conn.commit()
        f.close()

        # close the communication with the PostgreSQL
        cur.close()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if conn is not None:
            conn.close()
            logging.debug('Database connection closed.')

    logging.info(f"{time.time() - starttime } since startup")


if __name__ == '__main__':
    cli(auto_envvar_prefix='GEORCHESTRA_ANALYTICS')
