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
@auth_bp.route("/descargar-datos-premium")
@login_required
def descargar_datos_premium():
    """Descarga el reporte PDF PREMIUM del usuario"""
    try:
        print(f"[Premium] Generando reporte premium para {current_user.id}")
        
        # Importar función premium
        try:
            from utils.pdf_reports_premium import create_premium_pdf_report
            pdf_path = create_premium_pdf_report(current_user.id)
        except ImportError as e:
            print(f"[Premium] Error importando: {e}")
            # Fallback a versión simple
            from utils.pdf_reports_simple import create_simple_pdf_report
            pdf_path = create_simple_pdf_report(current_user.id)
        
        if not pdf_path or not os.path.exists(pdf_path):
            flash("No se pudo generar el reporte premium.", "danger")
            return redirect(url_for("auth.perfil_usuario"))
        
        # Nombre del archivo
        timestamp = datetime.now().strftime('%Y%m%d')
        filename = f"Reporte_Premium_{current_user.username}_{timestamp}.pdf"
        
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
        flash(f"Error al generar reporte premium: {str(e)[:80]}...", "danger")
        return redirect(url_for("auth.perfil_usuario"))
# ============================================================
# 📄 PDF 2 - RESUMEN (Alternativo)
# ============================================================
@auth_bp.route("/descargar-resumen")
@login_required
def descargar_resumen():
    """Descarga un resumen simple en PDF"""
    try:
        pdf_path = generate_local_pdf(current_user.id)
        
        if pdf_path and os.path.exists(pdf_path):
            filename = f"Resumen_{current_user.username}_{datetime.now().strftime('%Y%m%d')}.pdf"
            return send_file(
                pdf_path,
                as_attachment=True,
                download_name=filename,
                mimetype='application/pdf'
            )
        
        flash("No se pudo generar el resumen.", "danger")
        return redirect(url_for("auth.perfil_usuario"))
        
    except Exception as e:
        flash(f"Error: {str(e)[:50]}...", "danger")
        return redirect(url_for("auth.perfil_usuario"))


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

