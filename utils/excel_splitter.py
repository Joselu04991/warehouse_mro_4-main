# utils/excel_splitter.py
import pandas as pd
from datetime import datetime
from pathlib import Path


def normalizar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza columnas reales del Excel histórico
    a un formato estándar interno
    """

    # limpiar nombres
    df.columns = (
        df.columns
        .astype(str)
        .str.replace("\n", " ")
        .str.replace("  ", " ")
        .str.strip()
    )

    mapa = {
        "Código del Material": ["Código del Material", "Codigo del Material", "CODIGO"],
        "Texto breve de material": ["Texto breve de material", "Descripción"],
        "Unidad Medida": ["Unidad Medida", "Unidad", "U.M"],
        "Ubicación": ["Ubicación", "Ubicacion"],
        "Fisico": ["Fisico", "Físico", "Stock Fisico"],
        "STOCK": ["STOCK", "Stock Sistema"],
        "Difere": ["Difere", "Diferencia"],
        "Observac.": ["Observac.", "Observaciones"],
    }

    columnas_finales = {}

    for estandar, variantes in mapa.items():
        for v in variantes:
            if v in df.columns:
                columnas_finales[v] = estandar
                break

    df = df.rename(columns=columnas_finales)

    faltantes = set(mapa.keys()) - set(df.columns)
    if faltantes:
        raise Exception(f"❌ Columnas faltantes en hoja: {faltantes}")

    return df


def dividir_excel_por_dias(
    archivo_excel: Path,
    salida_base: Path,
    fecha_inicio: datetime,
    fecha_fin: datetime,
):
    salida_base.mkdir(parents=True, exist_ok=True)

    xls = pd.ExcelFile(archivo_excel)

    for sheet in xls.sheet_names:
        try:
            fecha = datetime.strptime(sheet.strip(), "%d-%m-%Y")
        except:
            continue

        if not (fecha_inicio <= fecha <= fecha_fin):
            continue

        df = pd.read_excel(
            archivo_excel,
            sheet_name=sheet,
            dtype=str
        )

        df = normalizar_columnas(df)

        # carpetas automáticas
        carpeta = salida_base / f"{fecha.year}" / f"{fecha.month:02d}"
        carpeta.mkdir(parents=True, exist_ok=True)

        salida = carpeta / f"inventario_{fecha:%Y_%m_%d}.xlsx"
        df.to_excel(salida, index=False)

        print(f"✅ {salida}")
