from io import BytesIO
from datetime import datetime
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side


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
def generate_discrepancies_excel(df):
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
            df[c] = 0 if "Stock" in c or c == "Diferencia" else ""

    df = df[columnas]

    # =======================
    # HOJA 1: RESUMEN
    # =======================
    ws_resumen = wb.active
    ws_resumen.title = "RESUMEN"

    fecha = datetime.now().strftime("%d/%m/%Y %H:%M")

    ws_resumen.append(["REPORTE DE DISCREPANCIAS DE INVENTARIO"])
    ws_resumen.append([f"Fecha de generación: {fecha}"])
    ws_resumen.append(["Sistema: Warehouse MRO"])
    ws_resumen.append([])

    total = len(df)
    ok = (df["Estado"] == "OK").sum()
    falta = (df["Estado"] == "FALTA").sum()
    sobra = (df["Estado"] == "SOBRA").sum()
    critico = (df["Estado"] == "CRÍTICO").sum()

    resumen_data = [
        ("Total materiales", total),
        ("OK", ok),
        ("FALTANTES", falta),
        ("SOBRANTES", sobra),
        ("CRÍTICOS", critico),
    ]

    ws_resumen.append(["Indicador", "Cantidad"])
    for r in resumen_data:
        ws_resumen.append(r)

    header_fill = PatternFill("solid", fgColor="1F4E78")
    header_font = Font(bold=True, color="FFFFFF")

    for cell in ws_resumen[5]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")

    # =======================
    # HOJA 2: DETALLE
    # =======================
    ws = wb.create_sheet("DETALLE_DISCREPANCIAS")
    ws.append(columnas)

    for _, r in df.iterrows():
        ws.append(list(r))

    center = Alignment(horizontal="center", vertical="center")
    thin = Side(border_style="thin", color="000000")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    fill_ok = PatternFill("solid", fgColor="C6EFCE")
    fill_falta = PatternFill("solid", fgColor="FFC7CE")
    fill_sobra = PatternFill("solid", fgColor="FFEB9C")
    fill_critico = PatternFill("solid", fgColor="FF0000")

    for row in ws.iter_rows(min_row=2):
        estado = row[7].value
        for cell in row:
            cell.border = border
            cell.alignment = center

        if estado == "OK":
            for cell in row:
                cell.fill = fill_ok
        elif estado == "FALTA":
            for cell in row:
                cell.fill = fill_falta
        elif estado == "SOBRA":
            for cell in row:
                cell.fill = fill_sobra
        elif estado == "CRÍTICO":
            for cell in row:
                cell.fill = fill_critico
                cell.font = Font(color="FFFFFF", bold=True)

    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    for col in ws.columns:
        max_length = max(len(str(c.value)) if c.value else 0 for c in col)
        ws.column_dimensions[col[0].column_letter].width = max_length + 4

    wb.save(output)
    output.seek(0)
    return output

