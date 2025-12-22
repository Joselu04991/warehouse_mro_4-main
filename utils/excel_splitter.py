import pandas as pd
from datetime import datetime
from pathlib import Path
from openpyxl import load_workbook


COLUMN_MAP = {
    "Código del Material": ["Código del Material", "Codigo del Material", "Codigo"],
    "Texto breve de material": ["Texto breve de material", "Descripción", "Texto"],
    "Unidad de medida base": ["Unidad Medida", "Unidad", "UM"],
    "Ubicación": ["Ubicación", "Ubicacion", "Location"],
    "Libre utilización": ["Fisico", "STOCK", "Cantidad"],
    "Difere": ["Difere", "Diferencia"],
    "Observac.": ["Observac.", "Observaciones"],
}


def _map_columns(df):
    mapped = {}
    for final, candidates in COLUMN_MAP.items():
        for c in candidates:
            if c in df.columns:
                mapped[final] = c
                break
    return mapped


def dividir_excel_por_dias(
    archivo_excel: Path,
    salida_base: str,
    anio: int,
    mes_inicio: int,
    mes_fin: int,
):
    salida_base = Path(salida_base)
    wb = load_workbook(archivo_excel, read_only=True, data_only=True)

    for sheet in wb.sheetnames:
        try:
            fecha = datetime.strptime(sheet.strip(), "%d-%m-%Y")
        except:
            continue

        if fecha.year != anio or not (mes_inicio <= fecha.month <= mes_fin):
            continue

        print(f"📄 Procesando hoja {sheet}")

        df = pd.read_excel(
            archivo_excel,
            sheet_name=sheet,
            dtype=str
        )

        col_map = _map_columns(df)

        required = [
            "Código del Material",
            "Texto breve de material",
            "Unidad de medida base",
            "Ubicación",
            "Libre utilización",
        ]

        if not all(k in col_map for k in required):
            raise Exception(
                f"❌ Columnas faltantes en hoja {sheet}: {list(col_map.keys())}"
            )

        df = df.rename(columns={v: k for k, v in col_map.items()})
        df = df[required].copy()

        df["Ubicación"] = df["Ubicación"].astype(str).str.replace(" ", "").str.upper()
        df["Libre utilización"] = pd.to_numeric(
            df["Libre utilización"], errors="coerce"
        ).fillna(0)

        out_dir = salida_base / str(fecha.year) / f"{fecha.month:02d}"
        out_dir.mkdir(parents=True, exist_ok=True)

        out_file = out_dir / f"inventario_{fecha:%Y_%m_%d}.xlsx"
        df.to_excel(out_file, index=False)

    print("✅ Excel histórico dividido correctamente")
