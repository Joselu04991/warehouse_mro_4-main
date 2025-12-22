# utils/excel_splitter.py
import pandas as pd
from datetime import datetime
from pathlib import Path

def split_excel_by_day(
    excel_path: str,
    output_base="inventarios_procesados",
    start_date=None,
    end_date=None
):
    output_base = Path(output_base)

    xls = pd.ExcelFile(excel_path)

    for sheet in xls.sheet_names:
        try:
            fecha = datetime.strptime(sheet.strip(), "%d-%m-%Y")
        except ValueError:
            continue

        if start_date and fecha < start_date:
            continue
        if end_date and fecha > end_date:
            continue

        print(f"Procesando hoja {sheet}")

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

        # 📁 Crear carpetas automáticamente
        out_dir = output_base / f"{fecha.year}" / f"{fecha.month:02d}"
        out_dir.mkdir(parents=True, exist_ok=True)

        out_file = out_dir / f"inventario_{fecha:%Y_%m_%d}.xlsx"
        df.to_excel(out_file, index=False)

    return True
