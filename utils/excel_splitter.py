import pandas as pd
from datetime import datetime
from pathlib import Path


def split_excel_by_day(
    excel_path: str,
    output_base: str = "inventarios_procesados",
    year: int = 2025,
    start_month: int = 4,
    end_month: int = 12
):
    """
    Divide un Excel histórico con múltiples hojas (por día)
    en archivos diarios organizados por año/mes.
    """

    output_base = Path(output_base)
    xls = pd.ExcelFile(excel_path)

    for sheet in xls.sheet_names:
        try:
            fecha = datetime.strptime(sheet.strip(), "%d-%m-%Y")
        except ValueError:
            continue

        if fecha.year != year:
            continue

        if not (start_month <= fecha.month <= end_month):
            continue

        print(f"📅 Procesando hoja: {sheet}")

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

        # Crear carpetas año / mes
        out_dir = output_base / str(fecha.year) / f"{fecha.month:02d}"
        out_dir.mkdir(parents=True, exist_ok=True)

        out_file = out_dir / f"inventario_{fecha:%Y_%m_%d}.xlsx"
        df.to_excel(out_file, index=False)

    print("✅ Excel histórico dividido correctamente")
