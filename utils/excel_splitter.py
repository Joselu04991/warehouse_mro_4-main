from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from openpyxl import load_workbook, Workbook


@dataclass
class DailyExport:
    sheet_name: str
    fecha: datetime
    output_path: Path
    rows: int


def _norm(s: str) -> str:
    s = (s or "").strip()
    s = s.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    s = re.sub(r"\s+", " ", s)
    s = s.strip().lower()
    s = s.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ñ", "n")
    s = s.replace('"', "").replace("'", "")
    return s


def _parse_sheet_date(sheet_name: str) -> Optional[datetime]:
    name = sheet_name.strip()
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(name, fmt)
        except Exception:
            pass
    return None


def _find_header_row(ws, max_scan_rows: int = 30) -> Optional[int]:
    needed_tokens = {
        "codigo del material", "texto breve de material", "ubicacion",
        "unidad medida", "fisico", "stock", "difere", "observac"
    }
    for r in range(1, max_scan_rows + 1):
        values = [ws.cell(row=r, column=c).value for c in range(1, min(ws.max_column, 30) + 1)]
        normed = {_norm(str(v)) for v in values if v is not None}
        hits = 0
        for t in needed_tokens:
            if any(t in x for x in normed):
                hits += 1
        if hits >= 4:
            return r
    return None


def _map_columns(header_values: List[str]) -> Dict[str, int]:
    idx = {}
    for i, val in enumerate(header_values):
        idx[_norm(str(val))] = i

    def pick(*cands: str) -> Optional[int]:
        for cand in cands:
            for key, pos in idx.items():
                if cand in key:
                    return pos
        return None

    colmap = {
        "Item": pick("item"),
        "Código del Material": pick("codigo del material", "codigo material", "material"),
        "Texto breve de material": pick("texto breve de material", "texto breve", "descripcion", "texto"),
        "Unidad Medida": pick("unidad medida", "unidad medid", "unidad", "u.m", "um"),
        "Ubicación": pick("ubicacion", "ubicacion sap", "ubic"),
        "Fisico": pick("fisico"),
        "STOCK": pick("stock"),
        "Difere": pick("difere", "difer"),
        "Observac.": pick("observac", "observacion"),
    }

    missing = [k for k, v in colmap.items() if v is None]
    if missing:
        raise Exception(f"❌ No pude mapear estas columnas: {missing}. Encabezados detectados: {list(idx.keys())[:25]}")

    return {k: int(v) for k, v in colmap.items()}  # type: ignore[arg-type]


def dividir_excel_por_dias(
    archivo_excel: str | Path,
    salida_base: str | Path = "inventarios_procesados",
    anio: int = 2025,
    mes_inicio: int = 4,
    mes_fin: int = 12,
) -> List[DailyExport]:
    archivo_excel = Path(archivo_excel)
    salida_base = Path(salida_base)
    salida_base.mkdir(parents=True, exist_ok=True)

    wb = load_workbook(archivo_excel, read_only=True, data_only=True)

    exports: List[DailyExport] = []

    for sheet in wb.sheetnames:
        fecha = _parse_sheet_date(sheet)
        if not fecha:
            continue

        if fecha.year != anio or not (mes_inicio <= fecha.month <= mes_fin):
            continue

        ws = wb[sheet]
        header_row = _find_header_row(ws)
        if not header_row:
            continue

        header_values = []
        max_col = min(ws.max_column, 60)
        for c in range(1, max_col + 1):
            header_values.append(ws.cell(row=header_row, column=c).value)

        col = _map_columns(header_values)

        out_dir = salida_base / f"{fecha.year:04d}" / f"{fecha.month:02d}"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"inventario_{fecha:%Y_%m_%d}.xlsx"

        out_wb = Workbook(write_only=True)
        out_ws = out_wb.create_sheet("DATA")

        output_headers = ["Item", "Código del Material", "Texto breve de material", "Unidad Medida", "Ubicación", "Fisico", "STOCK", "Difere", "Observac."]
        out_ws.append(output_headers)

        rows_written = 0
        start_row = header_row + 1

        for r in ws.iter_rows(min_row=start_row, values_only=True):
            if r is None:
                continue

            code = r[col["Código del Material"]] if col["Código del Material"] < len(r) else None
            text = r[col["Texto breve de material"]] if col["Texto breve de material"] < len(r) else None
            if code is None and text is None:
                continue

            item = r[col["Item"]] if col["Item"] < len(r) else None
            unidad = r[col["Unidad Medida"]] if col["Unidad Medida"] < len(r) else None
            ubic = r[col["Ubicación"]] if col["Ubicación"] < len(r) else None
            fis = r[col["Fisico"]] if col["Fisico"] < len(r) else None
            stock = r[col["STOCK"]] if col["STOCK"] < len(r) else None
            dif = r[col["Difere"]] if col["Difere"] < len(r) else None
            obs = r[col["Observac."]] if col["Observac."] < len(r) else None

            def s(x):
                if x is None:
                    return ""
                return str(x).strip()

            def ub(x):
                return s(x).replace(" ", "").upper()

            out_ws.append([
                s(item),
                s(code),
                s(text),
                s(unidad),
                ub(ubic),
                s(fis),
                s(stock),
                s(dif),
                s(obs),
            ])
            rows_written += 1

        out_wb.save(out_path)
        exports.append(DailyExport(sheet, fecha, out_path, rows_written))

    return exports
