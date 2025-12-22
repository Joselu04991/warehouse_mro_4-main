from pathlib import Path
from datetime import datetime
from openpyxl import load_workbook
import pandas as pd

BASE_DIR = Path("inventarios_procesados")

def dividir_excel_por_dias(archivo_excel):
    wb = load_workbook(archivo_excel, read_only=True, data_only=True)

    for sheet_name in wb.sheetnames:
        try:
            fecha = datetime.strptime(sheet_name.strip(), "%d-%m-%Y")
        except:
            continue

        if not (fecha.month >= 4 and fecha.month <= 12):
            continue

        print(f"Procesando hoja {sheet_name}")

        ws = wb[sheet_name]
        data = list(ws.values)
        headers = data[0]
        rows = data[1:]

        df = pd.DataFrame(rows, columns=headers)

        df = df.rename(columns={
            "Código del Material": "Código del Material",
            "Texto breve de material": "Texto breve de material",
            "Unidad Medid": "Unidad de medida base",
            "Ubicación": "Ubicación",
            "Fisico": "Libre utilización"
        })

        df = df[
            ["Código del Material",
             "Texto breve de material",
             "Unidad de medida base",
             "Ubicación",
             "Libre utilización"]
        ]

        salida_dir = BASE_DIR / str(fecha.year) / f"{fecha.month:02d}"
        salida_dir.mkdir(parents=True, exist_ok=True)

        salida = salida_dir / f"inventario_{fecha:%Y_%m_%d}.xlsx"
        df.to_excel(salida, index=False)

    wb.close()
