import pandas as pd
from datetime import datetime
from pathlib import Path

# ================= CONFIGURACIÓN =================

ENTRADA = Path("inventarios_originales")
SALIDA = Path("inventarios_procesados")

ANIO = 2025
FECHA_INICIO = datetime(2025, 4, 1)
FECHA_FIN = datetime(2025, 12, 31)

COLUMNAS_OBJETIVO = {
    "Código del Material": "Código del Material",
    "Texto breve de material": "Texto breve de material",
    "Unidad Medid": "Unidad de medida base",
    "Unidad de medida base": "Unidad de medida base",
    "Ubicación": "Ubicación",
    "Fisico": "Libre utilización",
    "Físico": "Libre utilización",
    "Libre utilización": "Libre utilización",
}

# ================= PROCESO =================

def normalizar_columnas(df):
    nuevas = {}
    for c in df.columns:
        if c in COLUMNAS_OBJETIVO:
            nuevas[c] = COLUMNAS_OBJETIVO[c]
    return df.rename(columns=nuevas)


def procesar_excel(path_excel):
    print(f"\n📦 Procesando archivo: {path_excel.name}")
    xls = pd.ExcelFile(path_excel)

    for sheet in xls.sheet_names:
        try:
            fecha = datetime.strptime(sheet.strip(), "%d-%m-%Y")
        except:
            continue

        if not (FECHA_INICIO <= fecha <= FECHA_FIN):
            continue

        print(f"   └─ 📅 {sheet}")

        df = pd.read_excel(
            path_excel,
            sheet_name=sheet,
            dtype=str
        )

        df = normalizar_columnas(df)

        columnas_finales = [
            "Código del Material",
            "Texto breve de material",
            "Unidad de medida base",
            "Ubicación",
            "Libre utilización"
        ]

        if not all(c in df.columns for c in columnas_finales):
            print("     ⚠️ Hoja omitida (faltan columnas)")
            continue

        df = df[columnas_finales]
        df["Ubicación"] = df["Ubicación"].astype(str).str.replace(" ", "").str.upper()
        df["Libre utilización"] = pd.to_numeric(df["Libre utilización"], errors="coerce").fillna(0)

        carpeta_salida = (
            SALIDA /
            str(fecha.year) /
            f"{fecha.month:02d}"
        )
        carpeta_salida.mkdir(parents=True, exist_ok=True)

        salida = carpeta_salida / f"inventario_{fecha:%Y_%m_%d}.xlsx"
        df.to_excel(salida, index=False)

        print(f"     ✅ Generado: {salida}")


def main():
    if not ENTRADA.exists():
        print("❌ No existe inventarios_originales/")
        return

    for excel in ENTRADA.glob("*.xlsx"):
        procesar_excel(excel)

    print("\n🎉 PROCESO COMPLETO FINALIZADO")


if __name__ == "__main__":
    main()
