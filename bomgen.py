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


switch_re = re.compile(r"sw_.*")
connector_re = re.compile(r"conn_.*")
bananajack_re = re.compile(r"bananasocket_.*")

parttypes = {
    "c": "capacitor",
    "c_polarized": "capacitor",
    "d": "diode",
    "d_schottky": "diode",
    "r": "resistor",
    "r_potentiometer": "potentiometer",
    "r_potentiometer_trim": "trimmer",
}

parttype_res = {
    "switch": switch_re,
    "connector": connector_re,
    "socket": bananajack_re,
}


def part_to_type(part):
    if part in parttypes:
        return parttypes.get(part)
    for t in parttype_res.keys():
        re = parttype_res.get(t)
        if re.match(part):
            return t
    return None


cap_re = re.compile(r"(\d+)([pnu])(\d*)f$")
res_re = re.compile(r"(\d+)([kmr])(\d*)$")


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


def tidy_value(v):
    if v:
        return v.strip().lower()


def tidy_int(i):
    if i:
        return int(i.strip())
    else:
        return 0


def combine_boms(input_boms, directory):
    final_bom = {}
    for bom in input_boms:
        for entry in bom:
            part = tidy_value(entry.get("Part"))
            parttype = part_to_type(part)
            value = tidy_value(entry.get("Value"))
            tolerance = tidy_value(entry.get("Tolerance"))
            # voltage = tidy_value(entry.get("Voltage"))
            spec = tidy_value(entry.get("Spec"))
            partnumber = tidy_value(entry.get("PartNumber"))
            quantity = tidy_int(entry.get("Quantity Per PCB"))
            args = {
                'parttype': parttype,
                'value': value,
                'tolerance': tolerance,
                # 'voltage': voltage,
                'spec': spec,
            }
            if partnumber:
                components = directory.find_component_by_partnumber(partnumber)
            else:
                components = directory.find_component(**args)

            component = {}
            if len(components) < 1:
                print("no components found", args)
                print(args)
                partnumber = 'no part number'
            elif len(components) > 1:
                print("multiple components found")
                print(args)
                for c in components:
                    print(c)
                partnumber = 'no components number'
            else:
                component = components[0]
                partnumber = component.get('partnumber', 'no part number')

            key = "{parttype}{value}{tolerance}{spec}".format(**args)

            if key in final_bom:
                final_bom[key]["quantity"] += quantity
            else:
                final_bom[key] = {
                    "parttype": component.get('parttype', ''),
                    "value": component.get('value', value),
                    "spec": component.get('spec', spec),
                    "part number": partnumber,
                    "quantity": quantity,
                    "mouser": component.get('mouser'),
                    "farnell": component.get('farnell'),
                    "other": component.get('other'),
                }
    return list(final_bom.values())


if __name__ == '__main__':
    config = ConfigParser()
    config.read(config_file)
    component_data_url = config['components']['data_url']

    parser = argparse.ArgumentParser(description='price up kicad BOM')
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
        print("Getting data from {}".format(component_data_url))
        component_data = codecs.iterdecode(
            urllib.request.urlopen(component_data_url), 'utf-8')
        print(component_data)
        c = ComponentDirectory()
        c.cleanup()
        c.setup()
        for row in csv.DictReader(component_data, skipinitialspace=True):
            c.load_csv_row(row)
        del(c)
