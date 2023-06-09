
#-------------------------------------------------------------------------------
#
#  Ce script permet de créer des statistiques sur les services de geOrchestra.
#
#  Le script traite les informations des logs de la brique de sécurité de geOrchestra
#  afin d'en extraire les informations utiles pour les administrateurs
#
# Licence:     GPL 3
#
#-------------------------------------------------------------------------------

import os
import sys
import argparse
from argparse import RawTextHelpFormatter
from datetime import date, timedelta, datetime


# répertoire courant
script_dir = os.path.dirname(__file__)


# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
# +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++




def main():


  parser = argparse.ArgumentParser(description="""
This script allows you to believe the statistics on the geOrchestra services.
  
The script traces the information from the logs of the geOrchestra security module
in order to extract useful information for administrators.

Exemple : analyze_logs.py sec-proxy /var/logs/geor/security-proxy.2018-01-02.log
""", formatter_class=RawTextHelpFormatter)


  # setup the arguments
  parser.add_argument("source", help="""source of the logs to treat. Can be 'sec-proxy' or 'gateway'.""")
  parser.add_argument("logfile", help="""path to the logfile to analyze""")

  # debug
  #print( 'Number of arguments:', len(sys.argv), 'arguments.' )
  #print( 'Argument List:', str(sys.argv) )


  # variables globales
  global logsource
  global logfile

  # on teste les infos passées en arguments
  test_logsource = False
  test_logfile = False

  try:
    logsource = str(sys.argv[1])
    logfile = str(sys.argv[2])
  except:
    print("\nThere is an error in the arguments. Please retry.\n")
    parser.print_help()
    sys.exit()



  print( "")
  print( "  END")

  return

if __name__ == '__main__':
    main()

