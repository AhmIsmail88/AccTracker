# -*- coding: utf-8 -*-
"""أدوات تحويل صفوف الشيتات إلى قواميس (أول صف = عناوين)."""


def sheet_dicts(rows):
    if not rows:
        return []
    headers = [("" if h is None else str(h).strip()) for h in rows[0]]
    out = []
    for r in rows[1:]:
        if not any(v is not None and str(v).strip() != "" for v in r):
            continue
        d = {}
        for i, h in enumerate(headers):
            if not h:
                continue
            d[h] = r[i] if i < len(r) else None
        out.append(d)
    return out
