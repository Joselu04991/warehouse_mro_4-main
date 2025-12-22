import pandas as pd
from datetime import datetime
from pathlib import Path
import re

def normalizar(col):
    return (
        col.strip()
        .lower()
        .replace("\n", " ")
        .replace("\r", " ")
        .replace("  ", " ")
    )

def dividir_excel_por_dias(
    archivo_excel,
    output_base="inventarios_procesados",
    anio=2025,
    mes_inicio=4,
    mes_fin=12
):
    output_base = Path(output_base) / str(anio)
    output_base.mkdir(parents=True, exist_ok=True)

    xls = pd.ExcelFile(archivo_excel)

    for sheet in xls.sheet_names:

        # 🔹 detectar fecha en nombre de hoja
        try:
            fecha = datetime.strptime(sheet.strip(), "%d-%m-%Y")
        except:
            continue

        if not (mes_inicio <= fecha.month <= mes_fin):
            continue

        print(f"📄 Procesando hoja: {sheet}")

        df = pd.read_excel(
            archivo_excel,
            sheet_name=sheet,
            dtype=str
        )

        # 🔹 normalizar columnas
        df.columns = [normalizar(c) for c in df.columns]

        # 🔹 mapeo flexible (ESTE ES EL FIX CLAVE)
        mapa = {
            "codigo": ["código del material", "codigo del material"],
            "texto": ["texto breve de material"],
            "unidad": ["unidad medida", "unidad medid", "unidad"],
            "ubicacion": ["ubicación", "ubicacion"],
            "stock": ["fisico", "stock"]
        }

        def encontrar(col_opciones):
            for c in col_opciones:
                if c in df.columns:
                    return c
            return None

        c_codigo = encontrar(mapa["codigo"])
        c_texto = encontrar(mapa["texto"])
        c_unidad = encontrar(mapa["unidad"])
        c_ubicacion = encontrar(mapa["ubicacion"])
        c_stock = encontrar(mapa["stock"])

        if not all([c_codigo, c_texto, c_unidad, c_ubicacion, c_stock]):
            print("⚠️ Hoja ignorada por columnas incompatibles")
            continue

        df_final = df[[c_codigo, c_texto, c_unidad, c_ubicacion, c_stock]].copy()

        df_final.columns = [
            "Código del Material",
            "Texto breve de material",
            "Unidad de medida base",
            "Ubicación",
            "Libre utilización"
        ]

        # 🔹 limpiar datos
        df_final["Ubicación"] = df_final["Ubicación"].astype(str).str.replace(" ", "").str.upper()
        df_final["Libre utilización"] = pd.to_numeric(
            df_final["Libre utilización"], errors="coerce"
        ).fillna(0)

        # 🔹 estructura de carpetas
        carpeta_mes = output_base / f"{fecha.month:02d}"
        carpeta_mes.mkdir(exist_ok=True)

        salida = carpeta_mes / f"inventario_{fecha:%Y_%m_%d}.xlsx"
        df_final.to_excel(salida, index=False)

        print(f"✅ Generado: {salida}")
