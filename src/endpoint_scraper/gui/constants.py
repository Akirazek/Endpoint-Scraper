"""Category colors, icons, and CSV helpers."""

import os
import csv
import qtawesome as qta

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "output", "endpoints.csv")

CATEGORY_COLORS = {
    "content":           "#4fc3f7",
    "page":              "#81c784",
    "search":            "#ffb74d",
    "user":              "#ce93d8",
    "url-pattern":       "#90a4ae",
    "subdomain":         "#f06292",
    "external":          "#fff176",
    "robots-disallowed": "#ef5350",
    "api":               "#ff8a65",
    "auth":              "#aed581",
    "admin":             "#ba68c8",
    "api-network":       "#4dd0e1",
    "js-route":          "#fff176",
    "exposed-secret":    "#ef5350",
    "query-param":       "#90a4ae",
}

CATEGORY_PHOSPHOR = {
    "content":           "ph.file-text",
    "page":              "ph.file",
    "search":            "ph.magnifying-glass",
    "user":              "ph.user-circle",
    "url-pattern":       "ph.link",
    "subdomain":         "ph.globe",
    "external":          "ph.arrow-square-out",
    "robots-disallowed": "ph.prohibit",
    "api":               "ph.code",
    "auth":              "ph.lock",
    "admin":             "ph.shield",
    "api-network":       "ph.network",
    "js-route":          "ph.file-js",
    "exposed-secret":    "ph.warning",
    "query-param":       "ph.question",
}


def cat_icon(cat, color=None):
    name = CATEGORY_PHOSPHOR.get(cat, "ph.file")
    c = color or CATEGORY_COLORS.get(cat, "#cdd6f4")
    return qta.icon(name, color=c)


def load_csv(path):
    rows = []
    if not os.path.exists(path):
        return rows
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        next(reader, None)
        for r in reader:
            if len(r) >= 2:
                rows.append({"category": r[0].strip(), "value": r[1].strip()})
    return rows
