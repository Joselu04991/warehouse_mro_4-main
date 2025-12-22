import pandas as pd
from datetime import datetime
from pathlib import Path
import re

COLUMN_MAP = {
    "Código del Material": ["Código del Material", "Codigo del Material"],
    "Texto breve de material": ["Texto breve de material"],
    "Unidad Medida": ["Unidad Medida", "Unidad"],
    "Ubicación": ["Ubicación", "Ubicacion"],
    "Fisico": ["Fisico"],
    "STOCK": ["STOCK"],
    "Difere": ["Difere"],
    "Observac.": ["Observac.", "Observacion"],
}

def normalizar_columnas(df):
    nuevas = {}
    for col, posibles in COLUMN_MAP.items():
        for p in posibles:
            if p in df.columns:
                nuevas[p] = col
                break
    return df.rename(columns=nuevas)

def dividir_excel_por_dias(archivo_excel, salida_base, anio, mes_inicio, mes_fin):
    salida_base = Path(salida_base)
    salida_base.mkdir(parents=True, exist_ok=True)

    xls = pd.ExcelFile(archivo_excel)

    for sheet in xls.sheet_names:
        try:
            fecha = datetime.strptime(sheet.strip(), "%d-%m-%Y")
        except:
            continue

        if fecha.year != anio or not (mes_inicio <= fecha.month <= mes_fin):
            continue

        df = pd.read_excel(xls, sheet_name=sheet)
        df = normalizar_columnas(df)

        requeridas = [
            "Código del Material",
            "Texto breve de material",
            "Unidad Medida",
            "Ubicación",
            "Fisico",
            "STOCK",
            "Difere",
            "Observac.",
        ]

        faltantes = [c for c in requeridas if c not in df.columns]
        if faltantes:
            raise Exception(f"Columnas faltantes en hoja {sheet}: {faltantes}")

        salida_dir = salida_base / str(anio) / f"{fecha.month:02d}"
        salida_dir.mkdir(parents=True, exist_ok=True)

        salida = salida_dir / f"inventario_{fecha:%Y_%m_%d}.xlsx"
        df[requeridas].to_excel(salida, index=False)

    return True
