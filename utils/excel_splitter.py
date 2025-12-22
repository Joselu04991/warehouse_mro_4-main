import re
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

from openpyxl import load_workbook

def _now_pe():
    return datetime.now(ZoneInfo("America/Lima"))

def _norm(s: str) -> str:
    s = "" if s is None else str(s)
    s = s.replace("\n", " ").replace("\r", " ")
    s = re.sub(r"\s+", " ", s).strip()
    s = s.replace('"', "").replace("“", "").replace("”", "")
    return s

def _norm_key(s: str) -> str:
    s = _norm(s).lower()
    s = s.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ñ", "n")
    s = re.sub(r"[^a-z0-9 ]+", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _find_header_row(ws, max_scan_rows=30):
    required = {
        "codigo del material",
        "texto breve de material",
        "ubicacion",
        "fisico",
    }
    for r in range(1, max_scan_rows + 1):
        row_vals = [ _norm_key(c.value) for c in ws[r] ]
        present = set([v for v in row_vals if v])
        if required.issubset(present):
            return r, row_vals
    return None, None

def _sheet_date_from_name(sheet_name: str):
    s = sheet_name.strip()
    for fmt in ("%d-%m-%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except:
            pass
    return None

def importar_excel_historico_a_db(
    archivo_excel,
    db,
    InventoryHistory,
    user_id: int,
    source_filename: str,
    anio: int = 2025,
    mes_inicio: int = 4,
    mes_fin: int = 12,
    chunk_size: int = 5000,
):
    """
    Lee un Excel pesado con MUCHAS hojas (cada hoja = día) y guarda a InventoryHistory
    por lotes para no reventar memoria.

    Retorna: (snapshot_id, snapshot_name, total_rows)
    """
    archivo_excel = Path(str(archivo_excel))

    wb = load_workbook(filename=str(archivo_excel), read_only=True, data_only=True)

    snapshot_id = str(uuid.uuid4())
    snapshot_name = f"Inventario Antiguo { _now_pe():%d/%m/%Y %H:%M }"
    total_inserted = 0

    for sheet in wb.sheetnames:
        fecha = _sheet_date_from_name(sheet)
        if not fecha:
            continue
        if fecha.year != anio:
            continue
        if not (mes_inicio <= fecha.month <= mes_fin):
            continue

        ws = wb[sheet]
        header_row, header_keys = _find_header_row(ws)
        if not header_row:
            continue

        col_map = {}
        for idx, key in enumerate(header_keys, start=1):
            if not key:
                continue
            col_map[key] = idx

        def col_of(name_norm):
            return col_map.get(name_norm)

        c_codigo = col_of("codigo del material")
        c_texto  = col_of("texto breve de material")
        c_unidad = col_of("unidad medida") or col_of("unidad medid") or col_of("unidad de medida")
        c_ubi    = col_of("ubicacion")
        c_fisico = col_of("fisico")
        c_stock  = col_of("stock")
        c_dif    = col_of("difere") or col_of("difer") or col_of("diferencia")
        c_obs    = col_of("observac") or col_of("observac.")

        if not all([c_codigo, c_texto, c_ubi, c_fisico]):
            continue

        batch = []
        for row in ws.iter_rows(min_row=header_row + 1, values_only=True):
            codigo = _norm(row[c_codigo - 1] if c_codigo else "")
            if not codigo:
                continue

            texto = _norm(row[c_texto - 1] if c_texto else "")
            unidad = _norm(row[c_unidad - 1] if c_unidad else "")
            ubicacion = _norm(row[c_ubi - 1] if c_ubi else "").replace(" ", "").upper()

            fisico_raw = row[c_fisico - 1] if c_fisico else 0
            try:
                fisico = float(fisico_raw) if fisico_raw is not None else 0.0
            except:
                fisico = 0.0

            stock_raw = row[c_stock - 1] if c_stock else None
            dif_raw   = row[c_dif - 1] if c_dif else None
            obs_raw   = row[c_obs - 1] if c_obs else None

            try:
                stock = float(stock_raw) if stock_raw is not None else None
            except:
                stock = None

            try:
                dif = float(dif_raw) if dif_raw is not None else None
            except:
                dif = None

            obs = _norm(obs_raw) if obs_raw is not None else None

            batch.append({
                "user_id": user_id,
                "snapshot_id": snapshot_id,
                "snapshot_name": snapshot_name,
                "material_code": codigo,
                "material_text": texto,
                "base_unit": unidad if unidad else "N/A",
                "location": ubicacion if ubicacion else "N/A",
                "libre_utilizacion": fisico,   # FISICO = conteo real histórico
                "creado_en": datetime(fecha.year, fecha.month, fecha.day, 0, 0, 0, tzinfo=ZoneInfo("America/Lima")),
                "source_type": "HISTORICO",
                "source_filename": source_filename,
                # campos extra opcionales (si los agregas al modelo)
                # "stock_sistema": stock,
                # "difere": dif,
                # "observacion": obs,
            })

            if len(batch) >= chunk_size:
                db.session.bulk_insert_mappings(InventoryHistory, batch)
                db.session.commit()
                total_inserted += len(batch)
                batch.clear()

        if batch:
            db.session.bulk_insert_mappings(InventoryHistory, batch)
            db.session.commit()
            total_inserted += len(batch)
            batch.clear()

    return snapshot_id, snapshot_name, total_inserted
