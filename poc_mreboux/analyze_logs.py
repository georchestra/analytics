# -------------------------------------------------------------------------------
#
#  Ce script permet de créer des statistiques sur les services de geOrchestra.
#
#  Le script traite les informations des logs de la brique de sécurité de geOrchestra
#  afin d'en extraire les informations utiles pour les administrateurs
#
# Licence:     GPL 3
#
# -------------------------------------------------------------------------------

import os
import sys
import argparse
from argparse import RawTextHelpFormatter
import datetime
import time
import pandas as pd

# répertoire courant
script_dir = os.path.dirname(__file__)


# ==============================================================================

def getChrono(startTime, stopTime):
    # version en h min s
    hours, rem = divmod(stopTime - startTime, 3600)
    minutes, seconds = divmod(rem, 60)

    diffTime = "{:0>2}:{:0>2}:{:05.2f}".format(int(hours), int(minutes), seconds)
    return (diffTime)


# ==============================================================================


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
    # print( 'Number of arguments:', len(sys.argv), 'arguments.' )
    # print( 'Argument List:', str(sys.argv) )

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

    # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    print("")
    print("Reading the logfile " + logfile)

    startTime = time.perf_counter()

    # lecture du fichier et transformation en dataframe Pandas
    logfile_size = round(os.stat(logfile).st_size / (1024*1024))
    print(f"file size is {logfile_size} MB")

    log_frame = pd.read_csv(logfile, delimiter='€', encoding='utf-8', chunksize=10000, engine='python')


    print("done in " + getChrono(startTime, time.perf_counter()))
    print("")

    # close the logfile
    del log_frame

    print("")
    print("END")

    return


if __name__ == '__main__':
    main()
