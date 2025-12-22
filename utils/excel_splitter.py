# utils/excel_splitter.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re
import pandas as pd


@dataclass
class SplitResult:
    total_sheets: int
    processed: int
    skipped: int
    outputs: list[str]


def _norm(s: str) -> str:
    s = str(s) if s is not None else ""
    s = s.replace("\n", " ").replace("\r", " ")
    s = s.replace('"', "").replace("“", "").replace("”", "")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _build_column_map(df_cols: list[str]) -> dict[str, str]:
    """
    Devuelve un mapping {col_real_en_excel: col_canonica} para estas columnas:
    Item, Código del Material, Texto breve de material, Unidad Medida, Ubicación,
    Fisico, STOCK, Difere, Observac.
    """
    canon_targets = {
        "Item": ["item", "it", "n", "nro", "numero", "ítem"],
        "Código del Material": ["codigo del material", "código del material", "codigo material", "código material", "material", "cod material", "codigo"],
        "Texto breve de material": ["texto breve de material", "descripcion", "descripción", "texto", "material text"],
        "Unidad Medida": ["unidad medida", "unidad medid", "unidad", "um", "u.m", "unidad de medida", "unidad de medida base"],
        "Ubicación": ["ubicación", "ubicacion", "location", "ubi"],
        "Fisico": ["fisico", "físico", "conteo", "contado", "stock contado", "real", "conteo real"],
        "STOCK": ["stock", "stock sistema", "sistema"],
        "Difere": ["difere", "difer", "diferencia", "diff"],
        "Observac.": ["observac.", "observac", "observacion", "observación", "obs", "comentario", "comentarios"],
    }

    # índice por versión normalizada
    norm_to_real = {}
    for c in df_cols:
        norm_to_real[_norm(c).lower()] = c

    mapping = {}
    used_real = set()

    for canon, aliases in canon_targets.items():
        found_real = None

        # match directo
        for norm_real, real in norm_to_real.items():
            if norm_real == _norm(canon).lower():
                found_real = real
                break

        # match por alias
        if not found_real:
            for a in aliases:
                a_norm = _norm(a).lower()
                for norm_real, real in norm_to_real.items():
                    if norm_real == a_norm:
                        found_real = real
                        break
                if found_real:
                    break

        # match “contiene”
        if not found_real:
            canon_norm = _norm(canon).lower()
            for norm_real, real in norm_to_real.items():
                if canon_norm in norm_real:
                    found_real = real
                    break

        if found_real and found_real not in used_real:
            mapping[found_real] = canon
            used_real.add(found_real)

    return mapping


def dividir_excel_por_dias(
    archivo_excel: str | Path,
    salida_base: str | Path = "inventarios_procesados",
    anio: int = 2025,
    mes_inicio: int = 4,
    mes_fin: int = 12,
) -> SplitResult:
    """
    Divide un Excel con varias hojas (cada hoja = día) a Excels diarios.
    Requiere hojas con nombre tipo: '10-04-2025'.

    Mantiene estas columnas (todas necesarias):
    Item, Código del Material, Texto breve de material, Unidad Medida, Ubicación,
    Fisico, STOCK, Difere, Observac.
    """
    archivo_excel = Path(archivo_excel)
    salida_base = Path(salida_base)
    salida_base.mkdir(parents=True, exist_ok=True)

    xls = pd.ExcelFile(archivo_excel)
    outputs = []
    processed = 0
    skipped = 0

    for sheet in xls.sheet_names:
        sheet_clean = str(sheet).strip()

        try:
            fecha = datetime.strptime(sheet_clean, "%d-%m-%Y")
        except Exception:
            skipped += 1
            continue

        if fecha.year != anio or not (mes_inicio <= fecha.month <= mes_fin):
            skipped += 1
            continue

        # leer hoja
        df = pd.read_excel(archivo_excel, sheet_name=sheet, dtype=str)

        if df is None or df.empty:
            skipped += 1
            continue

        # mapear columnas reales → canónicas
        col_map = _build_column_map(list(df.columns))
        df = df.rename(columns=col_map)

        columnas_necesarias = [
            "Item",
            "Código del Material",
            "Texto breve de material",
            "Unidad Medida",
            "Ubicación",
            "Fisico",
            "STOCK",
            "Difere",
            "Observac.",
        ]

        faltantes = [c for c in columnas_necesarias if c not in df.columns]
        if faltantes:
            raise Exception(
                f"❌ Columnas faltantes en hoja {sheet_clean}: {faltantes}\n"
                f"📌 Columnas encontradas: {[str(c) for c in df.columns]}"
            )

        df = df[columnas_necesarias].copy()

        # limpieza mínima
        df["Código del Material"] = df["Código del Material"].astype(str).str.strip()
        df["Ubicación"] = df["Ubicación"].astype(str).str.replace(" ", "").str.upper().str.strip()

        # salida /2025/04/
        out_dir = salida_base / f"{fecha:%Y}" / f"{fecha:%m}"
        out_dir.mkdir(parents=True, exist_ok=True)

        out_file = out_dir / f"inventario_{fecha:%Y_%m_%d}.xlsx"
        df.to_excel(out_file, index=False)

        outputs.append(str(out_file))
        processed += 1

    return SplitResult(
        total_sheets=len(xls.sheet_names),
        processed=processed,
        skipped=skipped,
        outputs=outputs,
    )
