import re

class BOM:

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
        "switch": re.compile(r"sw_.*"),
        "connector": re.compile(r"conn_.*"),
        "socket": re.compile(r"bananasocket_.*"),
    }

    columns = ['Part', 'Value', 'Tolerance', 'Voltage', 'Spec', 'PartNumber', 'Quantity Per PCB']

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
        return None

    def tidy_value(self, v):
        if v:
            return v.strip().lower()

    def tidy_int(self, i):
        if i:
            return int(i.strip())
        else:
            return 0

    def add_entry(self, entry):
        part = self.tidy_value(entry.get(self.columns[0]))
        parttype = self.part_to_type(part)
        value = self.tidy_value(entry.get(self.columns[1]))
        tolerance = self.tidy_value(entry.get(self.columns[2]))
        voltage = self.tidy_value(entry.get(self.columns[3]))
        spec = self.tidy_value(entry.get(self.columns[4]))
        partnumber = self.tidy_value(entry.get(self.columns[5]))
        quantity = self.tidy_value(entry.get(self.columns[6]))

        args = {
            'parttype': parttype,
            'value': value,
            'tolerance': tolerance,
            # 'voltage': voltage,
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
                "parttype": component.get('parttype', ''),
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
