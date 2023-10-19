import unittest

from georchestra_analytics.log_processors import core


class TestProcessLogFile(unittest.TestCase):
  def test_read_sp(self):
    # core.process_log_file("../sample_data/sp_sample_gs_logs.log")
    self.assertEqual(True, True)  # add assertion here


if __name__ == '__main__':
  unittest.main()
