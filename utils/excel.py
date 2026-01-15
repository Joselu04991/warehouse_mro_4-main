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
# EXCEL PRO DE DISCREPANCIAS CON FUNCIONES INTERACTIVAS
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
        "Observaciones",
        "Acción requerida",
        "Prioridad",
    ]

    for c in columnas:
        if c not in df.columns:
            if "Stock" in c or c == "Diferencia":
                df[c] = 0
            elif c in ["Observaciones", "Acción requerida"]:
                df[c] = ""
            elif c == "Prioridad":
                df[c] = "MEDIA"

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

    # Asignar prioridad automática
    def asignar_prioridad(row):
        if row["Estado"] == "CRÍTICO":
            return "ALTA"
        elif row["Estado"] == "FALTA":
            return "MEDIA"
        elif row["Estado"] == "SOBRA":
            return "BAJA"
        elif row["Estado"] == "NO CONTADO":
            return "ALTA"
        return "BAJA"

    df["Prioridad"] = df.apply(asignar_prioridad, axis=1)

    # Ordenar por prioridad y diferencia
    df = df.sort_values(by=["Prioridad", "Diferencia"], ascending=[True, True])

    # =========================
    # ESTILOS
    # =========================
    header_fill = PatternFill("solid", fgColor="1F4E78")
    header_font = Font(bold=True, color="FFFFFF")
    title_font = Font(bold=True, size=14, color="FFFFFF")
    bold = Font(bold=True)
    italic = Font(italic=True)

    center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    left = Alignment(horizontal="left", vertical="center")

    thin = Side(style="thin")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    # Colores para estados
    fill_ok = PatternFill("solid", fgColor="C6EFCE")
    fill_falta = PatternFill("solid", fgColor="FFEB9C")
    fill_critico = PatternFill("solid", fgColor="FFC7CE")
    fill_sobra = PatternFill("solid", fgColor="BFEFFF")
    fill_nocont = PatternFill("solid", fgColor="E7E6E6")
    
    # Colores para prioridad
    fill_alta = PatternFill("solid", fgColor="FF6666")
    fill_media = PatternFill("solid", fgColor="FFFF99")
    fill_baja = PatternFill("solid", fgColor="99CCFF")

    # =========================
    # HOJA 1 – INSTRUCCIONES Y RESUMEN
    # =========================
    ws0 = wb.active
    ws0.title = "INSTRUCCIONES"

    # Título principal
    ws0["A1"] = "REPORTE DE DISCREPANCIAS – WAREHOUSE MRO"
    ws0.merge_cells("A1:K1")
    ws0["A1"].font = title_font
    ws0["A1"].fill = header_fill
    ws0["A1"].alignment = center

    # Información de generación
    generado_por = (meta or {}).get("generado_por", "Sistema MRO")
    generado_en = (meta or {}).get(
        "generado_en",
        datetime.now().strftime("%Y-%m-%d %H:%M")
    )

    ws0["A3"] = "Generado por:"
    ws0["B3"] = generado_por
    ws0["A4"] = "Fecha generación:"
    ws0["B4"] = generado_en
    ws0["A5"] = "Hoja de datos:"
    ws0["B5"] = "Ver hoja 'DETALLE' para información completa"

    for row in range(3, 6):
        ws0[f"A{row}"].font = bold

    # Instrucciones para usar el Excel
    ws0["A7"] = "INSTRUCCIONES DE USO:"
    ws0["A7"].font = Font(bold=True, size=12, color="1F4E78")
    
    instrucciones = [
        ("Filtrar datos:", "Usar Autofiltro en los encabezados de la hoja 'DETALDE'"),
        ("Ordenar:", "Click en encabezados para ordenar ascendente/descendente"),
        ("Resumen rápido:", "Ver hoja 'RESUMEN' para métricas clave"),
        ("Prioridades:", "ALTA=Urgente, MEDIA=Planificar, BAJA=Monitorear"),
        ("Actualizar:", "Modificar columnas 'Observaciones' y 'Acción requerida'"),
        ("Estados:", "OK=Correcto, FALTA=Diferencia <5, CRÍTICO=Diferencia ≥5"),
        ("Exportar filtros:", "Copiar filas visibles después de filtrar"),
    ]
    
    fila = 8
    for titulo, desc in instrucciones:
        ws0[f"A{fila}"] = titulo
        ws0[f"B{fila}"] = desc
        ws0[f"A{fila}"].font = bold
        ws0[f"B{fila}"].font = italic
        fila += 1

    # Atajos útiles
    fila += 1
    ws0[f"A{fila}"] = "ATAJOS EXCEL:"
    ws0[f"A{fila}"].font = Font(bold=True, size=11, color="FF0000")
    fila += 1
    
    atajos = [
        ("Ctrl+Shift+L", "Activar/Desactivar filtros"),
        ("Alt+D+F+F", "Aplicar filtro avanzado"),
        ("Ctrl+T", "Crear tabla dinámica"),
        ("Ctrl+Shift+Arrow", "Seleccionar rango de datos"),
        ("Alt+F1", "Crear gráfico rápido"),
    ]
    
    for atajo, funcion in atajos:
        ws0[f"A{fila}"] = atajo
        ws0[f"B{fila}"] = funcion
        ws0[f"A{fila}"].font = Font(bold=True, color="0000FF")
        fila += 1

    # =========================
    # HOJA 2 – RESUMEN ESTADÍSTICO
    # =========================
    ws1 = wb.create_sheet("RESUMEN")
    
    # Encabezado resumen
    ws1["A1"] = "RESUMEN ESTADÍSTICO"
    ws1.merge_cells("A1:D1")
    ws1["A1"].font = title_font
    ws1["A1"].fill = header_fill
    ws1["A1"].alignment = center

    # Métricas básicas
    total = len(df)
    ok = (df["Estado"] == "OK").sum()
    exactitud = round((ok / total) * 100, 2) if total else 0
    total_diferencia = df["Diferencia"].sum()
    items_criticos = (df["Estado"] == "CRÍTICO").sum()
    items_nocontados = (df["Estado"] == "NO CONTADO").sum()

    metricas = [
        ("Total ítems:", total),
        ("Exactitud inventario:", f"{exactitud}%"),
        ("Diferencia total:", total_diferencia),
        ("Ítems CRÍTICOS:", items_criticos),
        ("Ítems NO CONTADOS:", items_nocontados),
        ("Ítems OK:", ok),
        ("Ítems con FALTANTE:", (df["Estado"] == "FALTA").sum()),
        ("Ítems con SOBRA:", (df["Estado"] == "SOBRA").sum()),
    ]

    fila_res = 3
    for label, valor in metricas:
        ws1[f"A{fila_res}"] = label
        ws1[f"B{fila_res}"] = valor
        ws1[f"A{fila_res}"].font = bold
        fila_res += 1

    # Resumen por Estado
    fila_res += 1
    ws1[f"A{fila_res}"] = "RESUMEN POR ESTADO"
    ws1[f"A{fila_res}"].font = Font(bold=True, size=12, color="1F4E78")
    ws1.merge_cells(f"A{fila_res}:C{fila_res}")
    
    fila_res += 1
    ws1[f"A{fila_res}"] = "Estado"
    ws1[f"B{fila_res}"] = "Cantidad"
    ws1[f"C{fila_res}"] = "Porcentaje"
    for col in ["A", "B", "C"]:
        ws1[f"{col}{fila_res}"].font = bold
        ws1[f"{col}{fila_res}"].fill = PatternFill("solid", fgColor="E0E0E0")
    
    estados = ["OK", "FALTA", "CRÍTICO", "SOBRA", "NO CONTADO"]
    fila_res += 1
    for estado_lbl in estados:
        cantidad = int((df["Estado"] == estado_lbl).sum())
        porcentaje = round((cantidad / total) * 100, 2) if total else 0
        
        ws1[f"A{fila_res}"] = estado_lbl
        ws1[f"B{fila_res}"] = cantidad
        ws1[f"C{fila_res}"] = f"{porcentaje}%"
        
        # Color según estado
        if estado_lbl == "OK":
            fill = fill_ok
        elif estado_lbl == "FALTA":
            fill = fill_falta
        elif estado_lbl == "CRÍTICO":
            fill = fill_critico
        elif estado_lbl == "SOBRA":
            fill = fill_sobra
        else:
            fill = fill_nocont
            
        for col in ["A", "B", "C"]:
            ws1[f"{col}{fila_res}"].fill = fill
        
        fila_res += 1

    # Resumen por Prioridad
    fila_res += 1
    ws1[f"A{fila_res}"] = "RESUMEN POR PRIORIDAD"
    ws1[f"A{fila_res}"].font = Font(bold=True, size=12, color="1F4E78")
    ws1.merge_cells(f"A{fila_res}:C{fila_res}")
    
    fila_res += 1
    ws1[f"A{fila_res}"] = "Prioridad"
    ws1[f"B{fila_res}"] = "Cantidad"
    ws1[f"C{fila_res}"] = "Porcentaje"
    for col in ["A", "B", "C"]:
        ws1[f"{col}{fila_res}"].font = bold
        ws1[f"{col}{fila_res}"].fill = PatternFill("solid", fgColor="E0E0E0")
    
    prioridades = ["ALTA", "MEDIA", "BAJA"]
    fila_res += 1
    for prioridad in prioridades:
        cantidad = int((df["Prioridad"] == prioridad).sum())
        porcentaje = round((cantidad / total) * 100, 2) if total else 0
        
        ws1[f"A{fila_res}"] = prioridad
        ws1[f"B{fila_res}"] = cantidad
        ws1[f"C{fila_res}"] = f"{porcentaje}%"
        
        # Color según prioridad
        if prioridad == "ALTA":
            fill = fill_alta
        elif prioridad == "MEDIA":
            fill = fill_media
        else:
            fill = fill_baja
            
        for col in ["A", "B", "C"]:
            ws1[f"{col}{fila_res}"].fill = fill
        
        fila_res += 1

    # Ajustar anchos de columna
    for col in ["A", "B", "C", "D"]:
        ws1.column_dimensions[col].width = 25

    # =========================
    # HOJA 3 – DETALLE COMPLETO
    # =========================
    ws = wb.create_sheet("DETALLE")
    
    # Escribir encabezados
    ws.append(columnas)
    
    # Escribir datos
    for r in df.itertuples(index=False):
        ws.append(list(r))

    # Estilos para encabezados
    for cell in ws[1]:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = center
        cell.border = border

    # Ajustar anchos de columna
    widths = [18, 40, 10, 12, 14, 14, 12, 12, 25, 25, 12]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    # Congelar paneles y agregar filtros
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    # Aplicar estilos a los datos
    for row in ws.iter_rows(min_row=2, max_row=ws.max_row):
        estado_val = str(row[7].value)  # Columna Estado
        prioridad_val = str(row[10].value)  # Columna Prioridad (índice 10)

        # Color según estado
        if estado_val == "CRÍTICO":
            estado_fill = fill_critico
        elif estado_val == "FALTA":
            estado_fill = fill_falta
        elif estado_val == "SOBRA":
            estado_fill = fill_sobra
        elif estado_val == "NO CONTADO":
            estado_fill = fill_nocont
        else:
            estado_fill = fill_ok

        # Color según prioridad
        if prioridad_val == "ALTA":
            prioridad_fill = fill_alta
        elif prioridad_val == "MEDIA":
            prioridad_fill = fill_media
        else:
            prioridad_fill = fill_baja

        # Aplicar colores a celdas específicas
        for idx, cell in enumerate(row, start=1):
            cell.border = border
            cell.alignment = center if idx <= 8 else left  # Primeras 8 columnas centradas, resto izquierda
            
            # Estado colorea toda la fila
            if idx <= 10:  # No aplicar a Prioridad
                cell.fill = estado_fill
            
            # Prioridad solo colorea su propia celda
            if idx == 11:  # Columna Prioridad
                cell.fill = prioridad_fill
                cell.font = Font(bold=True)

        # Formato condicional para diferencias
        dif_cell = row[6]  # Columna Diferencia
        if dif_cell.value is not None:
            try:
                dif_val = float(dif_cell.value)
                if dif_val < 0:
                    dif_cell.font = Font(color="FF0000", bold=True)  # Rojo para negativo
                elif dif_val > 0:
                    dif_cell.font = Font(color="00B050", bold=True)  # Verde para positivo
            except:
                pass

    # =========================
    # HOJA 4 – FILTROS RÁPIDOS
    # =========================
    ws2 = wb.create_sheet("FILTROS_RAPIDOS")
    
    ws2["A1"] = "FILTROS RÁPIDOS PRE-CONFIGURADOS"
    ws2.merge_cells("A1:D1")
    ws2["A1"].font = title_font
    ws2["A1"].fill = header_fill
    ws2["A1"].alignment = center

    instrucciones_filtros = [
        ("Para usar:", "Copiar las fórmulas a la hoja 'DETALLE' en una nueva columna"),
        ("Filtrar por:", "Luego filtrar por TRUE en la nueva columna"),
    ]
    
    fila_filtro = 3
    for titulo, desc in instrucciones_filtros:
        ws2[f"A{fila_filtro}"] = titulo
        ws2[f"B{fila_filtro}"] = desc
        ws2[f"A{fila_filtro}"].font = bold
        ws2[f"B{fila_filtro}"].font = italic
        ws2.merge_cells(f"B{fila_filtro}:D{fila_filtro}")
        fila_filtro += 1

    fila_filtro += 1
    ws2[f"A{fila_filtro}"] = "Tipo de Filtro"
    ws2[f"B{fila_filtro}"] = "Fórmula a usar"
    ws2[f"C{fila_filtro}"] = "Descripción"
    ws2[f"D{fila_filtro}"] = "Cantidad"
    
    for col in ["A", "B", "C", "D"]:
        ws2[f"{col}{fila_filtro}"].font = bold
        ws2[f"{col}{fila_filtro}"].fill = PatternFill("solid", fgColor="E0E0E0")

    filtros = [
        (
            "CRÍTICOS URGENTES",
            '=AND($H2="CRÍTICO", $K2="ALTA")',
            "Items críticos con prioridad alta",
            items_criticos
        ),
        (
            "NO CONTADOS",
            '=$H2="NO CONTADO"',
            "Items que no fueron contados",
            items_nocontados
        ),
        (
            "FALTANTES SIGNIFICATIVOS",
            '=AND($G2<-10, $H2="CRÍTICO")',
            "Faltantes mayores a 10 unidades",
            (df["Diferencia"] < -10).sum()
        ),
        (
            "SOBRAS IMPORTANTES",
            '=AND($G2>20, $H2="SOBRA")',
            "Sobras mayores a 20 unidades",
            (df["Diferencia"] > 20).sum()
        ),
        (
            "UBICACIONES ESPECÍFICAS",
            '=OR(LEFT($D2,1)="E", LEFT($D2,2)="A1")',
            "Ubicaciones que comienzan con E o A1",
            df["Ubicación"].str.startswith(("E", "A1")).sum()
        ),
    ]

    fila_filtro += 1
    for nombre, formula, desc, cantidad in filtros:
        ws2[f"A{fila_filtro}"] = nombre
        ws2[f"B{fila_filtro}"] = formula
        ws2[f"C{fila_filtro}"] = desc
        ws2[f"D{fila_filtro}"] = cantidad
        
        # Color alternado para filas
        if fila_filtro % 2 == 0:
            fill = PatternFill("solid", fgColor="F2F2F2")
        else:
            fill = PatternFill("solid", fgColor="FFFFFF")
            
        for col in ["A", "B", "C", "D"]:
            ws2[f"{col}{fila_filtro}"].fill = fill
            ws2[f"{col}{fila_filtro}"].border = border
        
        fila_filtro += 1

    # Ajustar anchos
    for col, width in zip(["A", "B", "C", "D"], [25, 50, 40, 15]):
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


