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
# EXCEL PRO DE DISCREPANCIAS CON FÓRMULAS EN TODO
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
    
    # Calcular diferencia para análisis interno (en Excel será fórmula)
    df["Diferencia"] = df["Stock contado"] - df["Stock sistema"]
    
    # Calcular estado para análisis interno (en Excel será fórmula)
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
    # ESTILOS Y COLORES
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

    # COLORES PARA ESTADOS (la fila completa cambiará de color)
    fill_ok = PatternFill("solid", fgColor="C6EFCE")  # VERDE para OK
    fill_falta = PatternFill("solid", fgColor="FFEB9C")  # AMARILLO para FALTA
    fill_critico = PatternFill("solid", fgColor="FFC7CE")  # ROJO para CRÍTICO
    fill_sobra = PatternFill("solid", fgColor="FFEB9C")  # AMARILLO para SOBRA (mismo que falta)
    fill_nocont = PatternFill("solid", fgColor="E7E6E6")  # GRIS para NO CONTADO

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

    # Usar fórmulas para que sea dinámico
    ws0["D3"] = "Total ítems:"
    ws0["E3"] = f'=COUNTA(DISCREPANCIAS!A:A)-1'  # -1 por el encabezado
    ws0["D4"] = "Exactitud:"
    ws0["E4"] = f'=COUNTIF(DISCREPANCIAS!H:H,"OK")/E3*100'
    ws0["E4"].number_format = '0.00"%"'

    for row in range(3, 5):
        ws0[f"D{row}"].font = bold

    # Resumen por Estado con fórmulas
    ws0["A6"] = "Resumen por Estado"
    ws0["A6"].font = Font(bold=True, size=12)

    ws0.append(["Estado", "Cantidad", "Fórmula"])
    for col in range(1, 4):
        ws0.cell(row=7, column=col).font = bold
        ws0.cell(row=7, column=col).fill = PatternFill("solid", fgColor="E0E0E0")

    estados = ["OK", "FALTA", "CRÍTICO", "SOBRA", "NO CONTADO"]
    fila = 8
    for estado_lbl in estados:
        ws0[f"A{fila}"] = estado_lbl
        ws0[f"B{fila}"] = f'=COUNTIF(DISCREPANCIAS!$H:$H, A{fila})'
        ws0[f"C{fila}"] = f'=COUNTIF(DISCREPANCIAS!H:H, "{estado_lbl}")'
        fila += 1

    # Leyenda de colores
    ws0["D6"] = "Colores por Estado:"
    ws0["D6"].font = Font(bold=True, size=12)
    ws0.merge_cells("D6:F6")
    
    fila_color = 7
    colores_info = [
        ("OK", "VERDE", "Coincidencia exacta"),
        ("FALTA", "AMARILLO", "Faltan menos de 5 unidades"),
        ("CRÍTICO", "ROJO", "Faltan 5 o más unidades"),
        ("SOBRA", "AMARILLO", "Sobra material"),
        ("NO CONTADO", "GRIS", "No se contó el material"),
    ]
    
    for estado_lbl, color, significado in colores_info:
        ws0[f"D{fila_color}"] = estado_lbl
        ws0[f"E{fila_color}"] = color
        ws0[f"F{fila_color}"] = significado
        
        # Aplicar color de muestra
        if estado_lbl == "OK":
            ws0[f"E{fila_color}"].fill = fill_ok
        elif estado_lbl == "FALTA":
            ws0[f"E{fila_color}"].fill = fill_falta
        elif estado_lbl == "CRÍTICO":
            ws0[f"E{fila_color}"].fill = fill_critico
        elif estado_lbl == "SOBRA":
            ws0[f"E{fila_color}"].fill = fill_sobra
        else:  # NO CONTADO
            ws0[f"E{fila_color}"].fill = fill_nocont
            
        ws0[f"E{fila_color}"].font = bold
        ws0[f"E{fila_color}"].alignment = center
        fila_color += 1

    for col in range(1, 7):
        ws0.column_dimensions[get_column_letter(col)].width = 22

    # =========================
    # HOJA 2 – DETALLE CON FÓRMULAS EN TODO
    # =========================
    ws = wb.create_sheet("DISCREPANCIAS")
    
    # Escribir encabezados
    ws.append(columnas)

    # Escribir datos CON FÓRMULAS EN DIFERENCIA Y ESTADO
    for i, row in df.iterrows():
        row_data = []
        row_num = i + 2  # +2 porque la fila 1 es encabezado
        
        # Primeras 6 columnas con valores estáticos
        row_data.extend([
            row["Código Material"],
            row["Descripción"],
            row["Unidad"],
            row["Ubicación"],
            row["Stock sistema"],  # Columna E - Valor inicial
            row["Stock contado"],   # Columna F - Valor inicial
        ])
        
        # COLUMNA G: DIFERENCIA CON FÓRMULA =F-E
        row_data.append(f'=F{row_num}-E{row_num}')
        
        # COLUMNA H: ESTADO CON FÓRMULA COMPLETA
        estado_formula = f'=IF(F{row_num}=0,"NO CONTADO",IF(G{row_num}=0,"OK",IF(G{row_num}<0,IF(ABS(G{row_num})<5,"FALTA","CRÍTICO"),"SOBRA")))'
        row_data.append(estado_formula)
        
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
    # APLICAR COLORES A LA FILA COMPLETA SEGÚN ESTADO
    # =========================
    from openpyxl.formatting.rule import FormulaRule
    
    # 1. VERDE para OK
    ok_rule = FormulaRule(formula=['$H2="OK"'], 
                         fill=fill_ok)
    ws.conditional_formatting.add(f'A2:H{total+1}', ok_rule)
    
    # 2. AMARILLO para FALTA
    falta_rule = FormulaRule(formula=['$H2="FALTA"'], 
                           fill=fill_falta)
    ws.conditional_formatting.add(f'A2:H{total+1}', falta_rule)
    
    # 3. ROJO para CRÍTICO
    critico_rule = FormulaRule(formula=['$H2="CRÍTICO"'], 
                              fill=fill_critico)
    ws.conditional_formatting.add(f'A2:H{total+1}', critico_rule)
    
    # 4. AMARILLO para SOBRA
    sobra_rule = FormulaRule(formula=['$H2="SOBRA"'], 
                            fill=fill_sobra)
    ws.conditional_formatting.add(f'A2:H{total+1}', sobra_rule)
    
    # 5. GRIS para NO CONTADO
    nocont_rule = FormulaRule(formula=['$H2="NO CONTADO"'], 
                             fill=fill_nocont)
    ws.conditional_formatting.add(f'A2:H{total+1}', nocont_rule)

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
    # HOJA 3 - CÓMO FUNCIONA
    # =========================
    ws2 = wb.create_sheet("INSTRUCCIONES")
    
    ws2["A1"] = "CÓMO FUNCIONA - FÓRMULAS AUTOMÁTICAS"
    ws2.merge_cells("A1:D1")
    ws2["A1"].font = title_font
    ws2["A1"].fill = header_fill
    ws2["A1"].alignment = center

    instrucciones = [
        ("PASO", "QUÉ HACER", "QUÉ PASA", "EJEMPLO"),
        ("1", "Modificar Stock sistema (Col E)", "Se recalcula Diferencia automáticamente", "Si E2=10 y F2=8 → G2=8-10=-2"),
        ("2", "Modificar Stock contado (Col F)", "Se recalcula Diferencia automáticamente", "Si E2=10 y F2=15 → G2=15-10=5"),
        ("3", "Ver Diferencia (Col G)", "Fórmula: =F2-E2 (automática)", "Se actualiza SOLO al cambiar E o F"),
        ("4", "Ver Estado (Col H)", "Fórmula evalúa y clasifica automáticamente", "Si G2=-2 → 'FALTA' (amarillo)"),
        ("5", "Ver Color fila", "Color cambia según Estado (automático)", "OK=Verde, FALTA=Amarillo, CRÍTICO=Rojo"),
        ("", "", "", ""),
        ("FÓRMULA DE ESTADO:", "", "", ""),
        ("", '=IF(F2=0,"NO CONTADO",', "Si no se contó", ""),
        ("", 'IF(G2=0,"OK",', "Si es exacto", ""),
        ("", 'IF(G2<0,', "Si falta", ""),
        ("", 'IF(ABS(G2)<5,"FALTA","CRÍTICO"),', "Si falta poco o mucho", ""),
        ("", '"SOBRA")))', "Si sobra", ""),
        ("", "", "", ""),
        ("EJEMPLO COMPLETO:", "", "", ""),
        ("Stock sistema:", "10", "Valor modificable", ""),
        ("Stock contado:", "13", "Valor modificable", ""),
        ("Diferencia:", "=13-10 = 3", "Calculado automático", ""),
        ("Estado:", "SOBRA", "Calculado automático", ""),
        ("Color fila:", "AMARILLO", "Cambia automático", ""),
    ]

    fila_inst = 3
    for inst in instrucciones:
        ws2.append(inst)
        if fila_inst == 3:  # Encabezados
            for col in range(1, 5):
                ws2.cell(row=fila_inst, column=col).font = bold
                ws2.cell(row=fila_inst, column=col).fill = PatternFill("solid", fgColor="E0E0E0")
        fila_inst += 1

    # Resaltar fórmulas importantes
    for row in range(4, fila_inst):
        if "=F2-E2" in str(ws2[f"C{row}"].value) or "=IF(" in str(ws2[f"B{row}"].value):
            ws2[f"C{row}"].font = Font(color="0000FF", italic=True)
            ws2[f"B{row}"].font = Font(color="0000FF", italic=True)
        
        # Aplicar colores de ejemplo
        if "VERDE" in str(ws2[f"D{row}"].value):
            ws2[f"D{row}"].fill = fill_ok
        elif "AMARILLO" in str(ws2[f"D{row}"].value):
            ws2[f"D{row}"].fill = fill_falta
        elif "ROJO" in str(ws2[f"D{row}"].value):
            ws2[f"D{row}"].fill = fill_critico

    # Ajustar anchos
    for col, width in zip(["A", "B", "C", "D"], [15, 35, 40, 20]):
        ws2.column_dimensions[col].width = width

    # =========================
    # AGREGAR VALIDACIÓN DE DATOS
    # =========================
    # Añadir validación para que solo se ingresen números en E y F
    from openpyxl.worksheet.datavalidation import DataValidation
    
    # Validación para números positivos (opcional)
    dv = DataValidation(type="decimal", 
                       operator="greaterThanOrEqual", 
                       formula1=["0"],
                       showErrorMessage=True,
                       errorTitle="Valor inválido",
                       error="Ingrese un número mayor o igual a 0")
    
    # Aplicar validación a columnas E y F (Stock sistema y Stock contado)
    dv_range = f"E2:F{total+1}"
    dv.add(dv_range)
    ws.add_data_validation(dv)

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




