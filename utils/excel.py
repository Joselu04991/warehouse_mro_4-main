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
# EXCEL PRO DE DISCREPANCIAS CON 3 COLORES
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

    # Asegurar que existan todas las columnas
    for c in columnas:
        if c not in df.columns:
            if "Stock" in c or c == "Diferencia":
                df[c] = 0
            elif c == "Estado":
                df[c] = ""

    # Asegurar que los valores sean numéricos para cálculos
    df["Stock sistema"] = pd.to_numeric(df["Stock sistema"], errors='coerce').fillna(0)
    df["Stock contado"] = pd.to_numeric(df["Stock contado"], errors='coerce').fillna(0)
    
    # Calcular diferencia para análisis interno
    df["Diferencia"] = df["Stock contado"] - df["Stock sistema"]
    
    # Estado automático
    def estado(row):
        stock_contado = row.get("Stock contado", 0)
        diferencia = row.get("Diferencia", 0)
        
        if stock_contado == 0:
            return "NO CONTADO"
        if diferencia == 0:
            return "OK"
        if diferencia < 0:
            return "FALTA" if abs(diferencia) < 5 else "CRÍTICO"
        return "SOBRA"

    df["Estado"] = df.apply(estado, axis=1)

    # =========================
    # ESTILOS Y COLORES (SOLO 3)
    # =========================
    header_fill = PatternFill("solid", fgColor="1F4E78")
    header_font = Font(bold=True, color="FFFFFF")
    title_font = Font(bold=True, size=14, color="FFFFFF")
    bold = Font(bold=True)

    center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    left = Alignment(horizontal="left", vertical="center")
    right = Alignment(horizontal="right", vertical="center")

    thin = Side(style="thin")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    # SOLO 3 COLORES PARA DIFERENCIAS:
    fill_falta_rojo = PatternFill("solid", fgColor="FFC7CE")  # ROJO si falta
    fill_exacto_verde = PatternFill("solid", fgColor="C6EFCE")  # VERDE si exacto
    fill_sobra_amarillo = PatternFill("solid", fgColor="FFEB9C")  # AMARILLO si sobra

    # COLORES PARA ESTADOS
    fill_ok = PatternFill("solid", fgColor="C6EFCE")
    fill_falta_estado = PatternFill("solid", fgColor="FFEB9C")
    fill_critico = PatternFill("solid", fgColor="FF9999")
    fill_sobra_estado = PatternFill("solid", fgColor="FFEB9C")  # Mismo amarillo
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

    for row in range(3, 5):
        ws0[f"A{row}"].font = bold

    total = len(df)
    ok = (df["Estado"] == "OK").sum()
    exactitud = round((ok / total) * 100, 2) if total else 0

    ws0["D3"] = "Total ítems:"
    ws0["E3"] = total
    ws0["D4"] = "Exactitud:"
    ws0["E4"] = f"{exactitud}%"

    for row in range(3, 5):
        ws0[f"D{row}"].font = bold

    # Resumen por Estado
    ws0["A6"] = "Resumen por Estado"
    ws0["A6"].font = Font(bold=True, size=12)

    ws0.append(["Estado", "Cantidad"])
    ws0["A7"].font = bold
    ws0["B7"].font = bold

    estados = ["OK", "FALTA", "CRÍTICO", "SOBRA", "NO CONTADO"]
    fila = 8
    for estado_lbl in estados:
        ws0[f"A{fila}"] = estado_lbl
        ws0[f"B{fila}"] = int((df["Estado"] == estado_lbl).sum())
        fila += 1

    # Leyenda de los 3 colores
    ws0["D6"] = "Colores de Diferencia:"
    ws0["D6"].font = Font(bold=True, size=12)
    ws0.merge_cells("D6:E6")
    
    fila_color = 7
    colores_info = [
        ("Diferencia < 0", "ROJO", "Falta"),
        ("Diferencia = 0", "VERDE", "Exacto"),
        ("Diferencia > 0", "AMARILLO", "Sobra"),
    ]
    
    for texto, color, significado in colores_info:
        ws0[f"D{fila_color}"] = texto
        ws0[f"E{fila_color}"] = color
        ws0[f"F{fila_color}"] = significado
        
        # Aplicar color de muestra
        if "ROJO" in color:
            ws0[f"E{fila_color}"].fill = fill_falta_rojo
        elif "VERDE" in color:
            ws0[f"E{fila_color}"].fill = fill_exacto_verde
        elif "AMARILLO" in color:
            ws0[f"E{fila_color}"].fill = fill_sobra_amarillo
            
        ws0[f"E{fila_color}"].font = bold
        ws0[f"E{fila_color}"].alignment = center
        fila_color += 1

    for col in range(1, 7):
        ws0.column_dimensions[get_column_letter(col)].width = 22

    # =========================
    # HOJA 2 – DETALLE CON FÓRMULA SIMPLE
    # =========================
    ws = wb.create_sheet("DISCREPANCIAS")
    
    # Escribir encabezados
    ws.append(columnas)

    # Escribir datos CON FÓRMULA =F-E
    for i, row in df.iterrows():
        row_data = []
        row_num = i + 2  # +2 porque la fila 1 es encabezado
        
        # Primeras 6 columnas con valores estáticos
        row_data.extend([
            row["Código Material"],
            row["Descripción"],
            row["Unidad"],
            row["Ubicación"],
            row["Stock sistema"],  # Columna E
            row["Stock contado"],   # Columna F
        ])
        
        # COLUMNA G: DIFERENCIA CON FÓRMULA =F-E
        row_data.append(f'=F{row_num}-E{row_num}')
        
        # COLUMNA H: Estado
        row_data.append(row["Estado"])
        
        ws.append(row_data)

    # Estilos para encabezados
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center
        cell.border = border

    # Ajustar anchos de columna
    widths = [20, 45, 10, 14, 16, 16, 16, 14]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    # Congelar paneles y agregar filtros
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    # =========================
    # APLICAR LOS 3 COLORES A LA COLUMNA DIFERENCIA (G)
    # =========================
    from openpyxl.formatting.rule import CellIsRule
    
    # 1. 🔴 ROJO: Diferencia NEGATIVA (< 0) - FALTA
    red_rule = CellIsRule(operator='lessThan', formula=['0'], 
                         fill=fill_falta_rojo)
    ws.conditional_formatting.add(f'G2:G{total+1}', red_rule)
    
    # 2. 🟢 VERDE: Diferencia CERO (= 0) - EXACTO
    green_rule = CellIsRule(operator='equal', formula=['0'], 
                           fill=fill_exacto_verde)
    ws.conditional_formatting.add(f'G2:G{total+1}', green_rule)
    
    # 3. 🟡 AMARILLO: Diferencia POSITIVA (> 0) - SOBRA
    yellow_rule = CellIsRule(operator='greaterThan', formula=['0'], 
                            fill=fill_sobra_amarillo)
    ws.conditional_formatting.add(f'G2:G{total+1}', yellow_rule)

    # =========================
    # APLICAR COLORES A LA COLUMNA ESTADO (H)
    # =========================
    from openpyxl.formatting.rule import FormulaRule
    
    # CRÍTICO - ROJO OSCURO
    critico_rule = FormulaRule(formula=['$H2="CRÍTICO"'], 
                              fill=PatternFill("solid", fgColor="FF9999"))
    ws.conditional_formatting.add(f'A2:H{total+1}', critico_rule)
    
    # FALTA - AMARILLO CLARO
    falta_estado_rule = FormulaRule(formula=['$H2="FALTA"'], 
                                   fill=PatternFill("solid", fgColor="FFEB9C"))
    ws.conditional_formatting.add(f'A2:H{total+1}', falta_estado_rule)
    
    # SOBRA - AMARILLO (mismo que falta)
    sobra_estado_rule = FormulaRule(formula=['$H2="SOBRA"'], 
                                   fill=fill_sobra_amarillo)
    ws.conditional_formatting.add(f'A2:H{total+1}', sobra_estado_rule)
    
    # NO CONTADO - GRIS
    nocont_rule = FormulaRule(formula=['$H2="NO CONTADO"'], 
                             fill=PatternFill("solid", fgColor="E7E6E6"))
    ws.conditional_formatting.add(f'A2:H{total+1}', nocont_rule)
    
    # OK - VERDE (mismo que exacto)
    ok_rule = FormulaRule(formula=['$H2="OK"'], 
                         fill=fill_exacto_verde)
    ws.conditional_formatting.add(f'A2:H{total+1}', ok_rule)

    # Aplicar bordes y alineaciones
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=8):
        for cell in row:
            cell.border = border
            
            # Alinear según tipo de dato
            if cell.column in [5, 6, 7]:  # Columnas E, F, G (números)
                cell.alignment = right
                if cell.column == 7:  # Columna G (Diferencia)
                    cell.number_format = '0'  # Formato número sin decimales
            elif cell.column in [1, 3, 4, 8]:  # Código, Unidad, Ubicación, Estado
                cell.alignment = center
            else:  # Descripción
                cell.alignment = left

    # =========================
    # HOJA 3 - FÓRMULA SIMPLE
    # =========================
    ws2 = wb.create_sheet("AYUDA")
    
    ws2["A1"] = "FÓRMULA DE DIFERENCIA"
    ws2.merge_cells("A1:C1")
    ws2["A1"].font = title_font
    ws2["A1"].fill = header_fill
    ws2["A1"].alignment = center

    ayuda = [
        ("", "", ""),
        ("FÓRMULA EN COLUMNA G:", "", ""),
        ("Diferencia =", "Stock contado - Stock sistema", ""),
        ("", "", ""),
        ("EN EXCEL:", "=F2 - E2", ""),
        ("", "", ""),
        ("COLORES AUTOMÁTICOS:", "", ""),
        ("🔴 ROJO", "Si Diferencia < 0", "(Falta material)"),
        ("🟢 VERDE", "Si Diferencia = 0", "(Exacto)"),
        ("🟡 AMARILLO", "Si Diferencia > 0", "(Sobra material)"),
        ("", "", ""),
        ("EJEMPLO PRÁCTICO:", "", ""),
        ("Stock sistema (E2):", "10", ""),
        ("Stock contado (F2):", "8", ""),
        ("Diferencia (G2):", "=F2-E2 = -2", "🔴 ROJO (Falta 2 unidades)"),
        ("", "", ""),
        ("Stock sistema (E3):", "10", ""),
        ("Stock contado (F3):", "10", ""),
        ("Diferencia (G3):", "=F3-E3 = 0", "🟢 VERDE (Exacto)"),
        ("", "", ""),
        ("Stock sistema (E4):", "10", ""),
        ("Stock contado (F4):", "15", ""),
        ("Diferencia (G4):", "=F4-E4 = 5", "🟡 AMARILLO (Sobra 5 unidades)"),
    ]

    fila_ayuda = 3
    for item in ayuda:
        ws2.append(item)
        if fila_ayuda == 3:  # Encabezados
            for col in range(1, 4):
                ws2.cell(row=fila_ayuda, column=col).font = bold
        fila_ayuda += 1

    # Resaltar las fórmulas
    for row in range(5, fila_ayuda):
        if "=F" in str(ws2[f"B{row}"].value):
            ws2[f"B{row}"].font = Font(color="0000FF", italic=True)
        if "🔴" in str(ws2[f"A{row}"].value):
            ws2[f"A{row}"].fill = fill_falta_rojo
            ws2[f"A{row}"].font = bold
        if "🟢" in str(ws2[f"A{row}"].value):
            ws2[f"A{row}"].fill = fill_exacto_verde
            ws2[f"A{row}"].font = bold
        if "🟡" in str(ws2[f"A{row}"].value):
            ws2[f"A{row}"].fill = fill_sobra_amarillo
            ws2[f"A{row}"].font = bold

    # Ajustar anchos
    ws2.column_dimensions['A'].width = 25
    ws2.column_dimensions['B'].width = 30
    ws2.column_dimensions['C'].width = 35

    # =========================
    # GUARDAR Y RETORNAR
    # =========================
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



