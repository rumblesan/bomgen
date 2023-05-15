import re

class BOM:

    parttypes = {
        "c": "capacitor",
        "c_polarized": "capacitor",
        "d": "diode",
        "d_schottky": "diode",
        "d_zener": "diode",
        "r": "resistor",
        "r_potentiometer": "potentiometer",
        "r_potentiometer_trim": "trimmer",
    }

    parttype_res = {
        "transistor": re.compile(r".*transistor.*"),
        "switch": re.compile(r"sw_.*"),
        "connector": re.compile(r"conn_.*"),
        "socket": re.compile(r"bananasocket_.*"),
        "socket": re.compile(r".*mono jack.*"),
        "connector": re.compile(r"eurorack power.*"),
        "connector": re.compile(r"conn_\d+x\d+.*"),
    }

    columns = {
        'Part': ['Part'],
        'Value': ['Value'],
        'Tolerance': ['Tolerance'],
        'Voltage': ['Voltage'],
        'Spec': ['Spec'],
        'FootprintType': ['FootprintType'],
        'PartNumber': ['PartNumber'],
        'Quantity': ['Quantity', 'Quantity Per PCB']
    }

    def __init__(self, db):
        self.components = {}
        self.db = db

    def part_to_type(self, part):
        if part in self.parttypes:
            return self.parttypes.get(part)
        for t in self.parttype_res.keys():
            re = self.parttype_res.get(t)
            if re.match(part):
                return t
        print(part)
        return part

    def tidy_value(self, v):
        if v:
            return v.strip().lower()

    def tidy_int(self, i):
        if i:
            return int(i.strip())
        else:
            return 0

    def get_entry_value(self, entry, keys, default=None):
        for k in keys:
            v = entry.get(k)
            if v:
                return self.tidy_value(v)
        return default

    def add_entry(self, entry):
        part = self.get_entry_value(entry, self.columns['Part'])
        parttype = self.part_to_type(part)
        value = self.get_entry_value(entry, self.columns['Value'])
        tolerance = self.get_entry_value(entry, self.columns['Tolerance'])
        voltage = self.get_entry_value(entry, self.columns['Voltage'])
        spec = self.get_entry_value(entry, self.columns['Spec'])
        footprint_type = self.get_entry_value(entry, self.columns['FootprintType'], 'tht')
        partnumber = self.get_entry_value(entry, self.columns['PartNumber'])
        quantity = int(self.get_entry_value(entry, self.columns['Quantity']))

        args = {
            'parttype': parttype,
            'value': value,
            'tolerance': tolerance,
            # 'voltage': voltage,
            'footprint_type': footprint_type,
            'spec': spec,
        }
        if partnumber:
            components = self.db.find_component_by_partnumber(partnumber)
        else:
            components = self.db.find_component(**args)

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

        if key in self.components:
            self.components[key]["quantity"] += quantity
        else:
            self.components[key] = {
                "parttype": component.get('parttype', parttype),
                "value": component.get('value', value),
                "spec": component.get('spec', spec),
                "part number": partnumber,
                "quantity": quantity,
                "mouser": component.get('mouser'),
                "farnell": component.get('farnell'),
                "other": component.get('other'),
            }

    def get_output(self):
        return list(self.components.values())
