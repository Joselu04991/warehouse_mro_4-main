import pandas as pd
from datetime import datetime
from pathlib import Path

ARCHIVO_GRANDE = "INVENTARIO_HISTORICO.xlsx"
SALIDA = Path("inventarios_diarios")
SALIDA.mkdir(exist_ok=True)

# rango permitido
INICIO = datetime(2025, 4, 1)
FIN = datetime(2025, 12, 31)

xls = pd.ExcelFile(ARCHIVO_GRANDE)

for sheet in xls.sheet_names:
    try:
        fecha = datetime.strptime(sheet.strip(), "%d-%m-%Y")
    except:
        continue

    if not (INICIO <= fecha <= FIN):
        continue

    print(f"Procesando {sheet}")

    df = pd.read_excel(
        ARCHIVO_GRANDE,
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

    salida = SALIDA / f"inventario_{fecha:%Y_%m_%d}.xlsx"
    df.to_excel(salida, index=False)

print("✅ Inventarios diarios generados correctamente")
