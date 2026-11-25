import json, zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import TestCase

class WorkbookInspection(TestCase):
    def test_dump_workbook_layout_for_diagnostic(self):
        path = Path("data/Formula_Imperial_Worldwide_Series.xlsx")
        ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
              "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
        with zipfile.ZipFile(path) as z:
            shared = []
            if "xl/sharedStrings.xml" in z.namelist():
                root = ET.fromstring(z.read("xl/sharedStrings.xml"))
                shared = ["".join(t.text or "" for t in si.findall(".//m:t", ns)) for si in root.findall("m:si", ns)]
            wb = ET.fromstring(z.read("xl/workbook.xml"))
            rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
            relmap = {x.attrib["Id"]: x.attrib["Target"] for x in rels}
            output = []
            for sh in wb.findall(".//m:sheets/m:sheet", ns):
                target = relmap[sh.attrib["{"+ns["r"]+"}id"]].lstrip("/")
                if not target.startswith("xl/"): target = "xl/"+target
                root = ET.fromstring(z.read(target))
                rows = []
                for row in root.findall(".//m:sheetData/m:row", ns):
                    rn = int(row.attrib["r"])
                    if rn > 18: continue
                    cells = []
                    for c in row.findall("m:c", ns):
                        v = c.find("m:v", ns)
                        val = v.text if v is not None else ""
                        if c.attrib.get("t") == "s" and val: val = shared[int(val)]
                        elif c.attrib.get("t") == "inlineStr":
                            val = "".join(t.text or "" for t in c.findall(".//m:t", ns))
                        if val != "": cells.append(c.attrib["r"]+"="+str(val))
                    if cells: rows.append({"row": rn, "cells": cells})
                output.append({"sheet":sh.attrib["name"],"rows":rows})
        self.fail(json.dumps(output, ensure_ascii=False))
