
import logging
from logging.config import fileConfig

from log_processors import core


fileConfig("logging_config.ini")

if __name__ == '__main__':
  logging.info("running")
  core.process_log_file("../sample_data/sp_sample_gs_logs.log")