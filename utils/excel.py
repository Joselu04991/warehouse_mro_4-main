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

    if df is None or df.empty:
        ws = wb.active
        ws.title = "DISCREPANCIAS"
        ws.append(["SIN DATOS PARA EXPORTAR"])
        wb.save(output)
        output.seek(0)
        return output

    df = df.copy()

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
            df[c] = ""

    df = df[columnas]

    # =========================
    # Hoja 1: RESUMEN
    # =========================
    ws0 = wb.active
    ws0.title = "RESUMEN"

    title_fill = PatternFill("solid", fgColor="1F4E78")
    title_font = Font(bold=True, color="FFFFFF", size=14)
    bold = Font(bold=True)
    center = Alignment(horizontal="center", vertical="center")
    left = Alignment(horizontal="left", vertical="center")

    ws0["A1"] = "REPORTE DE DISCREPANCIAS - WAREHOUSE MRO"
    ws0["A1"].fill = title_fill
    ws0["A1"].font = title_font
    ws0["A1"].alignment = left
    ws0.merge_cells("A1:F1")

    generado_por = (meta or {}).get("generado_por", "Sistema")
    generado_en = (meta or {}).get("generado_en", "")

    ws0["A3"] = "Generado por:"
    ws0["B3"] = generado_por
    ws0["A4"] = "Generado en (Perú):"
    ws0["B4"] = generado_en

    ws0["A3"].font = bold
    ws0["A4"].font = bold

    # Conteos por estado
    estados = df["Estado"].value_counts().to_dict()
    ws0["A6"] = "Resumen por Estado"
    ws0["A6"].font = Font(bold=True, size=12)

    ws0.append(["Estado", "Cantidad"])
    ws0["A7"].font = bold
    ws0["B7"].font = bold

    row = 8
    for k in ["OK", "FALTA", "CRÍTICO", "SOBRA", "NO CONTADO"]:
        ws0[f"A{row}"] = k
        ws0[f"B{row}"] = int(estados.get(k, 0))
        row += 1

    ws0["D3"] = "Total items:"
    ws0["E3"] = int(len(df))
    ws0["D3"].font = bold

    # Ajuste ancho
    for col in range(1, 7):
        ws0.column_dimensions[get_column_letter(col)].width = 22

    # =========================
    # Hoja 2: DISCREPANCIAS
    # =========================
    ws = wb.create_sheet("DISCREPANCIAS")
    ws.append(columnas)

    for _, r in df.iterrows():
        ws.append(list(r))

    header = PatternFill("solid", fgColor="1F4E78")
    font = Font(bold=True, color="FFFFFF")
    thin = Side(border_style="thin", color="000000")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    # Header style
    for cell in ws[1]:
        cell.fill = header
        cell.font = font
        cell.alignment = center
        cell.border = border

    # Column widths
    widths = [18, 45, 10, 14, 14, 14, 12, 12]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    fill_ok = PatternFill("solid", fgColor="C6EFCE")
    fill_falta = PatternFill("solid", fgColor="FFEB9C")
    fill_critico = PatternFill("solid", fgColor="FFC7CE")
    fill_sobra = PatternFill("solid", fgColor="BFEFFF")
    fill_nocont = PatternFill("solid", fgColor="E7E6E6")

    # Body style + colores por Estado
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
        estado_val = str(row[7].value).upper() if row[7].value is not None else ""
        if "CRÍTICO" in estado_val:
            row_fill = fill_critico
        elif "FALTA" in estado_val:
            row_fill = fill_falta
        elif "SOBRA" in estado_val:
            row_fill = fill_sobra
        elif "NO CONTADO" in estado_val:
            row_fill = fill_nocont
        else:
            row_fill = fill_ok

        for cell in row:
            cell.border = border
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
            cell.fill = row_fill

    wb.save(output)
    output.seek(0)
    return output


