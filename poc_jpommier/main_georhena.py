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


def process(log_line):
    useful_extracts = {}
    # Get request path
    r = regex.findall(r"(GET|POST|PUT|PATCH)\s([\w/?=&.%]+)", log_line)
    if not r or not r[0]:
        return ""
    req_path = r[0][1]
    # Simplify the case: lower the url
    p = urllib.parse.unquote_plus(req_path).lower()

    # Root service (app)
    r = re.search(r"^/([\w]+)/", p)
    useful_extracts['app'] = r.group(1) if r else ""
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
            r = re.search(r"geoserver/([\w]+)/(wms|wfs|ows|wcs)?", p)
            if r:
                ns = r.group(1)

            ogc_layer=""
            r = regex.findall(r"layer[s]?=([:\w]+)", p)
            if r:
                ogc_layer = r[0]

            if ogc_layer and ":" not in ogc_layer:
                ogc_layer = ns + ":" + ogc_layer
            if ogc_layer:
                useful_extracts['ogc_layer'] = ogc_layer

            ogc_format = ""
            r = regex.findall(r"format=([/\w]+)", p)
            if r:
                useful_extracts['ogc_format'] = r[0]

    return f'{" ".join(useful_extracts.values())}'


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
            logline = line
            useful_extracts = process(line)
            logline = logline + " " + useful_extracts
            logger.debug(logline)
            output.write(logline+"\n")

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
