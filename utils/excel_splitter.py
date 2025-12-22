import pandas as pd
from datetime import datetime
from pathlib import Path

def dividir_excel_por_dias(
    archivo_excel,
    salida_base,
    anio,
    mes_inicio,
    mes_fin
):
    salida_base = Path(salida_base)
    salida_base.mkdir(exist_ok=True)

    xls = pd.ExcelFile(archivo_excel)

    for sheet in xls.sheet_names:
        try:
            fecha = datetime.strptime(sheet.strip(), "%d-%m-%Y")
        except:
            continue

        if fecha.year != anio or not (mes_inicio <= fecha.month <= mes_fin):
            continue

        df = pd.read_excel(
            archivo_excel,
            sheet_name=sheet,
            dtype=str
        )

        df.columns = df.columns.str.strip()

        columnas_map = {
            "Código del Material": "material_code",
            "Texto breve de material": "material_text",
            "Unidad Medida": "base_unit",
            "Ubicación": "location",
            "Fisico": "fisico",
            "STOCK": "stock",
            "Difere": "diferencia",
            "Observac.": "observacion"
        }

        for col in columnas_map:
            if col not in df.columns:
                raise Exception(f"❌ Falta columna '{col}' en hoja {sheet}")

        df = df[list(columnas_map.keys())]
        df = df.rename(columns=columnas_map)

        out_dir = salida_base / str(anio) / f"{fecha.month:02d}"
        out_dir.mkdir(parents=True, exist_ok=True)

        salida = out_dir / f"inventario_{fecha:%Y_%m_%d}.xlsx"
        df.to_excel(salida, index=False)

    return True
