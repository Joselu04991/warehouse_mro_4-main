from flask import (
    Blueprint, render_template, request, redirect,
    url_for, flash, current_app, send_file, session
)
from flask_login import (
    login_user, logout_user, login_required,
    current_user
)

# IMPORTS CORRECTOS PARA RAILWAY
from models import db
from models.user import User

from datetime import datetime
import os
from werkzeug.utils import secure_filename

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


# ============================================================
# 🔐 LOGIN SIMPLE (SIN BLOQUEO, SIN 2FA, SIN VERIFICACIÓN)
# ============================================================
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username").strip()
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()

        if not user or not user.check_password(password):
            flash("Usuario o contraseña incorrectos.", "danger")
            return redirect(url_for("auth.login"))

        user.last_login = datetime.utcnow()
        db.session.commit()
        login_user(user)

        flash("Bienvenido.", "success")
        return redirect(url_for("dashboard.dashboard"))

    return render_template("auth/login.html")


# ============================================================
# 📝 REGISTRO SIMPLE (SIN CONFIRMAR CORREO)
# ============================================================
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username").strip()
        email = request.form.get("email").strip()
        password = request.form.get("password")
        password2 = request.form.get("password2")

        if password != password2:
            flash("Las contraseñas no coinciden.", "danger")
            return redirect(url_for("auth.register"))

        if User.query.filter_by(username=username).first():
            flash("Ese usuario ya existe.", "danger")
            return redirect(url_for("auth.register"))

        if User.query.filter_by(email=email).first():
            flash("Ese correo ya está registrado.", "danger")
            return redirect(url_for("auth.register"))

        nuevo = User(
            username=username,
            email=email,
            role="user",
            status="active"
        )
        nuevo.set_password(password)

        db.session.add(nuevo)
        db.session.commit()

        flash("Cuenta creada. Ahora inicia sesión.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html")


# ============================================================
# 🚪 LOGOUT
# ============================================================
@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada.", "info")
    return redirect(url_for("auth.login"))


# ============================================================
# 👤 PERFIL
# ============================================================
@auth_bp.route("/perfil")
@login_required
def perfil_usuario():
    # Calcular KPIs básicos para mostrar en el perfil
    from models.inventory import InventoryItem
    from models.bultos import Bulto
    from models.alerts import Alert
    
    kpi_inventarios = InventoryItem.query.count()
    kpi_bultos = Bulto.query.count()
    kpi_alertas = Alert.query.count()
    
    return render_template("perfil_usuario.html",
                         kpi_inventarios=kpi_inventarios,
                         kpi_bultos=kpi_bultos,
                         kpi_alertas=kpi_alertas)


# ============================================================
# ✏ EDITAR PERFIL
# ============================================================
@auth_bp.route("/editar", methods=["GET", "POST"])
@login_required
def edit_user():
    if request.method == "POST":
        current_user.email = request.form.get("email")
        current_user.phone = request.form.get("phone")
        current_user.location = request.form.get("location")
        current_user.area = request.form.get("area")

        db.session.commit()

        flash("Cambios guardados.", "success")
        return redirect(url_for("auth.perfil_usuario"))

    return render_template("auth/edit_user.html")


# ============================================================
# 🔑 CAMBIAR CONTRASEÑA SIMPLE
# ============================================================
@auth_bp.route("/cambiar-password", methods=["GET", "POST"])
@login_required
def cambiar_password():
    if request.method == "POST":
        actual = request.form.get("current_password")
        nueva = request.form.get("new_password")
        confirmar = request.form.get("confirm_password")

        if not current_user.check_password(actual):
            flash("La contraseña actual es incorrecta.", "danger")
            return redirect(url_for("auth.cambiar_password"))

        if nueva != confirmar:
            flash("La confirmación no coincide.", "danger")
            return redirect(url_for("auth.cambiar_password"))

        current_user.set_password(nueva)
        db.session.commit()

        flash("Contraseña actualizada.", "success")
        return redirect(url_for("auth.perfil_usuario"))

    return render_template("auth/change_password.html")


# ============================================================
# 🖼 SUBIR FOTO
# ============================================================
@auth_bp.route("/subir-foto", methods=["GET", "POST"])
@login_required
def subir_foto():
    upload_folder = os.path.join(current_app.root_path, "static", "uploads", "users")
    os.makedirs(upload_folder, exist_ok=True)

    if request.method == "POST":
        file = request.files.get("photo")

        if not file:
            flash("No enviaste ninguna imagen.", "danger")
            return redirect(url_for("auth.subir_foto"))

        ext = file.filename.rsplit(".", 1)[-1].lower()
        if ext not in ["jpg", "jpeg", "png"]:
            flash("Formato no válido.", "danger")
            return redirect(url_for("auth.subir_foto"))

        filename = f"user_{current_user.id}.{ext}"
        path = os.path.join(upload_folder, filename)
        file.save(path)

        current_user.photo = f"uploads/users/{filename}"
        db.session.commit()

        flash("Foto actualizada.", "success")
        return redirect(url_for("auth.perfil_usuario"))

    return render_template("auth/upload_photo.html")


# ============================================================
# 📄 REPORTES PDF - VERSIÓN CORREGIDA SIN matplotlib
# ============================================================
@auth_bp.route("/reportes")
@login_required
def reportes_usuario():
    return render_template("auth/reportes_usuario.html")


# ============================================================
# 📄 PDF 1 - GERENCIA - VERSIÓN CORREGIDA
# ============================================================
@auth_bp.route("/descargar-datos")
@login_required
def descargar_datos_gerencia():
    """Descarga el reporte PDF básico del usuario"""
    try:
        print(f"[Básico] Generando reporte para {current_user.id}")
        
        # Primero intentar importar la función simple
        try:
            from utils.pdf_reports_simple import create_simple_pdf_report
            pdf_path = create_simple_pdf_report(current_user.id)
        except ImportError as e:
            print(f"[Básico] Error importando: {e}")
            pdf_path = generate_basic_pdf_fallback(current_user.id)
        
        if not pdf_path or not os.path.exists(pdf_path):
            flash("No se pudo generar el reporte.", "danger")
            return redirect(url_for("auth.perfil_usuario"))
        
        # Nombre del archivo
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"Reporte_Gerdau_{current_user.username}_{timestamp}.pdf"
        
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        print(f"[Básico] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f"Error al generar reporte: {str(e)[:80]}...", "danger")
        return redirect(url_for("auth.perfil_usuario"))


# ============================================================
# 📄 PDF PREMIUM - VERSIÓN MEJORADA
# ============================================================
@auth_bp.route("/descargar-datos-premium")
@auth_bp.route("/descargar-pdf-perfil")
@login_required
def descargar_datos_premium():
    """Descarga el reporte PDF PREMIUM del usuario"""
    try:
        print(f"[Premium] Generando reporte premium para {current_user.id}")
        
        # Intentar importar función premium
        try:
            from utils.pdf_reports_premium import create_premium_pdf_report
            pdf_path = create_premium_pdf_report(current_user.id)
        except ImportError as e:
            print(f"[Premium] Error importando premium: {e}")
            # Si no funciona, usar función local mejorada
            pdf_path = generate_premium_pdf_local(current_user.id)
        
        if not pdf_path or not os.path.exists(pdf_path):
            print(f"[Premium] Error: PDF no generado o no encontrado")
            flash("No se pudo generar el reporte premium.", "danger")
            return redirect(url_for("auth.perfil_usuario"))
        
        # Nombre del archivo
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"Reporte_Premium_{current_user.username}_{timestamp}.pdf"
        
        print(f"[Premium] Enviando PDF: {pdf_path}")
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        print(f"[Premium] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        flash(f"Error al generar reporte premium.", "danger")
        return redirect(url_for("auth.perfil_usuario"))


# ============================================================
# FUNCIONES DE RESPALDO PARA PDFs
# ============================================================

def generate_basic_pdf_fallback(user_id):
    """Función de respaldo para PDF básico"""
    try:
        from models.user import User
        from models.inventory import InventoryItem
        from models.bultos import Bulto
        from models.alerts import Alert
        
        user = User.query.get(user_id)
        if not user:
            return None
        
        # Crear directorio
        reports_dir = os.path.join(current_app.root_path, "static", "temp_pdfs")
        os.makedirs(reports_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        pdf_path = os.path.join(reports_dir, f"basico_{user_id}_{timestamp}.pdf")
        
        # Obtener datos
        kpi_inventarios = InventoryItem.query.count()
        kpi_bultos = Bulto.query.count()
        kpi_alertas = Alert.query.count()
        
        # Crear PDF simple
        from reportlab.lib.pagesizes import letter
        from reportlab.pdfgen import canvas
        from reportlab.lib import colors
        
        c = canvas.Canvas(pdf_path, pagesize=letter)
        width, height = letter
        
        # Encabezado
        c.setFont("Helvetica-Bold", 16)
        c.drawString(50, height - 50, f"Reporte Básico - {user.username}")
        
        c.setFont("Helvetica", 10)
        c.drawString(50, height - 80, f"Correo: {user.email or 'No registrado'}")
        c.drawString(50, height - 100, f"Rol: {getattr(user, 'role', 'Usuario').upper()}")
        
        # Estadísticas
        y = height - 140
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "Estadísticas:")
        
        c.setFont("Helvetica", 10)
        stats = [
            f"Inventarios subidos: {kpi_inventarios}",
            f"Bultos registrados: {kpi_bultos}",
            f"Alertas reportadas: {kpi_alertas}",
        ]
        
        for stat in stats:
            y -= 20
            c.drawString(70, y, stat)
        
        # Pie de página
        c.setFont("Helvetica", 8)
        c.drawString(50, 50, f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        
        c.save()
        return pdf_path
        
    except Exception as e:
        print(f"[Fallback Básico] Error: {e}")
        return None


def generate_premium_pdf_local(user_id):
    """Función local para generar PDF premium"""
    try:
        from models.user import User
        from models.inventory import InventoryItem
        from models.bultos import Bulto
        from models.alerts import Alert
        
        user = User.query.get(user_id)
        if not user:
            return None
        
        # Crear directorio premium
        premium_dir = os.path.join(current_app.root_path, "static", "reports_premium")
        os.makedirs(premium_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        pdf_path = os.path.join(premium_dir, f"premium_{user_id}_{timestamp}.pdf")
        
        # Obtener datos
        kpi_inventarios = InventoryItem.query.count()
        kpi_bultos = Bulto.query.count()
        kpi_alertas = Alert.query.count()
        score = getattr(user, 'score', 0)
        
        # ========== CREAR PDF PREMIUM SIMPLE ==========
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib import colors
        
        c = canvas.Canvas(pdf_path, pagesize=A4)
        width, height = A4
        
        # Colores Gerdau
        gerdau_blue = colors.Color(0/255, 59/255, 113/255)
        gerdau_yellow = colors.Color(248/255, 192/255, 0/255)
        
        # ===== PÁGINA 1: PORTADA =====
        # Fondo
        c.setFillColor(gerdau_blue)
        c.rect(0, 0, width, height, fill=True, stroke=False)
        
        # Título
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 28)
        c.drawCentredString(width/2, height/2 + 50, "REPORTE PREMIUM")
        c.setFont("Helvetica", 18)
        c.drawCentredString(width/2, height/2, "Sistema Warehouse MRO")
        c.drawCentredString(width/2, height/2 - 30, "GERDAU")
        
        # Información usuario
        c.setFont("Helvetica", 14)
        c.drawCentredString(width/2, height/2 - 80, f"Usuario: {user.username}")
        c.drawCentredString(width/2, height/2 - 110, f"Fecha: {datetime.now().strftime('%d/%m/%Y')}")
        
        # Código
        codigo = f"GERDAU-PRM-{user.id:04d}-{timestamp}"
        c.setFont("Helvetica", 10)
        c.drawCentredString(width/2, 100, f"Código: {codigo}")
        
        c.showPage()
        
        # ===== PÁGINA 2: ESTADÍSTICAS =====
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 20)
        c.drawString(50, height - 50, "ESTADÍSTICAS DETALLADAS")
        
        y = height - 100
        c.setFont("Helvetica", 12)
        
        stats = [
            f"• Inventarios subidos: {kpi_inventarios}",
            f"• Bultos registrados: {kpi_bultos}",
            f"• Alertas reportadas: {kpi_alertas}",
            f"• Puntaje técnico: {score} pts",
            f"• Perfil completado: {getattr(user, 'perfil_completado', 0)}%",
            f"• Fecha registro: {user.created_at.strftime('%d/%m/%Y') if user.created_at else 'N/A'}",
        ]
        
        for stat in stats:
            c.drawString(70, y, stat)
            y -= 25
        
        # ===== GRÁFICO SIMPLE =====
        try:
            # Dibujar barras
            bar_start_y = y - 100
            max_value = max(kpi_inventarios, kpi_bultos, kpi_alertas, 1)
            
            # Inventarios
            bar_height = (kpi_inventarios / max_value) * 100
            c.setFillColor(gerdau_blue)
            c.rect(100, bar_start_y, 40, bar_height, fill=True, stroke=True)
            c.setFillColor(colors.black)
            c.setFont("Helvetica", 8)
            c.drawString(100, bar_start_y - 10, f"Inventarios: {kpi_inventarios}")
            
            # Bultos
            bar_height = (kpi_bultos / max_value) * 100
            c.setFillColor(gerdau_yellow)
            c.rect(160, bar_start_y, 40, bar_height, fill=True, stroke=True)
            c.setFillColor(colors.black)
            c.drawString(160, bar_start_y - 10, f"Bultos: {kpi_bultos}")
            
            # Alertas
            bar_height = (kpi_alertas / max_value) * 100
            c.setFillColor(colors.red)
            c.rect(220, bar_start_y, 40, bar_height, fill=True, stroke=True)
            c.setFillColor(colors.black)
            c.drawString(220, bar_start_y - 10, f"Alertas: {kpi_alertas}")
            
        except Exception as e:
            print(f"[PDF Local] Error gráfico: {e}")
        
        # Pie de página
        c.setFont("Helvetica", 8)
        c.setFillColor(colors.gray)
        c.drawString(50, 50, f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        c.drawCentredString(width/2, 50, "Documento confidencial - GERDAU")
        
        c.save()
        
        print(f"[PDF Local Premium] Generado: {pdf_path}")
        return pdf_path
        
    except Exception as e:
        print(f"[generate_premium_pdf_local] Error: {e}")
        import traceback
        traceback.print_exc()
        return None


# ============================================================
# RUTA DE PRUEBA PARA PDF
# ============================================================
@auth_bp.route("/test-pdf")
@login_required
def test_pdf():
    """Ruta de prueba para verificar PDFs"""
    try:
        # Crear un PDF de prueba MUY simple
        from reportlab.pdfgen import canvas
        from io import BytesIO
        
        buffer = BytesIO()
        c = canvas.Canvas(buffer)
        c.drawString(100, 750, f"Test PDF - Usuario: {current_user.username}")
        c.drawString(100, 730, f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        c.save()
        
        buffer.seek(0)
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"test_{current_user.username}.pdf",
            mimetype='application/pdf'
        )
        
    except Exception as e:
        return f"Error: {str(e)}", 500


# ============================================================
# 📄 LISTAR REPORTES GENERADOS (Opcional)
# ============================================================
@auth_bp.route("/mis-reportes")
@login_required
def mis_reportes():
    """Muestra los reportes PDF generados por el usuario"""
    try:
        reports_dir = os.path.join(current_app.root_path, "static", "temp_pdfs")
        if not os.path.exists(reports_dir):
            os.makedirs(reports_dir, exist_ok=True)
        
        # Obtener archivos PDF del usuario
        user_files = []
        for filename in os.listdir(reports_dir):
            if filename.startswith(f"reporte_{current_user.id}_") and filename.endswith(".pdf"):
                filepath = os.path.join(reports_dir, filename)
                stat = os.stat(filepath)
                user_files.append({
                    'name': filename,
                    'path': filepath,
                    'created': datetime.fromtimestamp(stat.st_ctime).strftime('%d/%m/%Y %H:%M'),
                    'size': f"{stat.st_size / 1024:.1f} KB"
                })
        
        # Ordenar por fecha (más reciente primero)
        user_files.sort(key=lambda x: x['created'], reverse=True)
        
        return render_template("auth/mis_reportes.html", reports=user_files)
        
    except Exception as e:
        print(f"[mis_reportes] Error: {e}")
        flash("Error al cargar los reportes.", "danger")
        return redirect(url_for("auth.perfil_usuario"))


# ============================================================
# 🗑 LIMPIAR REPORTES ANTIGUOS (Opcional)
# ============================================================
@auth_bp.route("/limpiar-reportes", methods=["POST"])
@login_required
def limpiar_reportes():
    """Elimina reportes PDF antiguos del usuario"""
    try:
        reports_dir = os.path.join(current_app.root_path, "static", "temp_pdfs")
        if not os.path.exists(reports_dir):
            return redirect(url_for("auth.mis_reportes"))
        
        deleted = 0
        for filename in os.listdir(reports_dir):
            if filename.startswith(f"reporte_{current_user.id}_") and filename.endswith(".pdf"):
                filepath = os.path.join(reports_dir, filename)
                os.remove(filepath)
                deleted += 1
        
        if deleted > 0:
            flash(f"Se eliminaron {deleted} reportes antiguos.", "success")
        else:
            flash("No había reportes para eliminar.", "info")
            
        return redirect(url_for("auth.mis_reportes"))
        
    except Exception as e:
        print(f"[limpiar_reportes] Error: {e}")
        flash("Error al eliminar reportes.", "danger")
        return redirect(url_for("auth.mis_reportes"))

