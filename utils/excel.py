from io import BytesIO
from datetime import datetime
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side


# =============================================================================
# 1. CARGA FLEXIBLE DE INVENTARIO BASE
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
    df["Ubicación"] = df["Ubicación"].astype(str).str.strip().str.replace(" ", "").str.upper()

    # Libre utilización a número (si viene vacío/NaN, lo ponemos 0)
    df["Libre utilización"] = pd.to_numeric(df["Libre utilización"], errors="coerce").fillna(0)

    return df


# =============================================================================
# 2. CARGA DE INVENTARIO 2D (REQUERIDO POR warehouse2d_routes)
# =============================================================================
def load_warehouse2d_excel(file):
    df = pd.read_excel(file)

    columnas_requeridas = [
        "Código del Material",
        "Texto breve de material",
        "Unidad de medida base",
        "Ubicación",
        "Stock máximo",
        "Consumo mes actual",
        "Libre utilización",
        "Tamaño de lote mínimo",
    ]

    for c in columnas_requeridas:
        if c not in df.columns:
            raise Exception(f"❌ Falta columna obligatoria en mapa 2D: {c}")

    df = df.copy()

    df["Código del Material"] = df["Código del Material"].astype(str).str.strip()
    df["Texto breve de material"] = df["Texto breve de material"].astype(str).str.strip()
    df["Unidad de medida base"] = df["Unidad de medida base"].astype(str).str.strip()
    df["Ubicación"] = df["Ubicación"].astype(str).str.strip().str.replace(" ", "").str.upper()

    df["Stock máximo"] = pd.to_numeric(df["Stock máximo"], errors="coerce").fillna(0)
    df["Consumo mes actual"] = pd.to_numeric(df["Consumo mes actual"], errors="coerce").fillna(0)
    df["Libre utilización"] = pd.to_numeric(df["Libre utilización"], errors="coerce").fillna(0)
    df["Tamaño de lote mínimo"] = pd.to_numeric(df["Tamaño de lote mínimo"], errors="coerce").fillna(0)

    return df


# =============================================================================
# 3. ORDENAR UBICACIONES (E001, E015, E120...)
# =============================================================================
def sort_location_advanced(loc):
    try:
        if isinstance(loc, str):
            loc = loc.strip().upper().replace(" ", "")
            if loc.startswith("E"):
                nums = "".join([x for x in loc if x.isdigit()])
                return int(nums) if nums else 999999
        return 999999
    except:
        return 999999


# =============================================================================
# 4. GENERAR EXCEL PRO DE DISCREPANCIAS (NIVEL AUDITORÍA)
# =============================================================================
def generate_discrepancies_excel(df):
    """
    Excel PRO:
    - Hoja 1: DISCREPANCIAS (título, filtros, freeze panes, colores por estado)
    - Hoja 2: RESUMEN (KPIs)
    """

    output = BytesIO()
    wb = Workbook()

    # -------------------------------
    # Normalización defensiva
    # -------------------------------
    if df is None or df.empty:
        ws = wb.active
        ws.title = "DISCREPANCIAS"
        ws.append(["SIN DATOS PARA EXPORTAR"])
        wb.save(output)
        output.seek(0)
        return output

    df = df.copy()

    # Asegurar columnas esperadas (si faltan, las creamos)
    expected = [
        "Código Material",
        "Descripción",
        "Unidad",
        "Ubicación",
        "Stock sistema",
        "Stock contado",
        "Diferencia",
        "Estado",
    ]
    for c in expected:
        if c not in df.columns:
            df[c] = ""

    # Orden de columnas final
    df = df[expected]

    # Convertimos a valores seguros (para Excel)
    df["Código Material"] = df["Código Material"].astype(str).str.strip()
    df["Ubicación"] = df["Ubicación"].astype(str).str.strip().str.replace(" ", "").str.upper()
    df["Descripción"] = df["Descripción"].astype(str)
    df["Unidad"] = df["Unidad"].astype(str)

    # ------------------------------------------
    # Hoja 1: DISCREPANCIAS
    # ------------------------------------------
    ws = wb.active
    ws.title = "DISCREPANCIAS"

    # Título
    ws.merge_cells("A1:H1")
    ws["A1"] = "REPORTE DE DISCREPANCIAS DE INVENTARIO (MRO)"
    ws["A1"].font = Font(size=15, bold=True, color="0B1F3B")
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")

    ws.merge_cells("A2:H2")
    ws["A2"] = f"Generado: {datetime.now():%d/%m/%Y %H:%M}"
    ws["A2"].font = Font(size=10, italic=True, color="444444")
    ws["A2"].alignment = Alignment(horizontal="center")

    # Fila en blanco + headers
    ws.append([])
    ws.append(list(df.columns))

    header_row = 4
    header_fill = PatternFill("solid", fgColor="1F4E78")
    header_font = Font(bold=True, color="FFFFFF")
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for cell in ws[header_row]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center

    # Data rows
    for _, r in df.iterrows():
        ws.append([
            r["Código Material"],
            r["Descripción"],
            r["Unidad"],
            r["Ubicación"],
            r["Stock sistema"],
            r["Stock contado"],
            r["Diferencia"],
            r["Estado"],
        ])

    thin = Side(border_style="thin", color="1A1A1A")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    # Colores por estado
    colores = {
        "OK": "C6EFCE",
        "FALTA": "FFEB9C",
        "CRÍTICO": "FFC7CE",
        "SOBRA": "BDD7EE",
        "NO CONTADO": "D9D9D9",
    }

    for row in ws.iter_rows(min_row=header_row + 1, max_row=ws.max_row):
        estado = row[7].value
        fill = PatternFill("solid", fgColor=colores.get(str(estado).strip(), "FFFFFF"))

        for cell in row:
            cell.border = border
            cell.alignment = center
            if colores.get(str(estado).strip()):
                cell.fill = fill

    # Freeze + filter
    ws.freeze_panes = "A5"
    ws.auto_filter.ref = f"A4:H{ws.max_row}"

    # Auto widths + formato “pro”
    widths = {
        "A": 16,  # Código
        "B": 45,  # Descripción
        "C": 10,  # Unidad
        "D": 14,  # Ubicación
        "E": 14,  # Sistema
        "F": 14,  # Contado
        "G": 12,  # Diferencia
        "H": 12,  # Estado
    }
    for col, w in widths.items():
        ws.column_dimensions[col].width = w

    ws.row_dimensions[1].height = 26
    ws.row_dimensions[4].height = 20

    # ------------------------------------------
    # Hoja 2: RESUMEN
    # ------------------------------------------
    ws2 = wb.create_sheet("RESUMEN")

    ws2["A1"] = "RESUMEN EJECUTIVO"
    ws2["A1"].font = Font(size=14, bold=True, color="0B1F3B")

    total = len(df)
    ok = int((df["Estado"].astype(str).str.strip() == "OK").sum())
    falta = int((df["Estado"].astype(str).str.strip() == "FALTA").sum())
    crit = int((df["Estado"].astype(str).str.strip() == "CRÍTICO").sum())
    sobra = int((df["Estado"].astype(str).str.strip() == "SOBRA").sum())
    nocont = int((df["Estado"].astype(str).str.strip() == "NO CONTADO").sum())

    resumen = [
        ("Total materiales", total),
        ("OK", ok),
        ("FALTA", falta),
        ("CRÍTICO", crit),
        ("SOBRA", sobra),
        ("NO CONTADO", nocont),
    ]

    ws2.append([])
    start = 3
    for i, (k, v) in enumerate(resumen, start=start):
        ws2[f"A{i}"] = k
        ws2[f"B{i}"] = v
        ws2[f"A{i}"].font = Font(bold=True)
        ws2[f"A{i}"].alignment = Alignment(horizontal="left")
        ws2[f"B{i}"].alignment = Alignment(horizontal="center")

    ws2["A10"] = f"Generado: {datetime.now():%d/%m/%Y %H:%M}"
    ws2["A10"].font = Font(italic=True, color="444444")

    ws2.column_dimensions["A"].width = 26
    ws2.column_dimensions["B"].width = 14

    # Guardar
    wb.save(output)
    output.seek(0)
    return output
