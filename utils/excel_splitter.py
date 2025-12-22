import pandas as pd
from datetime import datetime
from pathlib import Path

def dividir_excel_por_dias(
    archivo_excel,
    salida_base="inventarios_procesados",
    anio=2025,
    mes_inicio=4,
    mes_fin=12
):
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

        carpeta_mes = salida_base / str(anio) / f"{fecha.month:02d}"
        carpeta_mes.mkdir(parents=True, exist_ok=True)

        df = pd.read_excel(
            archivo_excel,
            sheet_name=sheet,
            dtype=str
        )

        df = df.rename(columns={
            "Código del Material": "Código del Material",
            "Texto breve de material": "Texto breve de material",
            "Unidad Medid": "Unidad de medida base",
            "Ubicación": "Ubicación",
            "Fisico": "Libre utilización"
        })

        columnas = [
            "Código del Material",
            "Texto breve de material",
            "Unidad de medida base",
            "Ubicación",
            "Libre utilización"
        ]

        df = df[columnas]

        salida = carpeta_mes / f"inventario_{fecha:%Y_%m_%d}.xlsx"
        df.to_excel(salida, index=False)

    return True
