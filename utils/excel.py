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
# EXCEL PRO CON FÓRMULA DE DIFERENCIA DIRECTAMENTE
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
    
    # Calcular estado
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

    # COLORES PARA ESTADOS
    fill_ok = PatternFill("solid", fgColor="C6EFCE")  # VERDE para OK
    fill_falta = PatternFill("solid", fgColor="FFEB9C")  # AMARILLO para FALTA
    fill_critico = PatternFill("solid", fgColor="FFC7CE")  # ROJO para CRÍTICO
    fill_sobra = PatternFill("solid", fgColor="FFEB9C")  # AMARILLO para SOBRA
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
    # HOJA 2 – DETALLE CON FÓRMULA DE DIFERENCIA
    # =========================
    ws = wb.create_sheet("DISCREPANCIAS")
    
    # Escribir encabezados
    ws.append(columnas)

    # Escribir datos con FÓRMULA EN DIFERENCIA
    for i, row in df.iterrows():
        row_num = i + 2  # +2 porque la fila 1 es encabezado
        
        # Poner los valores directamente con fórmula en Diferencia
        ws.append([
            row["Código Material"],
            row["Descripción"],
            row["Unidad"],
            row["Ubicación"],
            row["Stock sistema"],  # Columna E - Valor
            row["Stock contado"],   # Columna F - Valor
            f'=F{row_num}-E{row_num}',  # Columna G - FÓRMULA DE DIFERENCIA
            row["Estado"],          # Columna H - Valor calculado
        ])

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
    # APLICAR COLORES A LAS FILAS SEGÚN ESTADO
    # =========================
    # Aplicar colores basados en el estado actual
    for row_idx, row in enumerate(ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=8), start=2):
        estado_celda = ws[f"H{row_idx}"].value  # Estado en columna H
        
        if estado_celda == "OK":
            fill = fill_ok
        elif estado_celda == "FALTA":
            fill = fill_falta
        elif estado_celda == "CRÍTICO":
            fill = fill_critico
        elif estado_celda == "SOBRA":
            fill = fill_sobra
        elif estado_celda == "NO CONTADO":
            fill = fill_nocont
        else:
            fill = None
        
        # Aplicar color a toda la fila
        if fill:
            for cell in row:
                cell.fill = fill
                cell.border = border
                
                # Alinear según tipo de dato
                if cell.column in [5, 6, 7]:  # Columnas E, F, G (números)
                    cell.alignment = right
                    if cell.column == 7:  # Columna G (Diferencia con fórmula)
                        # Resaltar diferencias basado en el valor calculado
                        dif_calculada = row[6].value  # Ya es la fórmula
                        # Si queremos resaltar, podemos hacerlo con formato condicional manual
                        pass
                        cell.number_format = '0'  # Formato número sin decimales
                elif cell.column in [1, 3, 4, 8]:  # Código, Unidad, Ubicación, Estado
                    cell.alignment = center
                else:  # Descripción
                    cell.alignment = left

    # =========================
    # HOJA 3 - FÓRMULA DE ESTADO PARA COPIAR
    # =========================
    ws2 = wb.create_sheet("FÓRMULA_ESTADO")
    
    ws2["A1"] = "FÓRMULA PARA COLUMNA ESTADO"
    ws2.merge_cells("A1:D1")
    ws2["A1"].font = title_font
    ws2["A1"].fill = header_fill
    ws2["A1"].alignment = center

    # Instrucciones para agregar fórmula de estado
    instrucciones = [
        ("PARA HACER DINÁMICO:", "", "", ""),
        ("1", "Insertar nueva columna", "Después de Diferencia", "Columna I"),
        ("2", "Copiar esta fórmula:", '=IF(F2=0,"NO CONTADO",IF(G2=0,"OK",IF(G2<0,IF(ABS(G2)<5,"FALTA","CRÍTICO"),"SOBRA")))', ""),
        ("3", "Pegar en celda I2", "", ""),
        ("4", "Arrastrar hacia abajo", "Click en esquina inferior derecha", ""),
        ("", "", "", ""),
        ("FÓRMULA COMPLETA:", "", "", ""),
        ("Estado =", 'IF(F2=0,', "Si no se contó", ""),
        ("", '"NO CONTADO",', "", ""),
        ("", 'IF(G2=0,', "Si diferencia es 0", ""),
        ("", '"OK",', "", ""),
        ("", 'IF(G2<0,', "Si diferencia negativa", ""),
        ("", 'IF(ABS(G2)<5,', "Si falta menos de 5", ""),
        ("", '"FALTA",', "", ""),
        ("", '"CRÍTICO"),', "Si falta 5 o más", ""),
        ("", '"SOBRA")))', "Si diferencia positiva", ""),
        ("", "", "", ""),
        ("EJEMPLO:", "", "", ""),
        ("Si E2=10, F2=8", "G2 = 8-10 = -2", "I2 = FALTA", "Color AMARILLO"),
        ("Si E2=10, F2=10", "G2 = 10-10 = 0", "I2 = OK", "Color VERDE"),
        ("Si E2=10, F2=5", "G2 = 5-10 = -5", "I2 = CRÍTICO", "Color ROJO"),
        ("Si E2=10, F2=15", "G2 = 15-10 = 5", "I2 = SOBRA", "Color AMARILLO"),
        ("Si E2=10, F2=0", "G2 = 0-10 = -10", "I2 = NO CONTADO", "Color GRIS"),
    ]

    fila_inst = 3
    for inst in instrucciones:
        ws2.append(inst)
        if fila_inst == 3:  # Encabezados
            for col in range(1, 5):
                ws2.cell(row=fila_inst, column=col).font = bold
                ws2.cell(row=fila_inst, column=col).fill = PatternFill("solid", fgColor="E0E0E0")
        fila_inst += 1

    # Resaltar la fórmula principal
    for row in range(5, 20):
        if 'IF(F2=0,"NO CONTADO"' in str(ws2[f"B{row}"].value):
            ws2[f"B{row}"].font = Font(color="0000FF", bold=True, size=11)
            ws2[f"B{row}"].fill = PatternFill("solid", fgColor="FFFFCC")

    # Mostrar cómo aplicar formatos condicionales
    fila_format = fila_inst + 2
    ws2[f"A{fila_format}"] = "APLICAR COLORES AUTOMÁTICOS:"
    ws2[f"A{fila_format}"].font = Font(bold=True, size=12, color="1F4E78")
    ws2.merge_cells(f"A{fila_format}:D{fila_format}")
    
    fila_format += 1
    formatos = [
        ("1", "Seleccionar columnas A:H", "", ""),
        ("2", "Home → Conditional Formatting → New Rule", "", ""),
        ("3", "Seleccionar 'Use a formula...'", "", ""),
        ("4", "Para VERDE (OK):", '=$H2="OK"', ""),
        ("5", "Para AMARILLO (FALTA):", '=$H2="FALTA"', ""),
        ("6", "Para ROJO (CRÍTICO):", '=$H2="CRÍTICO"', ""),
        ("7", "Para AMARILLO (SOBRA):", '=$H2="SOBRA"', ""),
        ("8", "Para GRIS (NO CONTADO):", '=$H2="NO CONTADO"', ""),
    ]
    
    for fmt in formatos:
        ws2.append(fmt)
        fila_format += 1

    # Ajustar anchos
    for col, width in zip(["A", "B", "C", "D"], [15, 50, 25, 20]):
        ws2.column_dimensions[col].width = width

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





