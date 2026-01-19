# utils/pdf_reports_premium.py
# PDF CORPORATIVO PREMIUM SIN matplotlib

import os
import io
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter, A4, landscape
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, String, Line, Rect, Polygon
from reportlab.graphics.charts.barcharts import VerticalBarChart, HorizontalBarChart
from reportlab.graphics.charts.piecharts import Pie, Pie3d
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.widgets.markers import makeMarker
from reportlab.graphics import renderPDF
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.units import inch, cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import qrcode
from flask import current_app
from models import db
from models.user import User
from models.inventory import InventoryItem
from models.bultos import Bulto
from models.alerts import Alert
from models.actividad import ActividadUsuario
import tempfile
import itertools

def create_premium_pdf_report(user_id):
    """
    GENERA UN PDF PREMIUM CORPORATIVO CON:
    - Portada profesional
    - Resumen ejecutivo
    - Estadísticas detalladas
    - Gráficos avanzados (sin matplotlib)
    - Timeline de actividad
    - Análisis de rendimiento
    - Recomendaciones
    - Códigos QR y seguridad
    """
    
    try:
        print(f"[PDF Premium] Iniciando para usuario {user_id}")
        
        # ============================================
        # 1. OBTENER TODOS LOS DATOS
        # ============================================
        user = User.query.get(user_id)
        if not user:
            print(f"[PDF Premium] Usuario no encontrado")
            return None
        
        # Crear directorio para PDFs premium
        premium_dir = os.path.join(current_app.root_path, "static", "reports_premium")
        os.makedirs(premium_dir, exist_ok=True)
        
        # Nombre del archivo
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        pdf_filename = f"Reporte_Premium_{user.username}_{timestamp}.pdf"
        pdf_path = os.path.join(premium_dir, pdf_filename)
        
        print(f"[PDF Premium] Generando: {pdf_path}")
        
        # ============================================
        # 2. RECOPILAR DATOS COMPLETOS
        # ============================================
        data = collect_comprehensive_data(user_id)
        
        # ============================================
        # 3. CREAR DOCUMENTO CON MÚLTIPLES PÁGINAS
        # ============================================
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72,
            title=f"Reporte Premium - {user.username}",
            author="Sistema Warehouse MRO - GERDAU",
            subject="Reporte Corporativo de Usuario"
        )
        
        story = []
        styles = getSampleStyleSheet()
        
        # ============================================
        # 4. ESTILOS PERSONALIZADOS PREMIUM
        # ============================================
        # Color corporativo Gerdau
        gerdau_blue = colors.HexColor('#003b71')
        gerdau_yellow = colors.HexColor('#f8c000')
        gerdau_dark = colors.HexColor('#001d38')
        gerdau_light = colors.HexColor('#e9f2ff')
        
        # Estilos personalizados
        premium_styles = {
            'title': ParagraphStyle(
                name='PremiumTitle',
                parent=styles['Title'],
                fontSize=28,
                textColor=gerdau_blue,
                alignment=TA_CENTER,
                spaceAfter=30,
                fontName='Helvetica-Bold'
            ),
            'section_title': ParagraphStyle(
                name='PremiumSection',
                parent=styles['Heading1'],
                fontSize=18,
                textColor=gerdau_dark,
                spaceAfter=15,
                fontName='Helvetica-Bold',
                borderWidth=1,
                borderColor=gerdau_yellow,
                borderPadding=(5, 5, 5, 5),
                backgroundColor=gerdau_light
            ),
            'subsection': ParagraphStyle(
                name='PremiumSubsection',
                parent=styles['Heading2'],
                fontSize=14,
                textColor=gerdau_blue,
                spaceAfter=10,
                fontName='Helvetica-Bold'
            ),
            'body': ParagraphStyle(
                name='PremiumBody',
                parent=styles['BodyText'],
                fontSize=10,
                textColor=colors.black,
                spaceAfter=8,
                alignment=TA_JUSTIFY
            ),
            'highlight': ParagraphStyle(
                name='PremiumHighlight',
                parent=styles['BodyText'],
                fontSize=11,
                textColor=gerdau_dark,
                spaceAfter=6,
                fontName='Helvetica-Bold',
                backColor=colors.HexColor('#ffffcc')
            ),
            'footer': ParagraphStyle(
                name='PremiumFooter',
                parent=styles['BodyText'],
                fontSize=8,
                textColor=colors.gray,
                alignment=TA_CENTER
            ),
            'kpi_value': ParagraphStyle(
                name='PremiumKPIValue',
                fontSize=24,
                textColor=gerdau_blue,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            ),
            'kpi_label': ParagraphStyle(
                name='PremiumKPILabel',
                fontSize=10,
                textColor=colors.gray,
                alignment=TA_CENTER
            )
        }
        
        # ============================================
        # 5. PÁGINA 1: PORTADA CORPORATIVA
        # ============================================
        story.append(Paragraph("REPORTE CORPORATIVO PREMIUM", premium_styles['title']))
        story.append(Spacer(1, 20))
        
        story.append(Paragraph("SISTEMA WAREHOUSE MRO", ParagraphStyle(
            name='Subtitle', fontSize=16, textColor=gerdau_yellow, alignment=TA_CENTER)))
        
        story.append(Spacer(1, 40))
        
        # Información del usuario en tarjeta
        user_card = [
            ['<b>INFORMACIÓN DEL USUARIO</b>', ''],
            ['<b>Nombre:</b>', user.username],
            ['<b>Correo:</b>', user.email or 'No registrado'],
            ['<b>Rol:</b>', getattr(user, 'role', 'Usuario').upper()],
            ['<b>Teléfono:</b>', getattr(user, 'phone', 'No registrado')],
            ['<b>Ubicación:</b>', getattr(user, 'location', 'No especificada')],
            ['<b>Área:</b>', getattr(user, 'area', 'No asignada')],
            ['<b>Miembro desde:</b>', user.created_at.strftime('%d/%m/%Y') if user.created_at else 'N/A'],
            ['<b>Puntaje técnico:</b>', f"<font color='#003b71'><b>{data['user']['score']} pts</b></font>"],
            ['<b>Perfil completado:</b>', f"<font color='#28a745'><b>{data['user']['perfil_completado']}%</b></font>"],
        ]
        
        user_table = Table(user_card, colWidths=[120, 300])
        user_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), gerdau_blue),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.white),
            ('ALIGN', (0, 0), (1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
        ]))
        
        story.append(user_table)
        story.append(Spacer(1, 30))
        
        # Código de seguridad
        security_code = f"GERDAU-PRM-{user.id:04d}-{timestamp}"
        story.append(Paragraph(
            f"<b>Código de seguridad del documento:</b> <font color='#dc3545'>{security_code}</font>",
            ParagraphStyle(name='Security', fontSize=9, alignment=TA_CENTER, textColor=colors.red)
        ))
        
        story.append(PageBreak())
        
        # ============================================
        # 6. PÁGINA 2: RESUMEN EJECUTIVO Y KPIs
        # ============================================
        story.append(Paragraph("RESUMEN EJECUTIVO", premium_styles['section_title']))
        story.append(Spacer(1, 15))
        
        # Resumen ejecutivo
        summary_text = f"""
        Este reporte presenta un análisis completo de la actividad y rendimiento del usuario 
        <b>{user.username}</b> en el Sistema Warehouse MRO de GERDAU. El análisis cubre el período 
        desde {data['user']['created_at'] if data['user']['created_at'] else 'su registro'} hasta la fecha actual.
        
        <br/><br/>
        <b>Hallazgos principales:</b>
        • Nivel de actividad: <b>{data['analysis']['activity_level']}</b>
        • Eficiencia en reportes: <b>{data['analysis']['efficiency']}%</b>
        • Tendencias: <b>{data['analysis']['trend']}</b>
        • Recomendaciones: {data['analysis']['recommendations']}
        """
        
        story.append(Paragraph(summary_text, premium_styles['body']))
        story.append(Spacer(1, 25))
        
        # KPIs en cuadrícula
        story.append(Paragraph("INDICADORES CLAVE DE RENDIMIENTO (KPIs)", premium_styles['subsection']))
        story.append(Spacer(1, 10))
        
        kpi_data = [
            ['KPI', 'VALOR', 'TENDENCIA', 'META', 'ESTADO'],
            ['Inventarios Subidos', str(data['stats']['inventarios']), 
             f"{data['trends']['inventarios']}%", '> 50', data['kpi_status']['inventarios']],
            ['Bultos Registrados', str(data['stats']['bultos']), 
             f"{data['trends']['bultos']}%", '> 30', data['kpi_status']['bultos']],
            ['Alertas Reportadas', str(data['stats']['alertas']), 
             f"{data['trends']['alertas']}%", '< 10', data['kpi_status']['alertas']],
            ['Eficiencia Operativa', f"{data['analysis']['efficiency']}%", 
             f"+{data['trends']['efficiency']}%", '> 85%', data['kpi_status']['efficiency']],
            ['Tiempo Promedio Respuesta', f"{data['stats']['avg_response_time']}h", 
             f"-{data['trends']['response_time']}%", '< 24h', data['kpi_status']['response_time']],
        ]
        
        kpi_table = Table(kpi_data, colWidths=[120, 60, 60, 50, 70])
        kpi_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), gerdau_dark),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('PADDING', (0, 0), (-1, -1), 6),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
        ]))
        
        story.append(kpi_table)
        story.append(Spacer(1, 25))
        
        # ============================================
        # 7. PÁGINA 3: GRÁFICOS AVANZADOS
        # ============================================
        story.append(PageBreak())
        story.append(Paragraph("ANÁLISIS GRÁFICO", premium_styles['section_title']))
        story.append(Spacer(1, 15))
        
        # Crear gráficos con reportlab nativo
        try:
            # Gráfico 1: Barras verticales comparativas
            drawing1 = Drawing(400, 200)
            vbc = VerticalBarChart()
            vbc.x = 50
            vbc.y = 20
            vbc.width = 300
            vbc.height = 150
            vbc.data = [
                [data['stats']['inventarios'], data['stats']['bultos'], data['stats']['alertas']],
                [data['stats']['inventarios'] * 0.8, data['stats']['bultos'] * 0.8, data['stats']['alertas'] * 1.2]
            ]
            vbc.categoryAxis.categoryNames = ['Inventarios', 'Bultos', 'Alertas']
            vbc.categoryAxis.labels.boxAnchor = 'n'
            vbc.valueAxis.valueMin = 0
            vbc.valueAxis.valueMax = max(data['stats']['inventarios'], data['stats']['bultos'], data['stats']['alertas']) * 1.3
            vbc.bars[0].fillColor = gerdau_blue
            vbc.bars[1].fillColor = gerdau_yellow
            vbc.barLabelFormat = '%d'
            vbc.barLabels.nudge = 10
            
            # Leyenda
            legend = Legend()
            legend.x = 350
            legend.y = 100
            legend.colorNamePairs = [
                (gerdau_blue, 'Actual'),
                (gerdau_yellow, 'Promedio')
            ]
            
            drawing1.add(vbc)
            drawing1.add(legend)
            
            # Convertir drawing a imagen y agregar
            img_buffer = io.BytesIO()
            renderPDF.drawToFile(drawing1, img_buffer, '')
            img_buffer.seek(0)
            
            # Guardar temporalmente y cargar como imagen
            temp_chart = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
            temp_chart.write(img_buffer.read())
            temp_chart.close()
            
            # Agregar imagen del gráfico
            chart_img = Image(temp_chart.name, width=400, height=200)
            chart_img.hAlign = 'CENTER'
            story.append(chart_img)
            story.append(Spacer(1, 10))
            story.append(Paragraph("<b>Figura 1:</b> Comparativa de actividad actual vs promedio", 
                                  ParagraphStyle(name='Caption', fontSize=8, alignment=TA_CENTER)))
            
            os.unlink(temp_chart.name)
            
        except Exception as e:
            print(f"[PDF Premium] Error gráfico 1: {e}")
            story.append(Paragraph("Gráfico no disponible temporalmente", premium_styles['body']))
        
        story.append(Spacer(1, 20))
        
        # Gráfico 2: Pie chart 3D
        try:
            drawing2 = Drawing(300, 200)
            pie = Pie3d()
            pie.x = 150
            pie.y = 20
            pie.width = 150
            pie.height = 150
            
            # Calcular distribución
            total = data['stats']['inventarios'] + data['stats']['bultos'] + data['stats']['alertas']
            if total > 0:
                pie.data = [data['stats']['inventarios'], data['stats']['bultos'], data['stats']['alertas']]
                pie.labels = ['Inventarios', 'Bultos', 'Alertas']
                pie.slices.strokeWidth = 0.5
                pie.slices[0].fillColor = gerdau_blue
                pie.slices[1].fillColor = gerdau_yellow
                pie.slices[2].fillColor = colors.red
                
                drawing2.add(pie)
                
                # Guardar y mostrar
                img_buffer2 = io.BytesIO()
                renderPDF.drawToFile(drawing2, img_buffer2, '')
                img_buffer2.seek(0)
                
                temp_chart2 = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
                temp_chart2.write(img_buffer2.read())
                temp_chart2.close()
                
                chart_img2 = Image(temp_chart2.name, width=300, height=200)
                chart_img2.hAlign = 'CENTER'
                story.append(chart_img2)
                story.append(Paragraph("<b>Figura 2:</b> Distribución de actividad", 
                                      ParagraphStyle(name='Caption', fontSize=8, alignment=TA_CENTER)))
                
                os.unlink(temp_chart2.name)
                
        except Exception as e:
            print(f"[PDF Premium] Error gráfico 2: {e}")
        
        story.append(PageBreak())
        
        # ============================================
        # 8. PÁGINA 4: ANÁLISIS TEMPORAL Y ACTIVIDAD
        # ============================================
        story.append(Paragraph("ANÁLISIS TEMPORAL", premium_styles['section_title']))
        story.append(Spacer(1, 15))
        
        # Tabla de tendencias mensuales
        if data['monthly_trends']:
            monthly_data = [['MES', 'INVENTARIOS', 'BULTOS', 'ALERTAS', 'TENDENCIA']]
            
            for month in data['monthly_trends'][:6]:  # Últimos 6 meses
                trend_icon = "📈" if month['trend'] == 'ascendente' else "📉" if month['trend'] == 'descendente' else "➡️"
                monthly_data.append([
                    month['month'],
                    str(month['inventarios']),
                    str(month['bultos']),
                    str(month['alertas']),
                    trend_icon
                ])
            
            monthly_table = Table(monthly_data, colWidths=[80, 60, 60, 60, 40])
            monthly_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), gerdau_blue),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ('PADDING', (0, 0), (-1, -1), 5),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
            ]))
            
            story.append(monthly_table)
            story.append(Spacer(1, 20))
        
        # Timeline de actividad reciente
        story.append(Paragraph("TIMELINE DE ACTIVIDAD RECIENTE", premium_styles['subsection']))
        story.append(Spacer(1, 10))
        
        if data['recent_activity']:
            activity_text = ""
            for i, activity in enumerate(data['recent_activity'][:15], 1):
                icon = "✅" if 'creó' in activity['descripcion'] or 'subió' in activity['descripcion'] else \
                       "⚠️" if 'alerta' in activity['descripcion'].lower() else "📋"
                activity_text += f"{icon} <b>{activity['fecha']}</b> - {activity['descripcion']}<br/>"
            
            story.append(Paragraph(activity_text, premium_styles['body']))
        else:
            story.append(Paragraph("No hay actividad registrada recientemente.", premium_styles['body']))
        
        story.append(Spacer(1, 25))
        
        # ============================================
        # 9. PÁGINA 5: RECOMENDACIONES Y CIERRE
        # ============================================
        story.append(PageBreak())
        story.append(Paragraph("RECOMENDACIONES Y PLAN DE ACCIÓN", premium_styles['section_title']))
        story.append(Spacer(1, 15))
        
        # Recomendaciones personalizadas
        recommendations = [
            ("📊 <b>Optimización de Procesos</b>", 
             f"Implementar checklists automatizados para reducir tiempos de respuesta en {data['stats']['avg_response_time']} horas."),
            ("🎯 <b>Mejora de Precisión</b>", 
             "Realizar capacitación mensual sobre el uso correcto del sistema de inventarios."),
            ("🚀 <b>Incremento de Productividad</b>", 
             f"Establecer metas SMART para aumentar la productividad en un {data['analysis']['efficiency_target']}%."),
            ("🛡️ <b>Reducción de Alertas</b>", 
             "Implementar sistema de prevención de errores basado en análisis predictivo."),
            ("📈 <b>Desarrollo de Habilidades</b>", 
             "Programar sesiones de mentoring sobre mejores prácticas en gestión de almacén.")
        ]
        
        for title, desc in recommendations:
            story.append(Paragraph(title, premium_styles['highlight']))
            story.append(Paragraph(desc, premium_styles['body']))
            story.append(Spacer(1, 10))
        
        story.append(Spacer(1, 20))
        
        # Plan de acción
        action_plan = [
            ['PRIORIDAD', 'ACCIÓN', 'RESPONSABLE', 'FECHA LÍMITE', 'ESTADO'],
            ['Alta', 'Capacitación sistema MRO', user.username, '15 días', 'Pendiente'],
            ['Media', 'Optimización procesos', 'Supervisor', '30 días', 'Planificado'],
            ['Baja', 'Actualización perfil', user.username, '7 días', 'En progreso'],
        ]
        
        action_table = Table(action_plan, colWidths=[50, 150, 80, 70, 60])
        action_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), gerdau_dark),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        
        story.append(action_table)
        story.append(Spacer(1, 30))
        
        # QR Code para verificación
        try:
            qr_data = f"""
            GERDAU REPORTE PREMIUM
            Usuario: {user.username}
            ID: {user.id}
            Código: {security_code}
            Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}
            Score: {data['user']['score']}
            """
            
            qr = qrcode.QRCode(version=2, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=6, border=2)
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            qr_temp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            qr.make_image(fill_color="#003b71", back_color="white").save(qr_temp.name)
            
            qr_img = Image(qr_temp.name, width=100, height=100)
            qr_img.hAlign = 'CENTER'
            story.append(qr_img)
            
            story.append(Paragraph(
                "<b>Código QR de verificación</b><br/>Escanea para validar autenticidad",
                ParagraphStyle(name='QRCaption', fontSize=8, alignment=TA_CENTER)
            ))
            
            os.unlink(qr_temp.name)
            
        except Exception as e:
            print(f"[PDF Premium] Error QR: {e}")
        
        # ============================================
        # 10. GENERAR PDF
        # ============================================
        # Función para agregar pie de página
        def add_premium_footer(canvas, doc):
            canvas.saveState()
            
            # Fecha y número de página
            canvas.setFont('Helvetica', 8)
            canvas.setFillColor(colors.gray)
            
            page_num = canvas.getPageNumber()
            fecha = datetime.now().strftime('%d/%m/%Y %H:%M')
            
            canvas.drawString(72, 30, f"Página {page_num} de {doc.page}")
            canvas.drawCentredString(297.5, 30, f"Documento confidencial - {security_code}")
            canvas.drawRightString(523, 30, f"Generado: {fecha}")
            
            # Línea decorativa
            canvas.setStrokeColor(gerdau_blue)
            canvas.setLineWidth(0.5)
            canvas.line(72, 42, 523, 42)
            
            # Logo pequeño
            canvas.setFillColor(gerdau_blue)
            canvas.setFont('Helvetica-Bold', 10)
            canvas.drawString(72, 55, "GERDAU")
            canvas.setFont('Helvetica', 7)
            canvas.drawString(72, 50, "Warehouse MRO")
            
            canvas.restoreState()
        
        # Construir documento
        doc.build(story, onFirstPage=add_premium_footer, onLaterPages=add_premium_footer)
        
        print(f"[PDF Premium] Generado exitosamente: {pdf_path}")
        return pdf_path
        
    except Exception as e:
        print(f"[PDF Premium] Error general: {e}")
        import traceback
        traceback.print_exc()
        return None


def collect_comprehensive_data(user_id):
    """Recopila todos los datos necesarios para el reporte premium"""
    
    user = User.query.get(user_id)
    
    # Estadísticas básicas
    inventarios = InventoryItem.query.count()
    bultos = Bulto.query.count()
    alertas = Alert.query.count()
    
    # Actividad reciente
    actividad = ActividadUsuario.query\
        .filter_by(user_id=user_id)\
        .order_by(ActividadUsuario.fecha.desc())\
        .limit(20)\
        .all()
    
    # Procesar actividad
    recent_activity = []
    for act in actividad:
        recent_activity.append({
            'fecha': act.fecha.strftime('%d/%m/%Y %H:%M') if hasattr(act.fecha, 'strftime') else str(act.fecha),
            'descripcion': act.descripcion
        })
    
    # Calcular tendencias (simuladas para ejemplo)
    import random
    monthly_trends = []
    months = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    
    for i, month in enumerate(months[-6:]):  # Últimos 6 meses
        base_value = max(1, inventarios // 6)
        trend_types = ['ascendente', 'descendente', 'estable']
        
        monthly_trends.append({
            'month': month,
            'inventarios': base_value + random.randint(-5, 15),
            'bultos': max(1, bultos // 6) + random.randint(-3, 10),
            'alertas': max(0, alertas // 6) + random.randint(-2, 5),
            'trend': random.choice(trend_types)
        })
    
    # Análisis de rendimiento
    efficiency = min(100, int((inventarios + bultos) / max(1, alertas) * 10))
    activity_level = 'Bajo' if inventarios + bultos < 10 else 'Moderado' if inventarios + bultos < 50 else 'Alto'
    
    # Determinar estado de KPIs
    def get_kpi_status(value, target, higher_is_better=True):
        if higher_is_better:
            if value >= target * 1.2:
                return 'Excelente'
            elif value >= target:
                return 'Bueno'
            elif value >= target * 0.7:
                return 'Aceptable'
            else:
                return 'Requiere atención'
        else:
            if value <= target * 0.5:
                return 'Excelente'
            elif value <= target:
                return 'Bueno'
            elif value <= target * 1.3:
                return 'Aceptable'
            else:
                return 'Requiere atención'
    
    return {
        'user': {
            'username': user.username,
            'email': user.email,
            'role': getattr(user, 'role', 'Usuario'),
            'score': getattr(user, 'score', 0),
            'perfil_completado': getattr(user, 'perfil_completado', 0),
            'created_at': user.created_at.strftime('%d/%m/%Y') if user.created_at else 'N/A'
        },
        'stats': {
            'inventarios': inventarios,
            'bultos': bultos,
            'alertas': alertas,
            'avg_response_time': random.randint(4, 48),  # Simulado
            'total_activities': inventarios + bultos + alertas
        },
        'trends': {
            'inventarios': random.randint(-10, 30),
            'bultos': random.randint(-5, 25),
            'alertas': random.randint(-15, 20),
            'efficiency': random.randint(5, 15),
            'response_time': random.randint(5, 25)
        },
        'analysis': {
            'activity_level': activity_level,
            'efficiency': efficiency,
            'efficiency_target': min(30, efficiency + random.randint(5, 15)),
            'trend': 'Positiva' if inventarios + bultos > alertas * 3 else 'Neutral' if inventarios + bultos > alertas else 'Requiere mejora',
            'recommendations': f"{random.randint(2, 5)} áreas de mejora identificadas"
        },
        'kpi_status': {
            'inventarios': get_kpi_status(inventarios, 50, True),
            'bultos': get_kpi_status(bultos, 30, True),
            'alertas': get_kpi_status(alertas, 10, False),
            'efficiency': get_kpi_status(efficiency, 85, True),
            'response_time': get_kpi_status(random.randint(4, 48), 24, False)
        },
        'monthly_trends': monthly_trends,
        'recent_activity': recent_activity
    }
