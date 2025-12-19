import pandas as pd
from datetime import datetime
from pathlib import Path

# ================= CONFIGURACIÓN =================

CARPETA_EXCELS = Path("excels_historicos")      # aquí van TODOS los excels grandes
SALIDA = Path("inventarios_diarios")            # salida final
SALIDA.mkdir(exist_ok=True)

INICIO = datetime(2025, 4, 1)
FIN = datetime(2025, 12, 31)

COLUMNAS_OBJETIVO = {
    "Código del Material": ["Código del Material", "Codigo", "Material"],
    "Texto breve de material": ["Texto breve de material", "Descripción", "Texto"],
    "Unidad de medida base": ["Unidad Medid", "Unidad", "UM"],
    "Ubicación": ["Ubicación", "Ubicacion", "Location"],
    "Libre utilización": ["Fisico", "Libre utilización", "Stock", "Cantidad"],
}

# ================= FUNCIONES =================

def mapear_columnas(df):
    cols = {}
    for destino, posibles in COLUMNAS_OBJETIVO.items():
        for c in posibles:
            if c in df.columns:
                cols[destino] = c
                break
    if len(cols) != len(COLUMNAS_OBJETIVO):
        raise Exception("❌ Columnas requeridas no encontradas")
    return cols

def normalizar(df, mapa):
    df = df[list(mapa.values())].copy()
    df.columns = list(mapa.keys())

    df["Código del Material"] = df["Código del Material"].astype(str).str.strip()
    df["Texto breve de material"] = df["Texto breve de material"].astype(str).str.strip()
    df["Unidad de medida base"] = df["Unidad de medida base"].astype(str).str.strip()
    df["Ubicación"] = df["Ubicación"].astype(str).str.replace(" ", "").str.upper()
    df["Libre utilización"] = pd.to_numeric(
        df["Libre utilización"], errors="coerce"
    ).fillna(0)

    return df

# ================= PROCESO =================

for archivo in CARPETA_EXCELS.glob("*.xlsx"):
    print(f"\n📂 Procesando archivo: {archivo.name}")

    try:
        xls = pd.ExcelFile(archivo)
    except Exception as e:
        print(f"❌ No se pudo abrir {archivo.name}: {e}")
        continue

    for hoja in xls.sheet_names:
        try:
            fecha = datetime.strptime(hoja.strip(), "%d-%m-%Y")
        except:
            continue

        if not (INICIO <= fecha <= FIN):
            continue

        print(f"   ▶ Hoja válida: {hoja}")

        try:
            df = pd.read_excel(
                archivo,
                sheet_name=hoja,
                dtype=str
            )

            mapa = mapear_columnas(df)
            df = normalizar(df, mapa)

            carpeta_fecha = SALIDA / f"{fecha:%Y}" / f"{fecha:%m}"
            carpeta_fecha.mkdir(parents=True, exist_ok=True)

            salida = carpeta_fecha / f"inventario_{fecha:%Y_%m_%d}.xlsx"
            df.to_excel(salida, index=False)

        except Exception as e:
            print(f"   ❌ Error en hoja {hoja}: {e}")

print("\n✅ PROCESO TERMINADO")
