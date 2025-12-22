import pandas as pd
from datetime import datetime
from pathlib import Path


def dividir_excel_por_dias(
    archivo_excel,
    salida_base,
    fecha_inicio=None,
    fecha_fin=None
):
    """
    Divide un Excel histórico con múltiples hojas (fechas) en archivos diarios.
    Mantiene TODAS las columnas originales.
    """

    salida_base = Path(salida_base)
    salida_base.mkdir(parents=True, exist_ok=True)

    xls = pd.ExcelFile(archivo_excel)

    for hoja in xls.sheet_names:
        try:
            fecha = datetime.strptime(hoja.strip(), "%d-%m-%Y")
        except ValueError:
            # hoja que no es fecha
            continue

        if fecha_inicio and fecha < fecha_inicio:
            continue
        if fecha_fin and fecha > fecha_fin:
            continue

        print(f"📄 Procesando hoja {hoja}")

        df = pd.read_excel(
            archivo_excel,
            sheet_name=hoja,
            dtype=str
        )

        # 🔁 NORMALIZAR NOMBRES (los reales de tu Excel)
        rename_map = {
            "Unidad Medida": "Unidad de medida base",
            "Fisico": "Libre utilización"
        }

        df.columns = df.columns.str.strip()
        df = df.rename(columns=rename_map)

        # ✅ VALIDAR columnas mínimas
        columnas_necesarias = [
            "Código del Material",
            "Texto breve de material",
            "Unidad de medida base",
            "Ubicación",
            "Libre utilización",
            "STOCK",
            "Difere",
            "Observac."
        ]

        faltantes = [c for c in columnas_necesarias if c not in df.columns]
        if faltantes:
            raise Exception(
                f"❌ Columnas faltantes en hoja {hoja}: {faltantes}"
            )

        # 📂 estructura /inventarios_procesados/2025/04/
        carpeta = salida_base / str(fecha.year) / f"{fecha.month:02d}"
        carpeta.mkdir(parents=True, exist_ok=True)

        salida = carpeta / f"inventario_{fecha:%Y_%m_%d}.xlsx"
        df.to_excel(salida, index=False)

        print(f"✅ Generado {salida}")

    print("🎉 División completada correctamente")
