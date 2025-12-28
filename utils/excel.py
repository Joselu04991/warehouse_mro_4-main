from io import BytesIO
from datetime import datetime
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter

# =============================================================================
# INVENTARIO BASE
# =============================================================================
def load_inventory_excel(file):
    df = pd.read_excel(file)

    columnas = [
        "Código del Material",
        "Texto breve de material",
        "Unidad de medida base",
        "Ubicación",
        "Libre utilización",
    ]

    for c in columnas:
        if c not in df.columns:
            raise Exception(f"❌ Falta columna: {c}")

    df = df.copy()
    df["Código del Material"] = df["Código del Material"].astype(str).str.strip()
    df["Texto breve de material"] = df["Texto breve de material"].astype(str).str.strip()
    df["Unidad de medida base"] = df["Unidad de medida base"].astype(str).str.strip()
    df["Ubicación"] = df["Ubicación"].astype(str).str.replace(" ", "").str.upper().str.strip()
    df["Libre utilización"] = pd.to_numeric(df["Libre utilización"], errors="coerce").fillna(0)

    return df

# =============================================================================
# INVENTARIO HISTÓRICO (EXCEL ANTIGUO)
# =============================================================================
def load_inventory_historic_excel(file):
    df = pd.read_excel(file)

    columnas_requeridas = [
        "Código del Material",
        "Texto breve de material",
        "Unidad Medida",
        "Ubicación",
        "Fisico",
        "STOCK",
        "Difere",
        "Observac.",
    ]

    for c in columnas_requeridas:
        if c not in df.columns:
            raise Exception(f"❌ Falta columna histórica: {c}")

    df = df.copy()

    df["Código del Material"] = df["Código del Material"].astype(str).str.strip()
    df["Texto breve de material"] = df["Texto breve de material"].astype(str).str.strip()
    df["Unidad Medida"] = df["Unidad Medida"].astype(str).str.strip()

    df["Ubicación"] = (
        df["Ubicación"]
        .astype(str)
        .str.replace(" ", "")
        .str.upper()
        .str.strip()
    )

    df["Fisico"] = pd.to_numeric(df["Fisico"], errors="coerce").fillna(0)
    df["STOCK"] = pd.to_numeric(df["STOCK"], errors="coerce").fillna(0)
    df["Difere"] = pd.to_numeric(df["Difere"], errors="coerce").fillna(0)
    df["Observac."] = df["Observac."].astype(str).fillna("")

    return df
# =============================================================================
# ALMACÉN 2D
# =============================================================================
def load_warehouse2d_excel(file):
    df = pd.read_excel(file)

    columnas_requeridas = [
        "Código del Material",
        "Texto breve de material",
        "Unidad de medida base",
        "Stock de seguridad",
        "Stock máximo",
        "Ubicación",
        "Libre utilización",
    ]

    for c in columnas_requeridas:
        if c not in df.columns:
            raise Exception(f"❌ Falta columna obligatoria en almacén 2D: {c}")

    df = df.copy()

    df["Código del Material"] = df["Código del Material"].astype(str).str.strip()
    df["Texto breve de material"] = df["Texto breve de material"].astype(str).str.strip()
    df["Unidad de medida base"] = df["Unidad de medida base"].astype(str).str.strip()

    df["Ubicación"] = (
        df["Ubicación"]
        .astype(str)
        .str.strip()
        .str.replace(" ", "")
        .str.upper()
    )

    df["Stock de seguridad"] = pd.to_numeric(df["Stock de seguridad"], errors="coerce").fillna(0)
    df["Stock máximo"] = pd.to_numeric(df["Stock máximo"], errors="coerce").fillna(0)
    df["Libre utilización"] = pd.to_numeric(df["Libre utilización"], errors="coerce").fillna(0)

    return df

# =============================================================================
# ORDENAR UBICACIONES
# =============================================================================
def sort_location_advanced(loc):
    try:
        loc = str(loc).replace(" ", "").upper()
        if loc.startswith("E"):
            nums = "".join(c for c in loc if c.isdigit())
            return int(nums) if nums else 999999
        return 999999
    except:
        return 999999


# =============================================================================
# EXCEL PRO DE DISCREPANCIAS (USADO POR inventory_routes)
# =============================================================================
def generate_discrepancies_excel(df, meta=None):

    output = BytesIO()
    wb = Workbook()

    # =========================
    # Validación
    # =========================
    if df is None or df.empty:
        ws = wb.active
        ws.title = "DISCREPANCIAS"
        ws.append(["SIN DATOS PARA EXPORTAR"])
        wb.save(output)
        output.seek(0)
        return output

    df = df.copy()

    # =========================
    # Columnas estándar
    # =========================
    columnas = [
        "Código Material",
        "Descripción",
        "Unidad",
        "Ubicación",
        "Stock sistema",
        "Stock contado",
        "Diferencia",
        "Estado",
    ]

    for c in columnas:
        if c not in df.columns:
            df[c] = 0 if "Stock" in c or c == "Diferencia" else ""

    # Normalización numérica
    df["Stock sistema"] = df["Stock sistema"].astype(float)
    df["Stock contado"] = df["Stock contado"].astype(float)

    # Diferencia SIEMPRE recalculada
    df["Diferencia"] = df["Stock contado"] - df["Stock sistema"]

    # Estado automático
    def estado(row):
        if row["Stock contado"] == 0:
            return "NO CONTADO"
        if row["Diferencia"] == 0:
            return "OK"
        if row["Diferencia"] < 0:
            return "FALTA" if abs(row["Diferencia"]) < 5 else "CRÍTICO"
        return "SOBRA"

    df["Estado"] = df.apply(estado, axis=1)

    df = df[columnas]

    # =========================
    # ESTILOS
    # =========================
    header_fill = PatternFill("solid", fgColor="1F4E78")
    header_font = Font(bold=True, color="FFFFFF")
    title_font = Font(bold=True, size=14, color="FFFFFF")
    bold = Font(bold=True)

    center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    left = Alignment(horizontal="left", vertical="center")

    thin = Side(style="thin")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    fill_ok = PatternFill("solid", fgColor="C6EFCE")
    fill_falta = PatternFill("solid", fgColor="FFEB9C")
    fill_critico = PatternFill("solid", fgColor="FFC7CE")
    fill_sobra = PatternFill("solid", fgColor="BFEFFF")
    fill_nocont = PatternFill("solid", fgColor="E7E6E6")

    # =========================
    # HOJA 1 – RESUMEN
    # =========================
    ws0 = wb.active
    ws0.title = "RESUMEN"

    ws0["A1"] = "REPORTE DE DISCREPANCIAS – WAREHOUSE MRO"
    ws0.merge_cells("A1:F1")
    ws0["A1"].font = title_font
    ws0["A1"].fill = header_fill
    ws0["A1"].alignment = left

    generado_por = (meta or {}).get("generado_por", "Sistema MRO")
    generado_en = (meta or {}).get(
        "generado_en",
        datetime.now().strftime("%Y-%m-%d %H:%M")
    )

    ws0["A3"] = "Generado por:"
    ws0["B3"] = generado_por
    ws0["A4"] = "Generado en:"
    ws0["B4"] = generado_en

    ws0["A3"].font = bold
    ws0["A4"].font = bold

    total = len(df)
    ok = (df["Estado"] == "OK").sum()
    exactitud = round((ok / total) * 100, 2) if total else 0

    ws0["D3"] = "Total ítems:"
    ws0["E3"] = total
    ws0["D4"] = "Exactitud:"
    ws0["E4"] = f"{exactitud}%"

    ws0["D3"].font = bold
    ws0["D4"].font = bold

    ws0["A6"] = "Resumen por Estado"
    ws0["A6"].font = Font(bold=True, size=12)

    ws0.append(["Estado", "Cantidad"])
    ws0["A7"].font = bold
    ws0["B7"].font = bold

    fila = 8
    for estado_lbl in ["OK", "FALTA", "CRÍTICO", "SOBRA", "NO CONTADO"]:
        ws0[f"A{fila}"] = estado_lbl
        ws0[f"B{fila}"] = int((df["Estado"] == estado_lbl).sum())
        fila += 1

    for col in range(1, 7):
        ws0.column_dimensions[get_column_letter(col)].width = 22

    # =========================
    # HOJA 2 – DETALLE
    # =========================
    ws = wb.create_sheet("DISCREPANCIAS")
    ws.append(columnas)

    for r in df.itertuples(index=False):
        ws.append(list(r))

    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center
        cell.border = border

    widths = [20, 45, 10, 14, 16, 16, 12, 14]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
        estado_val = str(row[7].value)

        if estado_val == "CRÍTICO":
            fill = fill_critico
        elif estado_val == "FALTA":
            fill = fill_falta
        elif estado_val == "SOBRA":
            fill = fill_sobra
        elif estado_val == "NO CONTADO":
            fill = fill_nocont
        else:
            fill = fill_ok

        for cell in row:
            cell.border = border
            cell.alignment = center
            cell.fill = fill

    wb.save(output)
    output.seek(0)
    return output
# =============================================================================
# EXPORTAR SNAPSHOT HISTÓRICO A EXCEL  ✅ (ESTO FALTABA)
# =============================================================================
def generate_history_snapshot_excel(items, snapshot_name):

    wb = Workbook()
    ws = wb.active
    ws.title = "INVENTARIO"

    headers = [
        "Código Material",
        "Descripción",
        "Unidad",
        "Ubicación",
        "Stock",
        "Fecha",
    ]
    ws.append(headers)

    for i in items:
        ws.append([
            i.material_code,
            i.material_text,
            i.base_unit,
            i.location,
            i.libre_utilizacion,
            i.creado_en.strftime("%d/%m/%Y") if i.creado_en else "",
        ])

    for col in range(1, len(headers) + 1):
        ws.column_dimensions[get_column_letter(col)].width = 22

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output

