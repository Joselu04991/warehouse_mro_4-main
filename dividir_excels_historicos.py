import pandas as pd
from datetime import datetime
from pathlib import Path

# ================= CONFIGURACIÓN =================

ENTRADA = Path("excels_grandes")  # aquí pones TODOS los Excel grandes
SALIDA = Path("inventarios_procesados")

INICIO = datetime(2025, 4, 1)
FIN = datetime(2025, 12, 31)

# ================================================

SALIDA.mkdir(exist_ok=True)

def normalizar_columnas(df):
    mapa = {
        "Código del Material": ["Código del Material", "Codigo", "Material"],
        "Texto breve de material": ["Texto breve de material", "Descripcion"],
        "Unidad de medida base": ["Unidad Medid", "Unidad", "UM"],
        "Ubicación": ["Ubicación", "Ubicacion"],
        "Libre utilización": ["Fisico", "Stock", "Libre"]
    }

    nuevas = {}
    for std, variantes in mapa.items():
        for v in variantes:
            if v in df.columns:
                nuevas[v] = std
                break

    df = df.rename(columns=nuevas)
    return df[list(mapa.keys())]

# ================= PROCESAMIENTO =================

for archivo in ENTRADA.glob("*.xlsx"):
    print(f"\n📂 Procesando archivo: {archivo.name}")
    xls = pd.ExcelFile(archivo)

    for hoja in xls.sheet_names:
        try:
            fecha = datetime.strptime(hoja.strip(), "%d-%m-%Y")
        except:
            continue

        if not (INICIO <= fecha <= FIN):
            continue

        print(f"  📄 Hoja {hoja}")

        df = pd.read_excel(
            archivo,
            sheet_name=hoja,
            dtype=str
        )

        df = normalizar_columnas(df)

        df["Ubicación"] = df["Ubicación"].str.replace(" ", "").str.upper()
        df["Libre utilización"] = pd.to_numeric(
            df["Libre utilización"], errors="coerce"
        ).fillna(0)

        # 📁 crear carpetas año/mes
        carpeta = SALIDA / str(fecha.year) / f"{fecha.month:02d}"
        carpeta.mkdir(parents=True, exist_ok=True)

        salida = carpeta / f"inventario_{fecha:%Y_%m_%d}.xlsx"
        df.to_excel(salida, index=False)

        print(f"    ✅ Guardado: {salida}")

print("\n🎉 PROCESO TERMINADO")
