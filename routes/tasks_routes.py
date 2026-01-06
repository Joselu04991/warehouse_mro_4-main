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
# CONFIGURACIÓN DE OUTLOOK/OFFICE 365
# =========================
def get_email_config():
    """Obtiene la configuración de email para Outlook/Office 365"""
    return {
        'SMTP_SERVER': 'smtp.office365.com',
        'SMTP_PORT': 587,
        'SENDER_EMAIL': os.environ.get('OUTLOOK_EMAIL', 'tu_correo@sider.com.pe'),
        'SENDER_PASSWORD': os.environ.get('OUTLOOK_PASSWORD', 'tu_contraseña')
    }


# =========================
# MIS TAREAS
# =========================
@tasks_bp.route("/")
@login_required
def my_tasks():
    reset_score_if_needed(current_user.id)

    tareas = Task.query.filter_by(assigned_to_id=current_user.id).all()
    
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
        
        try:
            usuario_asignado = User.query.get(task.assigned_to_id)
            if usuario_asignado and usuario_asignado.email:
                enviar_email_nueva_tarea(
                    usuario_asignado.email,
                    task.titulo,
                    task.descripcion,
                    task.fecha_limite.strftime('%d/%m/%Y'),
                    current_user.username
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
    
    try:
        if task.assigned_by_id:
            supervisor = User.query.get(task.assigned_by_id)
            if supervisor and supervisor.email:
                enviar_email_tarea_completada(
                    supervisor.email,
                    current_user.username,
                    task.titulo,
                    date.today().strftime('%d/%m/%Y')
                )
    except Exception as e:
        print(f"Error enviando notificación de completado: {e}")
    
    return redirect(url_for("tasks.my_tasks"))


# =========================
# ENVIAR CORREO DE TAREA (Individual)
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
        
        if int(task_days) < 0:
            estado = "⏰ VENCIDA"
            color = "#d9534f"
            icon = "⏰"
        elif int(task_days) <= 3:
            estado = "⚠ Por vencer"
            color = "#f0ad4e"
            icon = "⚠"
        else:
            estado = "✅ En tiempo"
            color = "#5cb85c"
            icon = "✅"
        
        # Usar triple comillas para evitar problemas con escapes
        html_content = f'''<!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Recordatorio de Tarea - MRO SIDER</title>
            <style>
                body {{ 
                    font-family: 'Segoe UI', 'Calibri', Arial, sans-serif; 
                    margin: 0; 
                    padding: 0; 
                    background-color: #f5f5f5; 
                    color: #333333; 
                }}
                .container {{ 
                    max-width: 600px; 
                    margin: 0 auto; 
                    background: #ffffff; 
                }}
                .header {{ 
                    background: #0056b3; 
                    color: white; 
                    padding: 25px; 
                    text-align: center; 
                }}
                .header h1 {{ 
                    margin: 0; 
                    font-size: 24px; 
                    font-weight: 300; 
                }}
                .content {{ 
                    padding: 30px; 
                    line-height: 1.6; 
                }}
                .task-card {{ 
                    background: #f8f9fa; 
                    border: 1px solid #dee2e6; 
                    border-left: 5px solid {color}; 
                    padding: 20px; 
                    margin: 25px 0; 
                    border-radius: 4px; 
                }}
                .task-title {{ 
                    font-size: 20px; 
                    font-weight: 600; 
                    color: #0056b3; 
                    margin-bottom: 15px; 
                }}
                .task-detail {{ 
                    margin: 10px 0; 
                    color: #495057; 
                }}
                .status-badge {{ 
                    display: inline-block; 
                    padding: 6px 12px; 
                    background: {color}; 
                    color: white; 
                    border-radius: 4px; 
                    font-weight: 600; 
                    font-size: 14px; 
                    margin-top: 10px; 
                }}
                .footer {{ 
                    text-align: center; 
                    color: #6c757d; 
                    font-size: 12px; 
                    margin-top: 30px; 
                    padding-top: 20px; 
                    border-top: 1px solid #e9ecef; 
                }}
                .message-box {{ 
                    background: #e8f4fd; 
                    border: 1px solid #b6d4fe; 
                    padding: 15px; 
                    border-radius: 4px; 
                    margin: 20px 0; 
                }}
                .logo {{ 
                    text-align: center; 
                    margin-bottom: 20px; 
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>{icon} Recordatorio de Tarea</h1>
                    <p style="margin: 5px 0 0 0; opacity: 0.9;">Sistema de Gestión MRO - SIDER PERÚ</p>
                </div>
                
                <div class="content">
                    <div class="logo">
                        <strong style="color: #0056b3; font-size: 18px;">SIDER PERÚ</strong>
                    </div>
                    
                    <p>Estimado usuario,</p>
                    <p>Le recordamos la siguiente tarea pendiente en el sistema:</p>
                    
                    <div class="task-card">
                        <div class="task-title">{task_title}</div>
                        <div class="task-detail"><strong>Descripción:</strong> {task_desc}</div>
                        <div class="task-detail"><strong>Fecha límite:</strong> {task_date}</div>
                        <div class="task-detail"><strong>Días restantes:</strong> {task_days} días</div>
                        <div class="status-badge">{estado}</div>
                    </div>
                    
                    {f'<div class="message-box"><strong>Mensaje adicional:</strong><br>{additional_message}</div>' if additional_message else ''}
                    
                    <p style="font-size: 14px; color: #6c757d;">
                        Este es un recordatorio automático del sistema de gestión de tareas MRO. 
                        Por favor, revise y complete la tarea antes de la fecha límite.
                    </p>
                    
                    <p>Atentamente,<br>
                    <strong>Sistema de Gestión MRO</strong><br>
                    SIDER PERÚ</p>
                </div>
                
                <div class="footer">
                    <p>© {datetime.now().year} SIDER PERÚ - Sistema de Gestión MRO</p>
                    <p>Usuario: {current_user.username} | Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
                    <p><small>Este correo fue generado automáticamente. Por favor no responder.</small></p>
                </div>
            </div>
        </body>
        </html>'''
        
        text_content = f"""RECORDATORIO DE TAREA - SISTEMA MRO SIDER

Título: {task_title}
Descripción: {task_desc}
Fecha límite: {task_date}
Días restantes: {task_days} días
Estado: {estado}

{f'Mensaje adicional: {additional_message}' if additional_message else ''}

Este es un recordatorio automático del sistema de gestión de tareas MRO.

Generado por: {current_user.username}
Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}

---
SIDER PERÚ
Sistema de Gestión MRO"""
        
        config = get_email_config()
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"{icon} Recordatorio: {task_title}"
        msg['From'] = config['SENDER_EMAIL']
        msg['To'] = recipient_email
        msg['X-Priority'] = '1'
        msg['Importance'] = 'High'
        
        part1 = MIMEText(text_content, 'plain', 'utf-8')
        part2 = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(part1)
        msg.attach(part2)
        
        with smtplib.SMTP(config['SMTP_SERVER'], config['SMTP_PORT']) as server:
            server.starttls()
            server.login(config['SENDER_EMAIL'], config['SENDER_PASSWORD'])
            server.send_message(msg)
        
        print(f"Correo enviado exitosamente a {recipient_email}")
        
        return jsonify({
            'success': True,
            'message': f'Correo enviado exitosamente a {recipient_email}'
        })
        
    except Exception as e:
        print(f"Error enviando correo: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error al enviar correo: {str(e)}'
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
        
        tareas = Task.query.filter_by(assigned_to_id=current_user.id).all()
        
        total_tareas = len(tareas)
        tareas_completadas = len([t for t in tareas if t.estado == "completada"])
        tareas_pendientes = total_tareas - tareas_completadas
        
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
        
        # Construir sección de tareas vencidas
        tareas_vencidas_html = ""
        if tareas_vencidas:
            for t in tareas_vencidas:
                dias_pasados = abs((t.fecha_limite - hoy).days)
                tareas_vencidas_html += f'<div class="task-item vencida"><strong>{t.titulo}</strong><br>Vencida el {t.fecha_limite.strftime("%d/%m/%Y")} (hace {dias_pasados} días)</div>'
        else:
            tareas_vencidas_html = '<p style="color: #6c757d; font-size: 14px;">✅ No hay tareas vencidas</p>'
        
        # Construir sección de tareas por vencer
        tareas_por_vencer_html = ""
        if tareas_por_vencer:
            for t in tareas_por_vencer:
                dias_restantes = (t.fecha_limite - hoy).days
                tareas_por_vencer_html += f'<div class="task-item por-vencer"><strong>{t.titulo}</strong><br>Vence el {t.fecha_limite.strftime("%d/%m/%Y")} (en {dias_restantes} días)</div>'
        else:
            tareas_por_vencer_html = '<p style="color: #6c757d; font-size: 14px;">✅ No hay tareas por vencer</p>'
        
        html_content = f'''<!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Resumen Semanal - MRO SIDER</title>
            <style>
                body {{ 
                    font-family: 'Segoe UI', 'Calibri', Arial, sans-serif; 
                    margin: 0; 
                    padding: 0; 
                    background-color: #f5f5f5; 
                    color: #333333; 
                }}
                .container {{ 
                    max-width: 600px; 
                    margin: 0 auto; 
                    background: #ffffff; 
                }}
                .header {{ 
                    background: #0056b3; 
                    color: white; 
                    padding: 25px; 
                    text-align: center; 
                }}
                .header h1 {{ 
                    margin: 0; 
                    font-size: 24px; 
                    font-weight: 300; 
                }}
                .stats {{ 
                    display: grid; 
                    grid-template-columns: repeat(2, 1fr); 
                    gap: 15px; 
                    margin: 25px; 
                }}
                .stat-card {{ 
                    background: white; 
                    padding: 20px; 
                    border-radius: 4px; 
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1); 
                    text-align: center; 
                    border: 1px solid #dee2e6; 
                }}
                .stat-value {{ 
                    font-size: 28px; 
                    font-weight: 600; 
                    margin: 10px 0; 
                }}
                .stat-label {{ 
                    color: #6c757d; 
                    font-size: 12px; 
                    text-transform: uppercase; 
                    letter-spacing: 0.5px; 
                }}
                .section {{ 
                    margin: 25px; 
                }}
                .section-title {{ 
                    color: #0056b3; 
                    font-size: 16px; 
                    font-weight: 600; 
                    margin-bottom: 15px; 
                    padding-bottom: 8px; 
                    border-bottom: 2px solid #e9ecef; 
                }}
                .task-item {{ 
                    background: #f8f9fa; 
                    padding: 15px; 
                    margin: 10px 0; 
                    border-radius: 4px; 
                    border-left: 4px solid; 
                    font-size: 14px; 
                }}
                .vencida {{ 
                    border-left-color: #d9534f; 
                    background: #fdf7f7; 
                }}
                .por-vencer {{ 
                    border-left-color: #f0ad4e; 
                    background: #fcf8f3; 
                }}
                .footer {{ 
                    text-align: center; 
                    color: #6c757d; 
                    font-size: 12px; 
                    margin: 30px 25px 0; 
                    padding: 20px 0; 
                    border-top: 1px solid #e9ecef; 
                }}
                .logo {{ 
                    text-align: center; 
                    margin: 20px 0; 
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>📊 Resumen Semanal de Tareas</h1>
                    <p style="margin: 5px 0 0 0; opacity: 0.9;">Usuario: {current_user.username} | Fecha: {hoy.strftime('%d/%m/%Y')}</p>
                </div>
                
                <div class="logo">
                    <strong style="color: #0056b3; font-size: 18px;">SIDER PERÚ - Sistema MRO</strong>
                </div>
                
                <div class="stats">
                    <div class="stat-card">
                        <div class="stat-value" style="color: #0056b3;">{total_tareas}</div>
                        <div class="stat-label">Total Tareas</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" style="color: #5cb85c;">{tareas_completadas}</div>
                        <div class="stat-label">Completadas</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" style="color: #f0ad4e;">{tareas_pendientes}</div>
                        <div class="stat-label">Pendientes</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" style="color: #d9534f;">{len(tareas_vencidas)}</div>
                        <div class="stat-label">Vencidas</div>
                    </div>
                </div>
                
                <div class="section">
                    <div class="section-title">⏰ Tareas Vencidas ({len(tareas_vencidas)})</div>
                    {tareas_vencidas_html}
                </div>
                
                <div class="section">
                    <div class="section-title">⚠ Tareas por Vencer ({len(tareas_por_vencer)})</div>
                    {tareas_por_vencer_html}
                </div>
                
                <div class="footer">
                    <p>© {hoy.year} SIDER PERÚ - Sistema de Gestión MRO</p>
                    <p><small>Resumen semanal generado automáticamente. Por favor no responder.</small></p>
                </div>
            </div>
        </body>
        </html>'''
        
        config = get_email_config()
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"📊 Resumen Semanal de Tareas - {hoy.strftime('%d/%m/%Y')}"
        msg['From'] = config['SENDER_EMAIL']
        msg['To'] = user_email
        msg['X-Priority'] = '1'
        
        part1 = MIMEText("Resumen semanal de tareas - Ver versión HTML", 'plain', 'utf-8')
        part2 = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(part1)
        msg.attach(part2)
        
        with smtplib.SMTP(config['SMTP_SERVER'], config['SMTP_PORT']) as server:
            server.starttls()
            server.login(config['SENDER_EMAIL'], config['SENDER_PASSWORD'])
            server.send_message(msg)
        
        print(f"Resumen semanal enviado a {user_email}")
        
        return jsonify({
            'success': True,
            'message': f'Resumen semanal enviado a {user_email}'
        })
        
    except Exception as e:
        print(f"Error enviando resumen semanal: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error al enviar resumen: {str(e)}'
        }), 500


# =========================
# FUNCIONES AUXILIARES DE EMAIL (OUTLOOK)
# =========================
def enviar_email_nueva_tarea(destinatario, titulo, descripcion, fecha_limite, asignador):
    """Envía email de notificación de nueva tarea asignada"""
    try:
        config = get_email_config()
        
        html = f'''<div style="font-family: 'Segoe UI', Calibri, Arial, sans-serif; max-width: 600px;">
            <div style="background: #0056b3; color: white; padding: 20px; text-align: center;">
                <h2 style="margin: 0; font-weight: 300;">📋 Nueva Tarea Asignada</h2>
            </div>
            <div style="padding: 25px;">
                <p>Estimado colaborador,</p>
                <p><strong>{asignador}</strong> le ha asignado una nueva tarea:</p>
                
                <div style="background: #f8f9fa; border: 1px solid #dee2e6; padding: 20px; margin: 20px 0; border-radius: 4px;">
                    <h3 style="color: #0056b3; margin-top: 0;">{titulo}</h3>
                    <p><strong>Descripción:</strong> {descripcion}</p>
                    <p><strong>Fecha límite:</strong> {fecha_limite}</p>
                </div>
                
                <p>Por favor, revise y complete la tarea antes de la fecha límite.</p>
                
                <p>Atentamente,<br>
                <strong>Sistema de Gestión MRO</strong><br>
                SIDER PERÚ</p>
            </div>
        </div>'''
        
        text = f"""NUEVA TAREA ASIGNADA - SISTEMA MRO

Se le ha asignado una nueva tarea por {asignador}:

Título: {titulo}
Descripción: {descripcion}
Fecha límite: {fecha_limite}

Por favor, revise y complete la tarea antes de la fecha límite.

Sistema de Gestión MRO
SIDER PERÚ"""
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"📋 Nueva Tarea: {titulo}"
        msg['From'] = config['SENDER_EMAIL']
        msg['To'] = destinatario
        msg['X-Priority'] = '1'
        
        msg.attach(MIMEText(text, 'plain', 'utf-8'))
        msg.attach(MIMEText(html, 'html', 'utf-8'))
        
        with smtplib.SMTP(config['SMTP_SERVER'], config['SMTP_PORT']) as server:
            server.starttls()
            server.login(config['SENDER_EMAIL'], config['SENDER_PASSWORD'])
            server.send_message(msg)
            
        print(f"Notificación de nueva tarea enviada a {destinatario}")
            
    except Exception as e:
        print(f"Error enviando notificación de nueva tarea: {e}")


def enviar_email_tarea_completada(destinatario, usuario, titulo, fecha_completado):
    """Envía email de notificación de tarea completada"""
    try:
        config = get_email_config()
        
        html = f'''<div style="font-family: 'Segoe UI', Calibri, Arial, sans-serif; max-width: 600px;">
            <div style="background: #28a745; color: white; padding: 20px; text-align: center;">
                <h2 style="margin: 0; font-weight: 300;">✅ Tarea Completada</h2>
            </div>
            <div style="padding: 25px;">
                <p>Estimado supervisor,</p>
                <p>El usuario <strong>{usuario}</strong> ha completado una tarea:</p>
                
                <div style="background: #f8f9fa; border: 1px solid #d4edda; padding: 20px; margin: 20px 0; border-radius: 4px;">
                    <h3 style="color: #28a745; margin-top: 0;">{titulo}</h3>
                    <p><strong>Completado el:</strong> {fecha_completado}</p>
                </div>
                
                <p>La tarea ha sido marcada como completada en el sistema.</p>
                
                <p>Atentamente,<br>
                <strong>Sistema de Gestión MRO</strong><br>
                SIDER PERÚ</p>
            </div>
        </div>'''
        
        text = f"""TAREA COMPLETADA - SISTEMA MRO

El usuario {usuario} ha completado una tarea:

Título: {titulo}
Completado el: {fecha_completado}

La tarea ha sido marcada como completada en el sistema.

Sistema de Gestión MRO
SIDER PERÚ"""
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"✅ Tarea Completada: {titulo}"
        msg['From'] = config['SENDER_EMAIL']
        msg['To'] = destinatario
        
        msg.attach(MIMEText(text, 'plain', 'utf-8'))
        msg.attach(MIMEText(html, 'html', 'utf-8'))
        
        with smtplib.SMTP(config['SMTP_SERVER'], config['SMTP_PORT']) as server:
            server.starttls()
            server.login(config['SENDER_EMAIL'], config['SENDER_PASSWORD'])
            server.send_message(msg)
            
        print(f"Notificación de tarea completada enviada a {destinatario}")
            
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
