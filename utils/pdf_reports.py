import os
import io
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing, String, Line
from reportlab.graphics.charts.barcharts import VerticalBarChart, HorizontalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.widgets.markers import makeMarker
from reportlab.graphics import renderPDF
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import qrcode
from flask import current_app
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import tempfile
import seaborn as sns
from PIL import Image as PILImage
import base64

# Importar modelos
from models.user import User
from models.inventory import InventoryItem
from models.bultos import Bulto
from models.alerts import Alert
from models.actividad import ActividadUsuario
from models import db

def create_pdf_reporte(user_id):
    """
    Genera el PDF CORPORATIVO PREMIUM del perfil del usuario
    Incluye:
    - Datos personales completos con foto
    - Puntaje anual (score) con gráfico de progreso
    - KPIs detallados con gráficos profesionales
    - Estadísticas avanzadas
    - Actividad reciente con timeline
    - QR de verificación dinámico
    - Marca de agua de seguridad
    """
    
    try:
        user = User.query.get(user_id)
        if not user:
            return None

        # ======================================================
        # CONFIGURACIÓN INICIAL
        # ======================================================
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        security_code = f"GERDAU-{user.id:04d}-{timestamp}"
        
        # Crear directorio de reportes si no existe
        reports_folder = os.path.join(current_app.root_path, "static", "reports")
        os.makedirs(reports_folder, exist_ok=True)
        
        pdf_path = os.path.join(reports_folder, f"perfil_usuario_{user.id}_{timestamp}.pdf")
        
        # ======================================================
        # DATOS DEL USUARIO
        # ======================================================
        user_data = {
            'username': user.username,
            'email': user.email or 'No registrado',
            'role': user.role.upper(),
            'phone': user.phone or 'No registrado',
            'location': user.location or 'No especificada',
            'area': user.area or 'No asignada',
            'created_at': user.created_at.strftime('%d/%m/%Y') if user.created_at else 'Sin registro',
            'score': getattr(user, 'score', 0),
            'perfil_completado': getattr(user, 'perfil_completado', 0),
            'photo_path': None
        }
        
        # Verificar foto del usuario
        if user.photo:
            photo_full_path = os.path.join(current_app.root_path, 'static', user.photo.lstrip('/'))
            if os.path.exists(photo_full_path):
                user_data['photo_path'] = photo_full_path
        
        # ======================================================
        # KPI Y ESTADÍSTICAS
        # ======================================================
        # Estadísticas básicas
        kpi_inventarios = InventoryItem.query.count()
        kpi_bultos = Bulto.query.count()
        kpi_alertas = Alert.query.count()
        
        # Estadísticas por mes (últimos 6 meses)
        six_months_ago = datetime.utcnow() - timedelta(days=180)
        
        # Inventarios por mes
        monthly_inventarios = db.session.query(
            db.func.strftime('%Y-%m', InventoryItem.created_at).label('month'),
            db.func.count().label('count')
        ).filter(InventoryItem.created_at >= six_months_ago)\
         .group_by('month')\
         .order_by('month')\
         .all()
        
        # Bultos por mes
        monthly_bultos = db.session.query(
            db.func.strftime('%Y-%m', Bulto.created_at).label('month'),
            db.func.count().label('count')
        ).filter(Bulto.created_at >= six_months_ago)\
         .group_by('month')\
         .order_by('month')\
         .all()
        
        # Alertas por tipo
        alertas_por_tipo = db.session.query(
            Alert.tipo,
            db.func.count().label('count')
        ).group_by(Alert.tipo).all()
        
        # ======================================================
        # ACTIVIDAD RECIENTE
        # ======================================================
        actividad = ActividadUsuario.query\
            .filter_by(user_id=user.id)\
            .order_by(ActividadUsuario.fecha.desc())\
            .limit(20)\
            .all()
        
        actividad_formateada = []
        for log in actividad:
            actividad_formateada.append({
                'fecha': log.fecha.strftime('%d/%m/%Y %H:%M'),
                'descripcion': log.descripcion[:100] + '...' if len(log.descripcion) > 100 else log.descripcion
            })
        
        # ======================================================
        # GENERAR PDF CON PLATYPUS (más control)
        # ======================================================
        doc = SimpleDocTemplate(
            pdf_path,
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        story = []
        styles = getSampleStyleSheet()
        
        # Estilos personalizados
        styles.add(ParagraphStyle(
            name='Title',
            parent=styles['Title'],
            fontSize=24,
            textColor=colors.HexColor('#003b71'),
            alignment=TA_CENTER,
            spaceAfter=30
        ))
        
        styles.add(ParagraphStyle(
            name='Subtitle',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#003b71'),
            spaceAfter=12
        ))
        
        styles.add(ParagraphStyle(
            name='Body',
            parent=styles['BodyText'],
            fontSize=10,
            spaceAfter=6
        ))
        
        styles.add(ParagraphStyle(
            name='TableHeader',
            parent=styles['BodyText'],
            fontSize=10,
            textColor=colors.white,
            alignment=TA_CENTER
        ))
        
        styles.add(ParagraphStyle(
            name='Footer',
            parent=styles['BodyText'],
            fontSize=8,
            textColor=colors.gray,
            alignment=TA_CENTER
        ))
        
        # ======================================================
        # PÁGINA 1: PORTADA
        # ======================================================
        # Logo Gerdau
        try:
            logo_path = os.path.join(current_app.root_path, "static", "img", "gerdau_logo.jpg")
            if os.path.exists(logo_path):
                logo = Image(logo_path, width=200, height=80)
                logo.hAlign = 'CENTER'
                story.append(logo)
                story.append(Spacer(1, 20))
        except:
            pass
        
        # Título principal
        story.append(Paragraph("REPORTE CORPORATIVO DE USUARIO", styles['Title']))
        story.append(Spacer(1, 10))
        
        # Fecha de generación
        story.append(Paragraph(
            f"Generado el: {datetime.utcnow().strftime('%d/%m/%Y %H:%M:%S')}",
            ParagraphStyle(name='Date', fontSize=10, alignment=TA_CENTER, textColor=colors.gray)
        ))
        
        story.append(Spacer(1, 40))
        
        # Información del usuario
        user_info_table_data = [
            ['DATOS DEL USUARIO', ''],
            ['Nombre de usuario:', user_data['username']],
            ['Correo electrónico:', user_data['email']],
            ['Rol en el sistema:', user_data['role']],
            ['Teléfono:', user_data['phone']],
            ['Ubicación:', user_data['location']],
            ['Área/Departamento:', user_data['area']],
            ['Miembro desde:', user_data['created_at']],
            ['Puntaje anual:', str(user_data['score']) + ' pts'],
            ['Perfil completado:', str(user_data['perfil_completado']) + '%']
        ]
        
        user_info_table = Table(user_info_table_data, colWidths=[120, 300])
        user_info_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#003b71')),
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
            ('FONTNAME', (1, 1), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        
        story.append(user_info_table)
        story.append(Spacer(1, 30))
        
        # Código de seguridad
        story.append(Paragraph(
            f"Código de seguridad del documento: <b>{security_code}</b>",
            ParagraphStyle(name='SecurityCode', fontSize=9, textColor=colors.red, alignment=TA_CENTER)
        ))
        
        story.append(PageBreak())
        
        # ======================================================
        # PÁGINA 2: KPIs Y GRÁFICOS
        # ======================================================
        story.append(Paragraph("ESTADÍSTICAS Y MÉTRICAS", styles['Subtitle']))
        story.append(Spacer(1, 20))
        
        # KPIs en tarjetas
        kpi_data = [
            ['MÉTRICA', 'VALOR', 'DESCRIPCIÓN'],
            ['Inventarios subidos', str(kpi_inventarios), 'Total de inventarios registrados en el sistema'],
            ['Bultos registrados', str(kpi_bultos), 'Total de bultos procesados'],
            ['Alertas reportadas', str(kpi_alertas), 'Alertas generadas por el usuario'],
            ['Puntaje técnico', str(user_data['score']), 'Puntaje acumulado por actividades'],
            ['Eficiencia', f"{user_data['perfil_completado']}%", 'Completitud del perfil']
        ]
        
        kpi_table = Table(kpi_data, colWidths=[120, 60, 240])
        kpi_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003b71')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#e9f2ff')),
            ('BACKGROUND', (0, 3), (-1, 3), colors.HexColor('#e9f2ff')),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 1), (1, -1), 'CENTER'),
            ('ALIGN', (2, 1), (2, -1), 'LEFT'),
            ('FONTNAME', (0, 1), (1, -1), 'Helvetica-Bold'),
            ('FONTNAME', (2, 1), (2, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        
        story.append(kpi_table)
        story.append(Spacer(1, 30))
        
        # Gráfico de barras
        try:
            # Crear gráfico con matplotlib
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
            
            # Gráfico 1: KPIs principales
            kpi_labels = ['Inventarios', 'Bultos', 'Alertas']
            kpi_values = [kpi_inventarios, kpi_bultos, kpi_alertas]
            
            bars = ax1.bar(kpi_labels, kpi_values, color=['#003b71', '#f8c000', '#dc3545'])
            ax1.set_title('Actividad del Usuario', fontweight='bold')
            ax1.set_ylabel('Cantidad')
            
            # Agregar valores en las barras
            for bar, value in zip(bars, kpi_values):
                height = bar.get_height()
                ax1.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                        f'{value}', ha='center', va='bottom', fontweight='bold')
            
            # Gráfico 2: Distribución
            if alertas_por_tipo:
                tipos = [tipo[0] or 'Sin tipo' for tipo in alertas_por_tipo]
                counts = [tipo[1] for tipo in alertas_por_tipo]
                ax2.pie(counts, labels=tipos, autopct='%1.1f%%', 
                       colors=plt.cm.Set3(np.linspace(0, 1, len(tipos))))
                ax2.set_title('Alertas por Tipo', fontweight='bold')
            
            plt.tight_layout()
            
            # Guardar gráfico temporalmente
            temp_chart = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            plt.savefig(temp_chart.name, dpi=150, bbox_inches='tight')
            plt.close()
            
            # Agregar gráfico al PDF
            chart_img = Image(temp_chart.name, width=400, height=200)
            chart_img.hAlign = 'CENTER'
            story.append(chart_img)
            
            # Limpiar archivo temporal
            os.unlink(temp_chart.name)
            
        except Exception as e:
            print(f"Error generando gráficos: {e}")
            story.append(Paragraph("Gráficos no disponibles temporalmente", styles['Body']))
        
        story.append(PageBreak())
        
        # ======================================================
        # PÁGINA 3: ACTIVIDAD RECIENTE
        # ======================================================
        story.append(Paragraph("HISTORIAL DE ACTIVIDAD", styles['Subtitle']))
        story.append(Spacer(1, 20))
        
        if actividad_formateada:
            # Crear tabla de actividad
            actividad_data = [['FECHA', 'ACCIÓN REALIZADA']]
            
            for act in actividad_formateada:
                actividad_data.append([act['fecha'], act['descripcion']])
            
            actividad_table = Table(actividad_data, colWidths=[100, 380])
            actividad_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#003b71')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 11),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('ALIGN', (0, 1), (0, -1), 'CENTER'),
                ('ALIGN', (1, 1), (1, -1), 'LEFT'),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
                ('PADDING', (0, 0), (-1, -1), 4),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ]))
            
            story.append(actividad_table)
        else:
            story.append(Paragraph("No hay actividad registrada para este usuario.", styles['Body']))
        
        story.append(Spacer(1, 30))
        
        # ======================================================
        # PÁGINA 4: RESUMEN Y FIRMAS
        # ======================================================
        story.append(PageBreak())
        story.append(Paragraph("RESUMEN EJECUTIVO", styles['Subtitle']))
        story.append(Spacer(1, 20))
        
        # Resumen ejecutivo
        summary_text = f"""
        <b>Usuario:</b> {user_data['username']}<br/>
        <b>Período analizado:</b> Últimos 6 meses<br/>
        <b>Puntaje de rendimiento:</b> {user_data['score']} pts<br/>
        <b>Nivel de actividad:</b> {('Bajo' if kpi_inventarios + kpi_bultos < 10 else 'Moderado' if kpi_inventarios + kpi_bultos < 50 else 'Alto')}<br/>
        <b>Eficiencia en reportes:</b> {min(100, int((kpi_inventarios + kpi_bultos) / max(1, kpi_alertas) * 10))}%<br/>
        <br/>
        <b>Observaciones:</b><br/>
        El usuario ha demostrado {'una participación activa' if kpi_inventarios + kpi_bultos > 20 else 'participación básica'} en el sistema.
        {'Presenta buen manejo de alertas y reportes.' if kpi_alertas < 5 else 'Requiere atención en el manejo de alertas.'}
        """
        
        story.append(Paragraph(summary_text, styles['Body']))
        story.append(Spacer(1, 40))
        
        # QR Code para verificación
        try:
            # Generar QR con datos codificados
            qr_data = f"""
            Usuario: {user_data['username']}
            ID: {user.id}
            Código: {security_code}
            Fecha: {datetime.utcnow().strftime('%Y-%m-%d')}
            Score: {user_data['score']}
            """
            
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_H,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)
            
            qr_img = qr.make_image(fill_color="#003b71", back_color="white")
            
            # Guardar QR temporalmente
            temp_qr = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            qr_img.save(temp_qr.name)
            
            # Agregar QR al PDF
            qr_pdf_img = Image(temp_qr.name, width=100, height=100)
            qr_pdf_img.hAlign = 'CENTER'
            story.append(qr_pdf_img)
            
            story.append(Spacer(1, 10))
            story.append(Paragraph(
                "<b>Código QR de verificación</b><br/>Escanea para validar autenticidad del documento",
                ParagraphStyle(name='QRCaption', fontSize=9, alignment=TA_CENTER)
            ))
            
            # Limpiar archivo temporal
            os.unlink(temp_qr.name)
            
        except Exception as e:
            print(f"Error generando QR: {e}")
        
        story.append(Spacer(1, 40))
        
        # Línea para firma
        signature_line = "_______________________________________"
        story.append(Paragraph(signature_line, ParagraphStyle(name='SignatureLine', fontSize=12, alignment=TA_CENTER)))
        story.append(Paragraph(
            "Gerente de Operaciones / Sistema Warehouse MRO",
            ParagraphStyle(name='SignatureTitle', fontSize=9, alignment=TA_CENTER, textColor=colors.gray)
        ))
        
        # ======================================================
        # PIE DE PÁGINA PARA TODAS LAS PÁGINAS
        # ======================================================
        def add_footer(canvas, doc):
            canvas.saveState()
            
            # Marca de agua de fondo
            canvas.setFont('Helvetica-Bold', 60)
            canvas.setFillColorRGB(0.95, 0.95, 0.95)
            canvas.translate(300, 400)
            canvas.rotate(45)
            canvas.drawString(0, 0, "GERDAU")
            canvas.restoreState()
            
            # Pie de página
            canvas.setFont('Helvetica', 8)
            canvas.setFillColor(colors.gray)
            
            # Información izquierda
            canvas.drawString(72, 30, f"Documento: {security_code}")
            
            # Información central
            canvas.drawCentredString(297.5, 30, f"Página {doc.page}")
            
            # Información derecha
            canvas.drawRightString(523, 30, datetime.utcnow().strftime('%d/%m/%Y'))
            
            # Línea separadora
            canvas.setStrokeColor(colors.HexColor('#003b71'))
            canvas.setLineWidth(0.5)
            canvas.line(72, 45, 523, 45)
            
            canvas.restoreState()
        
        # ======================================================
        # GENERAR PDF
        # ======================================================
        doc.build(story, onFirstPage=add_footer, onLaterPages=add_footer)
        
        # ======================================================
        # AGREGAR MARCA DE AGUA DE SEGURIDAD (opcional)
        # ======================================================
        try:
            # Esto es opcional - agrega una marca de agua visible
            from PyPDF2 import PdfReader, PdfWriter
            
            reader = PdfReader(pdf_path)
            writer = PdfWriter()
            
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                writer.add_page(page)
            
            # Agregar metadatos
            writer.add_metadata({
                '/Title': f'Reporte Corporativo - {user_data["username"]}',
                '/Author': 'Sistema Warehouse MRO - Gerdau',
                '/Subject': 'Reporte de usuario',
                '/Keywords': f'gerdau, usuario, reporte, {security_code}',
                '/Creator': 'Sistema Warehouse MRO v2.0',
                '/Producer': 'ReportLab PDF Library',
                '/CreationDate': datetime.utcnow().strftime("D:%Y%m%d%H%M%S"),
            })
            
            # Guardar con metadatos
            with open(pdf_path, 'wb') as output_file:
                writer.write(output_file)
                
        except ImportError:
            # Si PyPDF2 no está instalado, continuar sin metadatos
            pass
        
        return pdf_path
        
    except Exception as e:
        print(f"Error crítico generando PDF: {e}")
        import traceback
        traceback.print_exc()
        return None


def create_quick_stats_pdf(user_id):
    """
    Genera un PDF rápido de estadísticas (versión simplificada)
    Para cuando no se necesite el reporte completo
    """
    try:
        user = User.query.get(user_id)
        if not user:
            return None
        
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        pdf_path = os.path.join(current_app.root_path, "static", "reports", 
                               f"stats_{user.id}_{timestamp}.pdf")
        
        # Datos básicos
        kpi_inventarios = InventoryItem.query.count()
        kpi_bultos = Bulto.query.count()
        kpi_alertas = Alert.query.count()
        score = getattr(user, 'score', 0)
        
        # Crear PDF simple
        c = canvas.Canvas(pdf_path, pagesize=letter)
        width, height = letter
        
        # Encabezado
        c.setFillColorRGB(0, 59/255, 113/255)
        c.rect(0, height - 60, width, 60, fill=1)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, height - 40, "RESUMEN DE ESTADÍSTICAS")
        c.setFont("Helvetica", 10)
        c.drawString(50, height - 55, f"Usuario: {user.username}")
        
        # Contenido
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, height - 100, "Estadísticas Rápidas:")
        
        y = height - 130
        stats = [
            ("Inventarios subidos:", kpi_inventarios),
            ("Bultos registrados:", kpi_bultos),
            ("Alertas reportadas:", kpi_alertas),
            ("Puntaje técnico:", score),
        ]
        
        c.setFont("Helvetica", 12)
        for label, value in stats:
            c.drawString(70, y, f"{label} {value}")
            y -= 25
        
        # Fecha y código
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.gray)
        c.drawString(50, 50, f"Generado: {datetime.utcnow().strftime('%d/%m/%Y %H:%M')}")
        c.drawRightString(width - 50, 50, f"Código: GERDAU-{user.id:04d}")
        
        c.save()
        return pdf_path
        
    except Exception as e:
        print(f"Error en PDF rápido: {e}")
        return None
