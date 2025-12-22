import pandas as pd
from datetime import datetime
from pathlib import Path

ENTRADA = Path("inventarios_brutos")
SALIDA = Path("inventarios_procesados")

INICIO = datetime(2025, 4, 1)
FIN = datetime(2025, 12, 31)

SALIDA.mkdir(exist_ok=True)

for archivo in ENTRADA.glob("*.xlsx"):
    print(f"📂 Procesando archivo: {archivo.name}")
    xls = pd.ExcelFile(archivo)

    for hoja in xls.sheet_names:
        try:
            fecha = datetime.strptime(hoja.strip(), "%d-%m-%Y")
        except:
            continue

        if not (INICIO <= fecha <= FIN):
            continue

        print(f"  🗓️ {hoja}")

        df = pd.read_excel(
            archivo,
            sheet_name=hoja,
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

        carpeta = SALIDA / f"{fecha.year}" / f"{fecha.month:02d}"
        carpeta.mkdir(parents=True, exist_ok=True)

        salida = carpeta / f"inventario_{fecha:%Y_%m_%d}.xlsx"
        df.to_excel(salida, index=False)

print("✅ Procesamiento terminado")
