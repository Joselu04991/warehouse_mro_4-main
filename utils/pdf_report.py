import os
import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics import renderPDF
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
import qrcode
from flask import current_app

from models.user import User
from models.inventory import InventoryItem
from models.bultos import Bulto
from models.alerts import Alert
from models.actividad import ActividadUsuario


def create_pdf_reporte(user_id):
    """
    REPORTE CORPORATIVO ULTRA – PERFIL DE USUARIO
    Incluye:
    - Datos personales
    - Nota (score anual)
    - KPIs
    - Gráficos
    - Actividad
    - QR de verificación
    - Marca de agua
    """

    user = User.query.get(user_id)
    if not user:
        return None

    # ================= KPIs =================
    kpi_inventarios = InventoryItem.query.count()
    kpi_bultos = Bulto.query.count()
    kpi_alertas = Alert.query.count()

    score = getattr(user, "score", 0)
    perfil_completado = getattr(user, "perfil_completado", 0)

    actividad = (
        ActividadUsuario.query
        .filter_by(user_id=user.id)
        .order_by(ActividadUsuario.fecha.desc())
        .limit(25)
        .all()
    )

    security_code = f"SEC-{user.id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

    # ================= RUTA PDF =================
    reports_folder = os.path.join(current_app.root_path, "static", "reports")
    os.makedirs(reports_folder, exist_ok=True)

    pdf_path = os.path.join(
        reports_folder,
        f"perfil_usuario_{user.id}_CORPORATIVO_ULTRA.pdf"
    )

    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter

    # ================= MARCA DE AGUA =================
    c.saveState()
    c.setFont("Helvetica-Bold", 60)
    c.setFillColorRGB(0.93, 0.93, 0.93)
    c.translate(width / 5, height / 3)
    c.rotate(45)
    c.drawString(0, 0, "GERDAU - CONFIDENCIAL")
    c.restoreState()

    # ================= HEADER =================
    c.setFillColorRGB(0, 59/255, 113/255)
    c.rect(0, height - 95, width, 95, fill=1)

    c.setFont("Helvetica-Bold", 22)
    c.setFillColor(colors.white)
    c.drawString(30, height - 55, "Reporte Corporativo de Usuario")

    c.setFont("Helvetica", 11)
    c.drawString(30, height - 75, "Sistema Warehouse MRO – SIDERPERU / GERDAU")

    try:
        logo_path = os.path.join(current_app.root_path, "static", "img", "gerdau_logo.jpg")
        c.drawImage(logo_path, width - 150, height - 85, width=120, height=55, mask="auto")
    except:
        pass

    # ================= DATOS USUARIO =================
    top = height - 135

    if user.photo:
        try:
            photo_path = os.path.join(current_app.root_path, "static", user.photo)
            c.drawImage(photo_path, 30, top - 125, width=110, height=110, mask="auto")
        except:
            pass

    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 15)
    c.drawString(160, top, f"Usuario: {user.username}")

    c.setFont("Helvetica", 12)
    c.drawString(160, top - 22, f"Rol: {user.role.upper()}")
    c.drawString(160, top - 42, f"Correo: {user.email}")
    c.drawString(160, top - 62, f"Área: {user.area or 'No asignada'}")
    c.drawString(160, top - 82, f"Ubicación: {user.location or 'No registrada'}")

    creado = user.created_at.strftime("%d/%m/%Y") if user.created_at else "Sin registro"
    c.drawString(160, top - 102, f"Miembro desde: {creado}")

    # ================= SCORE =================
    c.setFont("Helvetica-Bold", 14)
    c.setFillColor(colors.HexColor("#003b71"))
    c.drawString(160, top - 130, f"Nota anual (Score): {score} pts")

    c.setFont("Helvetica", 11)
    c.setFillColor(colors.black)
    c.drawString(160, top - 150, f"Perfil completado: {perfil_completado}%")

    # ================= GRÁFICO DE BARRAS =================
    chart = Drawing(400, 220)
    bar = VerticalBarChart()

    bar.x = 50
    bar.y = 40
    bar.width = 300
    bar.height = 160
    bar.data = [[kpi_inventarios, kpi_bultos, kpi_alertas]]
    bar.categoryAxis.categoryNames = ["Inventarios", "Bultos", "Alertas"]
    bar.bars[0].fillColor = colors.HexColor("#003b71")

    chart.add(bar)
    renderPDF.draw(chart, c, 30, top - 380)

    # ================= GRÁFICO PIE =================
    total = kpi_inventarios + kpi_bultos + kpi_alertas
    if total > 0:
        pie_draw = Drawing(220, 180)
        pie = Pie()
        pie.x = 50
        pie.y = 20
        pie.width = 130
        pie.height = 130
        pie.data = [kpi_inventarios, kpi_bultos, kpi_alertas]
        pie.labels = ["Inventarios", "Bultos", "Alertas"]
        pie_draw.add(pie)
        renderPDF.draw(pie_draw, c, width - 260, top - 380)

    # ================= QR =================
    qr_buf = io.BytesIO()
    qr = qrcode.QRCode(box_size=3, border=2)
    qr.add_data(f"Usuario:{user.id}|Score:{score}|Fecha:{datetime.utcnow()}")
    qr.make(fit=True)
    img = qr.make_image()
    img.save(qr_buf, format="PNG")
    qr_buf.seek(0)

    c.drawImage(ImageReader(qr_buf), width - 120, top - 200, width=70, height=70)

    # ================= ACTIVIDAD =================
    y = top - 420
    c.setFont("Helvetica-Bold", 15)
    c.drawString(30, y, "Actividad reciente del usuario")
    y -= 20

    c.setFont("Helvetica", 10)

    if actividad:
        for log in actividad:
            if y < 80:
                c.showPage()
                y = height - 50
                c.setFont("Helvetica", 10)

            fecha = log.fecha.strftime("%d/%m/%Y %H:%M")
            c.drawString(30, y, f"{fecha} — {log.descripcion}")
            y -= 16
    else:
        c.drawString(30, y, "No hay actividad registrada.")

    # ================= FOOTER =================
    c.setFillColorRGB(0, 59/255, 113/255)
    c.rect(0, 0, width, 45, fill=1)

    c.setFont("Helvetica", 9)
    c.setFillColor(colors.white)
    c.drawString(30, 25, "Sistema Warehouse MRO — GERDAU / SIDERPERU")
    c.drawRightString(width - 30, 25, f"Código de seguridad: {security_code}")

    c.save()
    return pdf_path
