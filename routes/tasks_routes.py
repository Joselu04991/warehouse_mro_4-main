from datetime import date, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

from models import db
from models.task import Task
from models.user import User
from utils.task_scoring import aplicar_puntaje
from utils.score import reset_score_if_needed

tasks_bp = Blueprint("tasks", __name__, url_prefix="/tasks")

# =========================
# CONFIGURACIÓN DE EMAIL
# =========================
def get_email_config():
    """Obtiene la configuración de email desde variables de entorno"""
    return {
        'SMTP_SERVER': os.environ.get('SMTP_SERVER', 'smtp.gmail.com'),
        'SMTP_PORT': int(os.environ.get('SMTP_PORT', 587)),
        'SENDER_EMAIL': os.environ.get('SMTP_USERNAME', 'tu_correo@gmail.com'),
        'SENDER_PASSWORD': os.environ.get('SMTP_PASSWORD', 'tu_contraseña')
    }


# =========================
# MIS TAREAS
# =========================
@tasks_bp.route("/")
@login_required
def my_tasks():
    reset_score_if_needed(current_user.id)

    tareas = Task.query.filter_by(assigned_to_id=current_user.id).all()
    
    # Calcular días restantes para cada tarea
    for tarea in tareas:
        if tarea.fecha_limite:
            delta = tarea.fecha_limite - date.today()
            tarea.days_left = delta.days
            tarea.is_overdue = delta.days < 0
        else:
            tarea.days_left = 999
            tarea.is_overdue = False
    
    return render_template("tasks/my_tasks.html", tareas=tareas)


# =========================
# FORM CREAR TAREA (GET)
# =========================
@tasks_bp.route("/create", methods=["GET"])
@login_required
def create_task_form():
    if current_user.role not in ["admin", "owner"]:
        flash("No autorizado", "danger")
        return redirect(url_for("tasks.my_tasks"))

    usuarios = User.query.filter(User.status == "active").all()
    return render_template("tasks/create_task.html", usuarios=usuarios)


# =========================
# CREAR TAREA (POST)
# =========================
@tasks_bp.route("/create", methods=["POST"])
@login_required
def create_task():
    if current_user.role not in ["admin", "owner"]:
        flash("No autorizado", "danger")
        return redirect(url_for("tasks.my_tasks"))

    try:
        task = Task(
            titulo=request.form["titulo"],
            descripcion=request.form["descripcion"],
            assigned_to_id=int(request.form["assigned_to"]),
            assigned_by_id=current_user.id,
            fecha_limite=date.fromisoformat(request.form["fecha_limite"])
        )

        db.session.add(task)
        db.session.commit()

        flash("Tarea creada correctamente", "success")
        
        # Opcional: Enviar notificación por email al asignado
        try:
            usuario_asignado = User.query.get(task.assigned_to_id)
            if usuario_asignado and usuario_asignado.email:
                enviar_email_notificacion(
                    usuario_asignado.email,
                    task.titulo,
                    task.descripcion,
                    task.fecha_limite.strftime('%d/%m/%Y')
                )
        except Exception as e:
            print(f"Error enviando notificación de nueva tarea: {e}")
        
        return redirect(url_for("tasks.my_tasks"))
        
    except Exception as e:
        flash(f"Error al crear tarea: {str(e)}", "danger")
        return redirect(url_for("tasks.create_task_form"))


# =========================
# COMPLETAR TAREA
# =========================
@tasks_bp.route("/complete/<int:task_id>")
@login_required
def complete_task(task_id):
    task = Task.query.get_or_404(task_id)

    if task.assigned_to_id != current_user.id:
        flash("No autorizado", "danger")
        return redirect(url_for("tasks.my_tasks"))

    task.estado = "completada"
    task.fecha_completado = date.today()

    aplicar_puntaje(task)

    db.session.commit()
    flash("Tarea completada", "success")
    
    # Opcional: Enviar notificación de completado al supervisor
    try:
        if task.assigned_by_id:
            supervisor = User.query.get(task.assigned_by_id)
            if supervisor and supervisor.email:
                enviar_email_completado(
                    supervisor.email,
                    current_user.username,
                    task.titulo,
                    date.today().strftime('%d/%m/%Y')
                )
    except Exception as e:
        print(f"Error enviando notificación de completado: {e}")
    
    return redirect(url_for("tasks.my_tasks"))


# =========================
# ENVIAR CORREO DE TAREA
# =========================
@tasks_bp.route("/send_task_email", methods=["POST"])
@login_required
def send_task_email():
    try:
        data = request.get_json()
        
        task_id = data.get('task_id')
        recipient_email = data.get('recipient_email', 'jose.castillo@sider.com.pe')
        task_title = data.get('task_title', 'Sin título')
        task_desc = data.get('task_desc', 'Sin descripción')
        task_date = data.get('task_date', 'No especificada')
        task_days = data.get('task_days', '0')
        additional_message = data.get('additional_message', '')
        
        # Configurar estado visual
        if int(task_days) < 0:
            estado = "⏰ VENCIDA"
            color = "#ff416c"
            tipo = "urgent"
        elif int(task_days) <= 3:
            estado = "⚠ Por vencer"
            color = "#f7971e"
            tipo = "warning"
        else:
            estado = "✅ En tiempo"
            color = "#11998e"
            tipo = "normal"
        
        # Crear contenido HTML del correo
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}
                .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }}
                .content {{ padding: 25px; }}
                .task-card {{ background: #f8f9fa; border-radius: 10px; padding: 25px; margin: 20px 0; border-left: 5px solid {color}; }}
                .task-title {{ font-size: 22px; font-weight: bold; color: #2c3e50; margin-bottom: 10px; }}
                .task-detail {{ margin: 8px 0; color: #495057; }}
                .status-badge {{ display: inline-block; padding: 5px 15px; background: {color}; color: white; border-radius: 20px; font-weight: bold; margin-top: 10px; }}
                .footer {{ text-align: center; color: #6c757d; font-size: 12px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e9ecef; }}
                .btn-action {{ display: inline-block; padding: 12px 25px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                            color: white; text-decoration: none; border-radius: 8px; margin-top: 15px; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📋 Recordatorio de Tarea</h1>
                    <p>Sistema de Gestión de Tareas - MRO SIDER</p>
                </div>
                
                <div class="content">
                    <div class="task-card">
                        <div class="task-title">{task_title}</div>
                        <div class="task-detail"><strong>📝 Descripción:</strong> {task_desc}</div>
                        <div class="task-detail"><strong>📅 Fecha límite:</strong> {task_date}</div>
                        <div class="task-detail"><strong>⏳ Días restantes:</strong> {task_days} días</div>
                        <div class="status-badge">{estado}</div>
                    </div>
                    
                    {f'<div style="background: #e8f4fd; padding: 15px; border-radius: 8px; margin: 20px 0;"><strong>💬 Mensaje adicional:</strong><br>{additional_message}</div>' if additional_message else ''}
                    
                    <p style="color: #6c757d; font-size: 14px;">Este es un recordatorio automático del sistema de gestión de tareas MRO.</p>
                    
                    <div style="text-align: center; margin-top: 25px;">
                        <a href="#" class="btn-action">👁️ Ver Tarea en el Sistema</a>
                    </div>
                </div>
                
                <div class="footer">
                    <p>© {datetime.now().year} Sistema MRO SIDER - Este correo fue generado automáticamente</p>
                    <p>Usuario: {current_user.username} | Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Contenido en texto plano (para clientes de email que no soportan HTML)
        text_content = f"""
        RECORDATORIO DE TAREA - SISTEMA MRO
        
        Título: {task_title}
        Descripción: {task_desc}
        Fecha límite: {task_date}
        Días restantes: {task_days} días
        Estado: {estado}
        
        {f'Mensaje adicional: {additional_message}' if additional_message else ''}
        
        Este es un recordatorio automático del sistema de gestión de tareas MRO.
        
        Generado por: {current_user.username}
        Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}
        """
        
        # Configuración de email
        config = get_email_config()
        
        # Crear mensaje
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"📋 Recordatorio: {task_title}"
        msg['From'] = config['SENDER_EMAIL']
        msg['To'] = recipient_email
        msg['X-Priority'] = '1'  # Alta prioridad
        
        # Adjuntar partes
        part1 = MIMEText(text_content, 'plain')
        part2 = MIMEText(html_content, 'html')
        msg.attach(part1)
        msg.attach(part2)
        
        # Enviar correo
        with smtplib.SMTP(config['SMTP_SERVER'], config['SMTP_PORT']) as server:
            server.starttls()
            server.login(config['SENDER_EMAIL'], config['SENDER_PASSWORD'])
            server.send_message(msg)
        
        # Registrar envío en la tarea (opcional)
        if task_id:
            try:
                task = Task.query.get(task_id)
                if task:
                    # Puedes agregar un campo para registrar envíos de email
                    # task.last_email_sent = datetime.now()
                    # db.session.commit()
                    pass
            except:
                pass
        
        return jsonify({
            'success': True,
            'message': f'Correo enviado exitosamente a {recipient_email}'
        })
        
    except Exception as e:
        print(f"Error enviando correo: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =========================
# ENVIAR RESUMEN SEMANAL
# =========================
@tasks_bp.route("/send_weekly_summary", methods=["POST"])
@login_required
def send_weekly_summary():
    try:
        data = request.get_json()
        user_email = data.get('email', current_user.email)
        
        # Obtener tareas del usuario
        tareas = Task.query.filter_by(assigned_to_id=current_user.id).all()
        
        # Calcular estadísticas
        total_tareas = len(tareas)
        tareas_completadas = len([t for t in tareas if t.estado == "completada"])
        tareas_pendientes = total_tareas - tareas_completadas
        
        # Filtrar por estado
        hoy = date.today()
        tareas_vencidas = []
        tareas_por_vencer = []
        
        for t in tareas:
            if t.estado != "completada" and t.fecha_limite:
                delta = (t.fecha_limite - hoy).days
                if delta < 0:
                    tareas_vencidas.append(t)
                elif delta <= 3:
                    tareas_por_vencer.append(t)
        
        # Crear resumen HTML
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }}
                .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 12px; overflow: hidden; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }}
                .stats {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin: 25px 0; }}
                .stat-card {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 3px 10px rgba(0,0,0,0.08); text-align: center; }}
                .stat-value {{ font-size: 32px; font-weight: bold; margin: 10px 0; }}
                .stat-label {{ color: #6c757d; font-size: 14px; text-transform: uppercase; letter-spacing: 1px; }}
                .section {{ margin: 25px 0; }}
                .section-title {{ color: #495057; font-size: 18px; font-weight: bold; margin-bottom: 15px; border-bottom: 2px solid #e9ecef; padding-bottom: 8px; }}
                .task-item {{ background: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 8px; border-left: 4px solid; }}
                .vencida {{ border-left-color: #ff416c; }}
                .por-vencer {{ border-left-color: #f7971e; }}
                .completada {{ border-left-color: #11998e; }}
                .footer {{ text-align: center; color: #6c757d; font-size: 12px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e9ecef; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 Resumen Semanal de Tareas</h1>
                    <p>Usuario: {current_user.username} | Fecha: {hoy.strftime('%d/%m/%Y')}</p>
                </div>
                
                <div class="stats">
                    <div class="stat-card">
                        <div class="stat-value" style="color: #667eea;">{total_tareas}</div>
                        <div class="stat-label">Total Tareas</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" style="color: #11998e;">{tareas_completadas}</div>
                        <div class="stat-label">Completadas</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" style="color: #f7971e;">{tareas_pendientes}</div>
                        <div class="stat-label">Pendientes</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" style="color: #ff416c;">{len(tareas_vencidas)}</div>
                        <div class="stat-label">Vencidas</div>
                    </div>
                </div>
                
                {f'<div class="section"><div class="section-title">⏰ Tareas Vencidas ({len(tareas_vencidas)})</div>{"".join([f"<div class=\"task-item vencida\"><strong>{t.titulo}</strong><br>Vencida el {t.fecha_limite.strftime(\"%d/%m/%Y\")}</div>" for t in tareas_vencidas]) if tareas_vencidas else "<p style=\"color: #6c757d;\">✅ No hay tareas vencidas</p>"}</div>'}
                
                {f'<div class="section"><div class="section-title">⚠ Tareas por Vencer ({len(tareas_por_vencer)})</div>{"".join([f"<div class=\"task-item por-vencer\"><strong>{t.titulo}</strong><br>Vence el {t.fecha_limite.strftime(\"%d/%m/%Y\")} ({(t.fecha_limite - hoy).days} días)</div>" for t in tareas_por_vencer]) if tareas_por_vencer else "<p style=\"color: #6c757d;\">✅ No hay tareas por vencer</p>"}</div>'}
                
                <div class="footer">
                    <p>© {hoy.year} Sistema MRO SIDER - Resumen semanal generado automáticamente</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Enviar correo
        config = get_email_config()
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"📊 Resumen Semanal de Tareas - {hoy.strftime('%d/%m/%Y')}"
        msg['From'] = config['SENDER_EMAIL']
        msg['To'] = user_email
        
        part1 = MIMEText("Resumen semanal de tareas - Ver versión HTML", 'plain')
        part2 = MIMEText(html_content, 'html')
        msg.attach(part1)
        msg.attach(part2)
        
        with smtplib.SMTP(config['SMTP_SERVER'], config['SMTP_PORT']) as server:
            server.starttls()
            server.login(config['SENDER_EMAIL'], config['SENDER_PASSWORD'])
            server.send_message(msg)
        
        return jsonify({
            'success': True,
            'message': f'Resumen semanal enviado a {user_email}'
        })
        
    except Exception as e:
        print(f"Error enviando resumen semanal: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# =========================
# FUNCIONES AUXILIARES DE EMAIL
# =========================
def enviar_email_notificacion(destinatario, titulo, descripcion, fecha_limite):
    """Envía email de notificación de nueva tarea asignada"""
    try:
        config = get_email_config()
        
        html = f"""
        <h2>📋 Nueva Tarea Asignada</h2>
        <p>Se te ha asignado una nueva tarea en el sistema MRO:</p>
        <div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">
            <strong>{titulo}</strong><br>
            {descripcion}<br>
            <strong>Fecha límite:</strong> {fecha_limite}
        </div>
        """
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"📋 Nueva Tarea: {titulo}"
        msg['From'] = config['SENDER_EMAIL']
        msg['To'] = destinatario
        
        text = f"Nueva tarea asignada: {titulo}\nDescripción: {descripcion}\nFecha límite: {fecha_limite}"
        
        msg.attach(MIMEText(text, 'plain'))
        msg.attach(MIMEText(html, 'html'))
        
        with smtplib.SMTP(config['SMTP_SERVER'], config['SMTP_PORT']) as server:
            server.starttls()
            server.login(config['SENDER_EMAIL'], config['SENDER_PASSWORD'])
            server.send_message(msg)
            
    except Exception as e:
        print(f"Error enviando notificación: {e}")


def enviar_email_completado(destinatario, usuario, titulo, fecha_completado):
    """Envía email de notificación de tarea completada"""
    try:
        config = get_email_config()
        
        html = f"""
        <h2>✅ Tarea Completada</h2>
        <p>El usuario <strong>{usuario}</strong> ha completado una tarea:</p>
        <div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">
            <strong>{titulo}</strong><br>
            <strong>Completado el:</strong> {fecha_completado}
        </div>
        """
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"✅ Tarea Completada: {titulo}"
        msg['From'] = config['SENDER_EMAIL']
        msg['To'] = destinatario
        
        text = f"Tarea completada por {usuario}: {titulo}\nFecha: {fecha_completado}"
        
        msg.attach(MIMEText(text, 'plain'))
        msg.attach(MIMEText(html, 'html'))
        
        with smtplib.SMTP(config['SMTP_SERVER'], config['SMTP_PORT']) as server:
            server.starttls()
            server.login(config['SENDER_EMAIL'], config['SENDER_PASSWORD'])
            server.send_message(msg)
            
    except Exception as e:
        print(f"Error enviando notificación de completado: {e}")


# =========================
# RANKING TÉCNICOS
# =========================
@tasks_bp.route("/ranking")
@login_required
def ranking():
    usuarios = (
        User.query
        .filter(User.score.isnot(None))
        .order_by(User.score.desc())
        .all()
    )
    return render_template("tasks/ranking.html", usuarios=usuarios)
