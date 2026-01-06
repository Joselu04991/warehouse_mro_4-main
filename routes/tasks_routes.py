from datetime import date, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import time

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
    try:
        return {
            'SMTP_SERVER': 'smtp.office365.com',
            'SMTP_PORT': 587,
            'SENDER_EMAIL': os.environ.get('OUTLOOK_EMAIL', ''),
            'SENDER_PASSWORD': os.environ.get('OUTLOOK_PASSWORD', '')
        }
    except:
        return None


# =========================
# FUNCIÓN SEGURA PARA ENVIAR EMAILS
# =========================
def send_email_safe(destinatario, asunto, contenido_texto, contenido_html=None):
    """Envía un email de manera segura con manejo de errores"""
    try:
        config = get_email_config()
        
        # Si no hay configuración de email, retornar sin error
        if not config or not config['SENDER_EMAIL'] or not config['SENDER_PASSWORD']:
            print("⚠️ Configuración de email no encontrada. Saltando envío de email.")
            return True
            
        msg = MIMEMultipart('alternative')
        msg['Subject'] = asunto
        msg['From'] = config['SENDER_EMAIL']
        msg['To'] = destinatario
        
        # Adjuntar texto plano
        msg.attach(MIMEText(contenido_texto, 'plain', 'utf-8'))
        
        # Si hay contenido HTML, adjuntarlo también
        if contenido_html:
            msg.attach(MIMEText(contenido_html, 'html', 'utf-8'))
        
        # Enviar con timeout
        with smtplib.SMTP(config['SMTP_SERVER'], config['SMTP_PORT'], timeout=10) as server:
            server.starttls()
            server.login(config['SENDER_EMAIL'], config['SENDER_PASSWORD'])
            server.send_message(msg)
        
        print(f"✅ Email enviado a {destinatario}")
        return True
        
    except Exception as e:
        print(f"⚠️ Error enviando email a {destinatario}: {str(e)}")
        return False


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
# CREAR TAREA (POST) - VERSIÓN SIMPLIFICADA
# =========================
@tasks_bp.route("/create", methods=["POST"])
@login_required
def create_task():
    if current_user.role not in ["admin", "owner"]:
        flash("No autorizado", "danger")
        return redirect(url_for("tasks.my_tasks"))

    try:
        # Crear la tarea primero
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
        
        # Intentar enviar notificación en segundo plano (no bloqueante)
        try:
            usuario_asignado = User.query.get(task.assigned_to_id)
            if usuario_asignado and usuario_asignado.email:
                # Preparar contenido del email
                asunto = f"📋 Nueva Tarea: {task.titulo}"
                texto = f"""NUEVA TAREA ASIGNADA

Se le ha asignado una nueva tarea por {current_user.username}:

Título: {task.titulo}
Descripción: {task.descripcion}
Fecha límite: {task.fecha_limite.strftime('%d/%m/%Y')}

Por favor, revise y complete la tarea antes de la fecha límite.

Sistema de Gestión MRO
SIDER PERÚ"""
                
                html = f"""<div style="font-family: Arial, sans-serif; max-width: 600px;">
                    <div style="background: #0056b3; color: white; padding: 20px; text-align: center;">
                        <h2 style="margin: 0;">📋 Nueva Tarea Asignada</h2>
                    </div>
                    <div style="padding: 25px;">
                        <p>Estimado colaborador,</p>
                        <p><strong>{current_user.username}</strong> le ha asignado una nueva tarea:</p>
                        <div style="background: #f8f9fa; border: 1px solid #dee2e6; padding: 20px; margin: 20px 0; border-radius: 4px;">
                            <h3 style="color: #0056b3; margin-top: 0;">{task.titulo}</h3>
                            <p><strong>Descripción:</strong> {task.descripcion}</p>
                            <p><strong>Fecha límite:</strong> {task.fecha_limite.strftime('%d/%m/%Y')}</p>
                        </div>
                        <p>Por favor, revise y complete la tarea antes de la fecha límite.</p>
                        <p>Atentamente,<br><strong>Sistema de Gestión MRO</strong><br>SIDER PERÚ</p>
                    </div>
                </div>"""
                
                # Enviar email de manera segura (no bloquea si falla)
                send_email_safe(usuario_asignado.email, asunto, texto, html)
                
        except Exception as e:
            print(f"⚠️ Error en notificación de nueva tarea: {e}")
            # No hacemos flash para no interrumpir el flujo principal
        
        return redirect(url_for("tasks.my_tasks"))
        
    except Exception as e:
        db.session.rollback()
        flash(f"Error al crear tarea: {str(e)}", "danger")
        return redirect(url_for("tasks.create_task_form"))


# =========================
# COMPLETAR TAREA - VERSIÓN SIMPLIFICADA
# =========================
@tasks_bp.route("/complete/<int:task_id>")
@login_required
def complete_task(task_id):
    task = Task.query.get_or_404(task_id)

    if task.assigned_to_id != current_user.id:
        flash("No autorizado", "danger")
        return redirect(url_for("tasks.my_tasks"))

    try:
        task.estado = "completada"
        task.fecha_completado = date.today()
        aplicar_puntaje(task)
        db.session.commit()
        
        flash("Tarea completada", "success")
        
        # Intentar enviar notificación en segundo plano
        try:
            if task.assigned_by_id:
                supervisor = User.query.get(task.assigned_by_id)
                if supervisor and supervisor.email:
                    asunto = f"✅ Tarea Completada: {task.titulo}"
                    texto = f"""TAREA COMPLETADA

El usuario {current_user.username} ha completado una tarea:

Título: {task.titulo}
Completado el: {date.today().strftime('%d/%m/%Y')}

La tarea ha sido marcada como completada en el sistema.

Sistema de Gestión MRO
SIDER PERÚ"""
                    
                    html = f"""<div style="font-family: Arial, sans-serif; max-width: 600px;">
                        <div style="background: #28a745; color: white; padding: 20px; text-align: center;">
                            <h2 style="margin: 0;">✅ Tarea Completada</h2>
                        </div>
                        <div style="padding: 25px;">
                            <p>Estimado supervisor,</p>
                            <p>El usuario <strong>{current_user.username}</strong> ha completado una tarea:</p>
                            <div style="background: #f8f9fa; border: 1px solid #d4edda; padding: 20px; margin: 20px 0; border-radius: 4px;">
                                <h3 style="color: #28a745; margin-top: 0;">{task.titulo}</h3>
                                <p><strong>Completado el:</strong> {date.today().strftime('%d/%m/%Y')}</p>
                            </div>
                            <p>La tarea ha sido marcada como completada en el sistema.</p>
                            <p>Atentamente,<br><strong>Sistema de Gestión MRO</strong><br>SIDER PERÚ</p>
                        </div>
                    </div>"""
                    
                    send_email_safe(supervisor.email, asunto, texto, html)
                    
        except Exception as e:
            print(f"⚠️ Error en notificación de tarea completada: {e}")
        
        return redirect(url_for("tasks.my_tasks"))
        
    except Exception as e:
        db.session.rollback()
        flash(f"Error al completar tarea: {str(e)}", "danger")
        return redirect(url_for("tasks.my_tasks"))


# =========================
# ENVIAR CORREO DE TAREA (Individual) - VERSIÓN SIMPLIFICADA
# =========================
@tasks_bp.route("/send_task_email", methods=["POST"])
@login_required
def send_task_email():
    try:
        data = request.get_json()
        
        recipient_email = data.get('recipient_email', 'jose.castillo@sider.com.pe')
        task_title = data.get('task_title', 'Sin título')
        task_desc = data.get('task_desc', 'Sin descripción')
        task_date = data.get('task_date', 'No especificada')
        task_days = data.get('task_days', '0')
        additional_message = data.get('additional_message', '')
        
        # Determinar estado
        dias = int(task_days) if task_days else 0
        if dias < 0:
            estado = "⏰ VENCIDA"
            color = "#d9534f"
            icon = "⏰"
        elif dias <= 3:
            estado = "⚠ Por vencer"
            color = "#f0ad4e"
            icon = "⚠"
        else:
            estado = "✅ En tiempo"
            color = "#5cb85c"
            icon = "✅"
        
        # Crear contenido del email
        asunto = f"{icon} Recordatorio: {task_title}"
        
        texto = f"""RECORDATORIO DE TAREA

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
        
        html = f"""<div style="font-family: Arial, sans-serif; max-width: 600px;">
            <div style="background: #0056b3; color: white; padding: 20px; text-align: center;">
                <h1 style="margin: 0; font-size: 24px;">{icon} Recordatorio de Tarea</h1>
                <p style="margin: 5px 0 0 0;">Sistema de Gestión MRO - SIDER PERÚ</p>
            </div>
            <div style="padding: 30px;">
                <div style="text-align: center; margin-bottom: 20px;">
                    <strong style="color: #0056b3; font-size: 18px;">SIDER PERÚ</strong>
                </div>
                <p>Estimado usuario,</p>
                <p>Le recordamos la siguiente tarea pendiente en el sistema:</p>
                <div style="background: #f8f9fa; border: 1px solid #dee2e6; border-left: 5px solid {color}; padding: 20px; margin: 25px 0; border-radius: 4px;">
                    <div style="font-size: 20px; font-weight: 600; color: #0056b3; margin-bottom: 15px;">{task_title}</div>
                    <div style="margin: 10px 0; color: #495057;"><strong>Descripción:</strong> {task_desc}</div>
                    <div style="margin: 10px 0; color: #495057;"><strong>Fecha límite:</strong> {task_date}</div>
                    <div style="margin: 10px 0; color: #495057;"><strong>Días restantes:</strong> {task_days} días</div>
                    <div style="display: inline-block; padding: 6px 12px; background: {color}; color: white; border-radius: 4px; font-weight: 600; font-size: 14px; margin-top: 10px;">{estado}</div>
                </div>
                {f'<div style="background: #e8f4fd; border: 1px solid #b6d4fe; padding: 15px; border-radius: 4px; margin: 20px 0;"><strong>Mensaje adicional:</strong><br>{additional_message}</div>' if additional_message else ''}
                <p style="font-size: 14px; color: #6c757d;">Este es un recordatorio automático del sistema de gestión de tareas MRO.</p>
                <p>Atentamente,<br><strong>Sistema de Gestión MRO</strong><br>SIDER PERÚ</p>
            </div>
            <div style="text-align: center; color: #6c757d; font-size: 12px; margin-top: 30px; padding-top: 20px; border-top: 1px solid #e9ecef;">
                <p>© {datetime.now().year} SIDER PERÚ - Sistema de Gestión MRO</p>
                <p>Usuario: {current_user.username} | Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}</p>
                <p><small>Este correo fue generado automáticamente. Por favor no responder.</small></p>
            </div>
        </div>"""
        
        # Enviar email de manera segura
        success = send_email_safe(recipient_email, asunto, texto, html)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Correo enviado exitosamente a {recipient_email}'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No se pudo enviar el correo. Verifique la configuración de email.'
            })
        
    except Exception as e:
        print(f"Error en send_task_email: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error: {str(e)}'
        }), 500


# =========================
# ENVIAR RESUMEN SEMANAL - VERSIÓN SIMPLIFICADA
# =========================
@tasks_bp.route("/send_weekly_summary", methods=["POST"])
@login_required
def send_weekly_summary():
    try:
        data = request.get_json()
        user_email = data.get('email', current_user.email)
        
        # Obtener estadísticas
        tareas = Task.query.filter_by(assigned_to_id=current_user.id).all()
        
        hoy = date.today()
        total = len(tareas)
        completadas = len([t for t in tareas if t.estado == "completada"])
        pendientes = total - completadas
        
        vencidas = []
        por_vencer = []
        
        for t in tareas:
            if t.estado != "completada" and t.fecha_limite:
                delta = (t.fecha_limite - hoy).days
                if delta < 0:
                    vencidas.append(t)
                elif delta <= 3:
                    por_vencer.append(t)
        
        # Crear contenido del email
        asunto = f"📊 Resumen Semanal de Tareas - {hoy.strftime('%d/%m/%Y')}"
        
        texto = f"""RESUMEN SEMANAL DE TAREAS

Usuario: {current_user.username}
Fecha: {hoy.strftime('%d/%m/%Y')}

ESTADÍSTICAS:
Total tareas: {total}
Completadas: {completadas}
Pendientes: {pendientes}
Vencidas: {len(vencidas)}
Por vencer: {len(por_vencer)}

TAREAS VENCIDAS:"""
        
        for t in vencidas:
            texto += f"\n- {t.titulo} (vencida el {t.fecha_limite.strftime('%d/%m/%Y')})"
        
        texto += "\n\nTAREAS POR VENCER:"
        for t in por_vencer:
            dias = (t.fecha_limite - hoy).days
            texto += f"\n- {t.titulo} (vence el {t.fecha_limite.strftime('%d/%m/%Y')}, en {dias} días)"
        
        texto += f"""

---
SIDER PERÚ
Sistema de Gestión MRO
Resumen generado automáticamente"""
        
        html = f"""<div style="font-family: Arial, sans-serif; max-width: 600px;">
            <div style="background: #0056b3; color: white; padding: 20px; text-align: center;">
                <h1 style="margin: 0; font-size: 24px;">📊 Resumen Semanal de Tareas</h1>
                <p style="margin: 5px 0 0 0;">Usuario: {current_user.username} | Fecha: {hoy.strftime('%d/%m/%Y')}</p>
            </div>
            <div style="padding: 30px;">
                <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin: 25px;">
                    <div style="background: white; padding: 20px; border-radius: 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; border: 1px solid #dee2e6;">
                        <div style="font-size: 28px; font-weight: 600; color: #0056b3;">{total}</div>
                        <div style="color: #6c757d; font-size: 12px; text-transform: uppercase;">Total Tareas</div>
                    </div>
                    <div style="background: white; padding: 20px; border-radius: 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; border: 1px solid #dee2e6;">
                        <div style="font-size: 28px; font-weight: 600; color: #5cb85c;">{completadas}</div>
                        <div style="color: #6c757d; font-size: 12px; text-transform: uppercase;">Completadas</div>
                    </div>
                    <div style="background: white; padding: 20px; border-radius: 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; border: 1px solid #dee2e6;">
                        <div style="font-size: 28px; font-weight: 600; color: #f0ad4e;">{pendientes}</div>
                        <div style="color: #6c757d; font-size: 12px; text-transform: uppercase;">Pendientes</div>
                    </div>
                    <div style="background: white; padding: 20px; border-radius: 4px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); text-align: center; border: 1px solid #dee2e6;">
                        <div style="font-size: 28px; font-weight: 600; color: #d9534f;">{len(vencidas)}</div>
                        <div style="color: #6c757d; font-size: 12px; text-transform: uppercase;">Vencidas</div>
                    </div>
                </div>
                <div style="margin: 25px;">
                    <div style="color: #0056b3; font-size: 16px; font-weight: 600; margin-bottom: 15px; padding-bottom: 8px; border-bottom: 2px solid #e9ecef;">⏰ Tareas Vencidas ({len(vencidas)})</div>
                    {"".join([f'<div style="background: #fdf7f7; padding: 15px; margin: 10px 0; border-radius: 4px; border-left: 4px solid #d9534f; font-size: 14px;"><strong>{t.titulo}</strong><br>Vencida el {t.fecha_limite.strftime("%d/%m/%Y")} (hace {abs((t.fecha_limite - hoy).days)} días)</div>' for t in vencidas]) if vencidas else '<p style="color: #6c757d; font-size: 14px;">✅ No hay tareas vencidas</p>'}
                </div>
                <div style="margin: 25px;">
                    <div style="color: #0056b3; font-size: 16px; font-weight: 600; margin-bottom: 15px; padding-bottom: 8px; border-bottom: 2px solid #e9ecef;">⚠ Tareas por Vencer ({len(por_vencer)})</div>
                    {"".join([f'<div style="background: #fcf8f3; padding: 15px; margin: 10px 0; border-radius: 4px; border-left: 4px solid #f0ad4e; font-size: 14px;"><strong>{t.titulo}</strong><br>Vence el {t.fecha_limite.strftime("%d/%m/%Y")} (en {(t.fecha_limite - hoy).days} días)</div>' for t in por_vencer]) if por_vencer else '<p style="color: #6c757d; font-size: 14px;">✅ No hay tareas por vencer</p>'}
                </div>
            </div>
            <div style="text-align: center; color: #6c757d; font-size: 12px; margin: 30px 25px 0; padding: 20px 0; border-top: 1px solid #e9ecef;">
                <p>© {hoy.year} SIDER PERÚ - Sistema de Gestión MRO</p>
                <p><small>Resumen semanal generado automáticamente. Por favor no responder.</small></p>
            </div>
        </div>"""
        
        # Enviar email de manera segura
        success = send_email_safe(user_email, asunto, texto, html)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Resumen semanal enviado a {user_email}'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'No se pudo enviar el correo. Verifique la configuración de email.'
            })
        
    except Exception as e:
        print(f"Error en send_weekly_summary: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Error: {str(e)}'
        }), 500


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
