#!/usr/bin/env python

import sqlite3


class ComponentDirectory(object):

    def __init__(self):
        self.con = sqlite3.connect('dbs/components.db')
        self.con.row_factory = sqlite3.Row
        self.cur = self.con.cursor()
        self.attribute_names = ['partnumber', 'parttype', 'value', 'footprint',
                                'tolerance', 'power_rating', 'voltage', 'spec']
        self.column_names = [c.replace(" ", "_") for c in self.attribute_names]
        self.supplier_names = ['mouser', 'farnell', 'other']

    def __del__(self):
        self.con.close()

    def setup(self):
        self.cur.execute('''CREATE TABLE IF NOT EXISTS components (
                         partnumber TEXT PRIMARY KEY NOT NULL,
                         parttype TEXT NOT NULL,
                         footprint TEXT,
                         value TEXT,
                         tolerance TEXT,
                         power_rating TEXT,
                         voltage TEXT,
                         spec TEXT
                         )''')
        self.cur.execute('''CREATE TABLE IF NOT EXISTS order_numbers (
                         partnumber TEXT NOT NULL,
                         mouser TEXT,
                         farnell TEXT,
                         other TEXT,
                         PRIMARY KEY (partnumber)
                         )''')
        self.con.commit()

    def cleanup(self):
        self.cur.execute('DROP TABLE IF EXISTS components')
        self.cur.execute('DROP TABLE IF EXISTS order_numbers')
        self.con.commit()

    def add_component(self,
                      partnumber=None,
                      parttype=None,
                      footprint=None,
                      value=None,
                      tolerance=None,
                      power_rating=None,
                      voltage=None,
                      spec=None):

        self.cur.execute('''INSERT OR REPLACE INTO components
                             values (?, ?, ?, ?, ?, ?, ?, ?)''',
                         (partnumber,
                          parttype,
                          footprint,
                          value,
                          tolerance,
                          power_rating,
                          voltage,
                          spec))
        self.con.commit()

    def add_order_numbers(self, partnumber, supplier_order_numbers):
        args = {'partnumber': partnumber}

        for supplier in self.supplier_names:
            args[supplier] = supplier_order_numbers.get(supplier)

        self.cur.execute('''INSERT OR REPLACE INTO order_numbers VALUES
                            (:partnumber, :mouser, :farnell, :other)
                         ''',
                         args)
        self.con.commit()

    def find_component(self,
                       parttype,
                       value,
                       tolerance=None,
                       power_rating=None,
                       voltage=None,
                       spec=None):
        args = {
            'value': value,
        }
        opt_args = {
            'parttype': parttype,
            'tolerance': tolerance,
            'power_rating': power_rating,
            'voltage': voltage,
            'spec': spec
        }
        qry = '''SELECT * FROM components AS c
                 JOIN order_numbers AS o
                 WHERE value=:value
                 AND c.partnumber = o.partnumber'''

        for name in opt_args:
            v = opt_args.get(name, None)
            if v and v != '':
                args[name] = v
                qry += ' AND ({col} = :{col} OR {col} is NULL)'.format(
                    col=name
                )

        return [self.row_to_dict(row) for row in self.cur.execute(qry, args)]

    def find_component_by_partnumber(self, partnumber):
        qry = '''SELECT * FROM components AS c
                 JOIN order_numbers AS o
                 WHERE c.partnumber=:partnumber
                 AND c.partnumber = o.partnumber'''

        args = {'partnumber': partnumber}

        return [self.row_to_dict(row) for row in self.cur.execute(qry, args)]

    def get_order_number(self, partnumber):
        qry = 'SELECT * FROM order_numbers WHERE partnumber = ?'
        return [{
            'partnumber': row['partnumber'],
            'supplier': row['supplier'],
            'order_number': row['order_number'],
        } for row in self.cur.execute(qry, partnumber)]

    def load_csv_row(self, row):
        values = {}
        partnumber = ''
        for attr in self.attribute_names:
            key = attr.replace(" ", "_")
            v = row.get(attr)
            if v:
                v = v.strip().lower()
            values[key] = v
        if values.get('partnumber', '') == '':
            print("skipping component without number", values)
            return
        else:
            self.add_component(**values)
            partnumber = values['partnumber']

        order_numbers = {}
        for supplier in self.supplier_names:
            order_number = row.get(supplier)
            order_numbers[supplier] = order_number
        self.add_order_numbers(partnumber, order_numbers)

    def row_to_dict(self, row):
        d = {}
        for name in self.column_names:
            d[name] = row[name]
        for name in self.supplier_names:
            d[name] = row[name]
        return d
