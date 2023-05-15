#!/usr/bin/env python

import argparse
import csv
import re
import codecs
import urllib.request
from configparser import ConfigParser

from pathlib import Path
from os.path import isfile

from componentdirectory import ComponentDirectory
from bom import BOM

config_file = 'config.ini'


def read_input_bom(bom_path):
    components = []
    if not isfile(bom_path):
        print("Could not find BOM file %s" % bom_path)
        return components
    with open(bom_path) as csvfile:
        bom_reader = csv.DictReader(csvfile, skipinitialspace=True)
        components = [p for p in bom_reader]
    return components



def value_to_sortable(comp_type, value):
    m = None
    if comp_type == 'capacitor':
        m = cap_re.match(value)
        if not m:
            return 0
    elif comp_type == 'resistor'\
            or comp_type == 'potentiometer'\
            or comp_type == 'trimpot':
        m = res_re.match(value)
        if not m:
            return 0
    else:
        return 0
    num = float("%s.%s" % (m.group(1), m.group(3)))
    return num * get_mult(m.group(2))


def get_mult(mult):
    if mult == "p":
        return 1
    elif mult == "n" or mult == "k":
        return 1000
    elif mult == "u" or mult == "m":
        return 1000000
    else:
        return 0


def sort_bom(final_bom):
    final_bom.sort(reverse=True, key=lambda p: p["quantity"])
    final_bom.sort(key=lambda p: value_to_sortable(p["parttype"], p["value"]))
    final_bom.sort(key=lambda p: p["parttype"])


def write_bom_csv(outputfile, final_bom):
    with open(outputfile, "w") as csvfile:
        fieldnames = ["parttype", "value", "spec",
                      "quantity", "info", "order code", "part number",
                      "mouser", "farnell", "other"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for line in final_bom:
            writer.writerow(line)
    print("Finished")


def combine_boms(input_boms, directory):
    final_bom = BOM(directory)
    for bom in input_boms:
        for entry in bom:
            final_bom.add_entry(entry)
    return final_bom.get_output()


def update_parts_db(urls):
    db = ComponentDirectory()
    db.cleanup()
    db.setup()
    for url in urls:
        print("Getting data from {}".format(url))
        component_data = codecs.iterdecode(
            urllib.request.urlopen(url), 'utf-8')
        for row in csv.DictReader(component_data, skipinitialspace=True):
            db.load_csv_row(row)
    del(db)


if __name__ == '__main__':
    config = ConfigParser()
    config.read(config_file)
    urls = config['ComponentURLs']
    component_urls = [urls[key] for key in urls.keys()]

    parser = argparse.ArgumentParser(
        description='put together an order from BOMs')
    parser.add_argument(
        'cmd', choices=['gen', 'update'], help='command to run')
    parser.add_argument('-b', '--boms', nargs='*',
                        dest='boms', help='BOM files to parse')
    parser.add_argument('-o', '--out', dest='outputfile', nargs='?',
                        help='output file', default='bom.csv')
    args = parser.parse_args()

    c = ComponentDirectory()

    if args.cmd == 'gen':
        output_file = Path(args.outputfile).with_suffix('.csv')
        input_boms = []
        for bp in args.boms:
            input_boms.append(read_input_bom(bp))
            print(bp)
        final_bom = combine_boms(input_boms, c)
        sort_bom(final_bom)
        write_bom_csv(output_file, final_bom)
    elif args.cmd == 'update':
        update_parts_db(component_urls)
