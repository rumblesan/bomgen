 
import xml.etree.ElementTree as ET
import re


def read_bomfile(bom_path, custom_fields):
    tree = ET.parse(bom_path)
    root = tree.getroot()
    components = [read_component_elem(c, custom_fields) for c in root.find('components')]

cap_re = re.compile(r"(\d+)([pnu])(\d*)f$")
res_re = re.compile(r"(\d+)([kmr])(\d*)$")

def read_component_elem(component_elem, custom_fields):
    c = {}
    c['Ref'] = component_elem.attrib.get('ref').lower().strip()
    c['Value'] = ''
    value_elem = component_elem.find('./value')
    if value_elem:
        c['Value'] = value_elem.text.lower().strip()

    libsource = component_elem.find('./libsource')
    c['Library'] = libsource.attrib.get('lib').lower().strip()
    c['Part'] = libsource.attrib.get('part').lower().strip()
    c['Description'] = libsource.attrib.get('description').lower().strip()

    for field in component_elem.find('./fields'):
        if field.name in custom_fields:
            c[field.name] = field.value.lower().strip()
    return c
