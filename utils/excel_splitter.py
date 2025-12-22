# utils/excel_splitter.py
import pandas as pd
from datetime import datetime
from pathlib import Path

def split_excel_by_day(
    excel_path,
    base_output="inventarios_procesados",
    year=2025,
    start_month=4,
    end_month=12
):
    base = Path(base_output) / str(year)
    base.mkdir(parents=True, exist_ok=True)

    xls = pd.ExcelFile(excel_path)

    for sheet in xls.sheet_names:
        try:
            fecha = datetime.strptime(sheet.strip(), "%d-%m-%Y")
        except:
            continue

        if not (start_month <= fecha.month <= end_month):
            continue

        month_dir = base / f"{fecha.month:02d}"
        month_dir.mkdir(exist_ok=True)

        df = pd.read_excel(
            excel_path,
            sheet_name=sheet,
            dtype=str
        )

        df = df.rename(columns={
            "Código del Material": "Código del Material",
            "Texto breve de material": "Texto breve de material",
            "Unidad Medid": "Unidad de medida base",
            "Ubicación": "Ubicación",
            "Fisico": "Libre utilización",
        })

        columnas = [
            "Código del Material",
            "Texto breve de material",
            "Unidad de medida base",
            "Ubicación",
            "Libre utilización",
        ]

        df = df[columnas]

        salida = month_dir / f"inventario_{fecha:%Y_%m_%d}.xlsx"
        df.to_excel(salida, index=False)

    return True
