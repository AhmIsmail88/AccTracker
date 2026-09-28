# -*- coding: utf-8 -*-
"""xlsx_min.py — Minimal XLSX reader/writer for ProTrack (stdlib only).

الهدف: قراءة/كتابة ملفات xlsx بسيطة (شيتات + صفوف + خلايا نصية/رقمية)
بدون أي اعتماديات خارجية، لاستخدامها في أدوات العقد (Phase 0).
ملاحظة: هذا ليس بديلاً كاملاً عن openpyxl — يكفي لعقد visit.xlsx.
"""
import io
import re
import zipfile
import xml.etree.ElementTree as ET

_MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


def _local(tag):
    return tag.rsplit("}", 1)[-1]


def _col_letter(idx):
    s = ""
    idx += 1
    while idx:
        idx, r = divmod(idx - 1, 26)
        s = chr(65 + r) + s
    return s


def _col_index(letters):
    v = 0
    for ch in letters:
        v = v * 26 + (ord(ch.upper()) - 64)
    return v - 1


def _xml_escape(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _xml_escape_attr(text):
    return _xml_escape(text).replace('"', "&quot;")


def _sheet_xml(rows):
    parts = ['<?xml version="1.0" encoding="UTF-8" standalone="yes"?>']
    parts.append('<worksheet xmlns="%s"><sheetData>' % _MAIN_NS)
    for r_i, row in enumerate(rows, start=1):
        cells = []
        for c_i, val in enumerate(row):
            if val is None or val == "":
                continue
            ref = "%s%d" % (_col_letter(c_i), r_i)
            if isinstance(val, bool):
                val = int(val)
            if isinstance(val, (int, float)):
                cells.append('<c r="%s"><v>%s</v></c>' % (ref, val))
            else:
                cells.append(
                    '<c r="%s" t="inlineStr"><is><t xml:space="preserve">%s</t></is></c>'
                    % (ref, _xml_escape(str(val)))
                )
        parts.append('<row r="%d">%s</row>' % (r_i, "".join(cells)))
    parts.append("</sheetData></worksheet>")
    return "".join(parts)


def write_workbook_bytes(sheets):
    """sheets: iterable of (name, rows) or dict. Returns xlsx bytes."""
    items = list(sheets.items()) if hasattr(sheets, "items") else list(sheets)
    ct_overrides = "".join(
        '<Override PartName="/xl/worksheets/sheet%d.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        % (i + 1)
        for i in range(len(items))
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        + ct_overrides
        + "</Types>"
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="%s">'
        '<Relationship Id="rId1" Type="%s/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>" % (_PKG_REL_NS, _REL_NS)
    )
    sheets_xml = "".join(
        '<sheet name="%s" sheetId="%d" r:id="rId%d"/>' % (_xml_escape_attr(name), i + 1, i + 1)
        for i, (name, _) in enumerate(items)
    )
    workbook = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="%s" xmlns:r="%s"><sheets>%s</sheets></workbook>'
        % (_MAIN_NS, _REL_NS, sheets_xml)
    )
    wb_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="%s">%s</Relationships>'
        % (
            _PKG_REL_NS,
            "".join(
                '<Relationship Id="rId%d" Type="%s/worksheet" Target="worksheets/sheet%d.xml"/>'
                % (i + 1, _REL_NS, i + 1)
                for i in range(len(items))
            ),
        )
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", content_types.encode("utf-8"))
        z.writestr("_rels/.rels", root_rels.encode("utf-8"))
        z.writestr("xl/workbook.xml", workbook.encode("utf-8"))
        z.writestr("xl/_rels/workbook.xml.rels", wb_rels.encode("utf-8"))
        for i, (_, rows) in enumerate(items):
            z.writestr("xl/worksheets/sheet%d.xml" % (i + 1), _sheet_xml(rows).encode("utf-8"))
    return buf.getvalue()


def write_workbook(path, sheets):
    with open(path, "wb") as f:
        f.write(write_workbook_bytes(sheets))


def _child_text(c, tag):
    for child in c:
        if _local(child.tag) == tag:
            return child.text
    return None


def _cell_value(c, shared):
    t = c.attrib.get("t", "")
    if t == "inlineStr":
        is_el = None
        for child in c:
            if _local(child.tag) == "is":
                is_el = child
                break
        if is_el is None:
            return None
        return "".join(x.text or "" for x in is_el.iter() if _local(x.tag) == "t")
    if t == "s":
        v = _child_text(c, "v")
        if v is None:
            return None
        try:
            return shared[int(v)]
        except (ValueError, IndexError):
            return None
    if t == "str":
        return _child_text(c, "v") or ""
    if t == "b":
        return _child_text(c, "v") == "1"
    v = _child_text(c, "v")
    if v is None or v == "":
        return None
    try:
        f = float(v)
    except ValueError:
        return v.strip()
    if f.is_integer() and "." not in v and "e" not in v.lower():
        return int(f)
    return f


def _parse_sheet(data, shared):
    root = ET.fromstring(data)
    rows = []
    for row_el in root.iter():
        if _local(row_el.tag) != "row":
            continue
        try:
            row_idx = int(row_el.attrib.get("r", str(len(rows) + 1)))
        except ValueError:
            row_idx = len(rows) + 1
        cells = {}
        auto_col = 0
        for c in row_el:
            if _local(c.tag) != "c":
                continue
            ref = c.attrib.get("r", "")
            m = re.match(r"([A-Za-z]+)", ref)
            if m:
                c_idx = _col_index(m.group(1))
            else:
                c_idx = auto_col
            cells[c_idx] = _cell_value(c, shared)
            auto_col = c_idx + 1
        if cells:
            width = max(cells) + 1
            row = [None] * width
            for i, v in cells.items():
                row[i] = v
            rows.append((row_idx, row))
    rows.sort(key=lambda x: x[0])
    out = []
    last = 0
    for idx, row in rows:
        while last + 1 < idx:
            out.append([])
            last += 1
        out.append(row)
        last = idx
    return out


def read_workbook(path_or_bytes):
    """Returns dict: sheet name -> list of rows. Each row = list of cell values."""
    if isinstance(path_or_bytes, (bytes, bytearray)):
        zf = zipfile.ZipFile(io.BytesIO(path_or_bytes))
    else:
        zf = zipfile.ZipFile(path_or_bytes)
    with zf:
        names = set(zf.namelist())
        shared = []
        if "xl/sharedStrings.xml" in names:
            sroot = ET.fromstring(zf.read("xl/sharedStrings.xml"))
            for si in sroot.iter():
                if _local(si.tag) == "si":
                    shared.append("".join(t.text or "" for t in si.iter() if _local(t.tag) == "t"))
        wb = ET.fromstring(zf.read("xl/workbook.xml"))
        rels = {}
        if "xl/_rels/workbook.xml.rels" in names:
            rroot = ET.fromstring(zf.read("xl/_rels/workbook.xml.rels"))
            for rel in rroot.iter():
                if _local(rel.tag) == "Relationship":
                    rels[rel.attrib.get("Id")] = rel.attrib.get("Target", "")
        result = {}
        for sheet in wb.iter():
            if _local(sheet.tag) != "sheet":
                continue
            name = sheet.attrib.get("name", "Sheet")
            rid = None
            for k, v in sheet.attrib.items():
                if _local(k) == "id":
                    rid = v
            target = rels.get(rid, "")
            target = target.lstrip("/")
            if not target.startswith("xl/"):
                target = "xl/" + target
            if target not in names:
                result[name] = []
                continue
            result[name] = _parse_sheet(zf.read(target), shared)
        return result
