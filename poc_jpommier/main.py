# This is a sample Python script.

# Press Maj+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.
import argparse
import logging
import json
import re
import regex
import urllib.parse

logger = logging.getLogger()


def process(log_dict):
    useful_extracts = {}

    # Root service (app)
    r = re.search(r"^/([\w]+)/", log_dict['RequestPath'])
    useful_extracts['app'] = r.group(1) if r else ""
    p = urllib.parse.unquote_plus(log_dict['RequestPath']).lower()
    # If OGC:
    if useful_extracts['app'] == "geoserver":
        #    - service type
        r = re.search(r"service=([\w]+)&", p)
        if r:
            # Extract matching values of all groups
            print(r.groups())
            useful_extracts['ogc_service'] = r.group(1)


            r = regex.findall(r"request=([\w]+)", p)
            if r:
                useful_extracts['ogc_request'] = r[0]

            #    - layer info
            # r = regex.findall(r"\L<words>", p, words=['wfs', 'wms', 'ows'])
            ns = ""
            r = re.search(r"geoserver/([\w]+)/wms?", p)
            if r:
                ns = r.group(1)

            ogc_layer=""
            r = regex.findall(r"layers=([:\w]+)", p)
            if r:
                ogc_layer = r[0]

            if ":" not in ogc_layer:
                ogc_layer = ns + ":" + ogc_layer

            useful_extracts['ogc_layer'] = ogc_layer

            ogc_format = ""
            r = regex.findall(r"format=([/\w]+)", p)
            if r:
                useful_extracts['ogc_format'] = ogc_layer = r[0]

    return useful_extracts


# Press the green button in the gutter to run the script.
if __name__ == '__main__':

    # Input arguments
    parser = argparse.ArgumentParser(description='''
    Extract useful information from the request-path (helper for the next step, log ingestion by promtail)
    ''')
    parser.add_argument('in_file', help='path to the source log file (json logs)')
    parser.add_argument('dest_file', help='path to the destiantion log file (json logs)')
    args = parser.parse_args()


    # INITIALIZE LOGGER
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
            '%(asctime)s %(name)-5s %(levelname)-3s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    loglevel = logging.DEBUG
    logger.setLevel(loglevel)

    # Using readlines()
    with open(args.in_file, 'r') as input, open(args.dest_file, 'w') as output:
        Lines = input.readlines()

        count = 0
        # Strips the newline character
        for line in Lines:
            count += 1
            logline = json.loads(line)
            useful_extracts = process(logline)
            logline.update(useful_extracts)
            logger.debug(logline)
            output.write(json.dumps(logline)+"\n")

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
