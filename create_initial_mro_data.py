# create_initial_mro_data.py
from app import app
from models import db
from models.scenario_mro import ScenarioMRO
import json

def create_initial_mro_scenarios():
    with app.app_context():
        print("Creando escenarios iniciales MRO...")
        
        # Verificar si ya existen escenarios
        if ScenarioMRO.query.count() > 0:
            print("Ya existen escenarios. Saltando creación inicial.")
            return
        
        # Escenario 1 - Para Aprendices (Inventario)
        scen1 = ScenarioMRO(
            scenario_code="SCEN-MRO-001",
            title="Discrepancia en Conteo de Herramientas",
            description="Durante el conteo en Zona A, encuentras que el sistema marca 15 llaves inglesas, pero físicamente hay 12. El supervisor necesita el reporte en 30 minutos.",
            category="inventario",
            target_roles="aprendiz,tecnico_almacen",
            difficulty=1,
            warehouse_zone="Zona A - Herramientas Manuales",
            material_type="Herramienta",
            criticality="medio",
            sap_transaction="MI04",
            sap_data_json={
                "material": "LLAVE-ING-001",
                "ubicacion": "ZA-12-04",
                "stock_sap": 15,
                "stock_minimo": 5,
                "ultimo_movimiento": "2024-01-10"
            },
            option_a="Ajustar SAP a 12 unidades y continuar sin reportar",
            option_b="Reportar discrepencia al supervisor inmediatamente",
            option_c="Buscar en zonas aledañas antes de reportar",
            correct_option="C",
            points_aprendiz=100,
            points_tecnico=80,
            points_planificador=60,
            feedback_correct="¡Correcto! Siempre debes investigar antes de ajustar.",
            feedback_incorrect="Incorrecto. Ajustar SAP sin investigación oculta problemas.",
            professional_analysis="Las discrepancias requieren investigación completa.",
            sap_procedure="MB51|Ver movimientos|LX03|Verificar ubicaciones|ZM07|Reportar",
            safety_considerations="Usar guantes. Mantener pasillos despejados.",
            key_learning="Nunca ajustes SAP sin investigar primero."
        )
        
        # Escenario 2 - Para Técnicos (Emergencia)
        scen2 = ScenarioMRO(
            scenario_code="SCEN-MRO-002",
            title="Material Crítico con Stock en Cero",
            description="Mantenimiento solicita urgente un rodamiento 6205-ZZ para línea de laminación. SAP muestra stock 0 pero hay 2 unidades en cuarentena. La línea se detiene en 45 minutos.",
            category="emergencia",
            target_roles="tecnico_almacen,planificador",
            difficulty=3,
            warehouse_zone="Zona Crítica - Repuestos",
            material_type="Repuesto",
            criticality="alto",
            sap_transaction="MIGO",
            sap_data_json={
                "material": "ROD-6205-ZZ",
                "stock_sap": 0,
                "stock_fisico_cuarentena": 2,
                "tiempo_reposicion": 30,
                "linea_afectada": "Laminación"
            },
            option_a="Entregar de cuarentena con registro condicional",
            option_b="Decir a mantenimiento que no hay stock disponible",
            option_c="Esperar autorización de calidad (2-3 horas)",
            correct_option="A",
            points_aprendiz=150,
            points_tecnico=120,
            points_planificador=90,
            feedback_correct="¡Bien decidido! En emergencias se prioriza producción.",
            feedback_incorrect="Parar la línea cuesta miles por hora.",
            professional_analysis="Procedimiento de emergencia controlado.",
            sap_procedure="MIGO|Movimiento 343|Comentario 'URGENTE'|Notificar calidad",
            safety_considerations="Verificar estado físico del material.",
            key_learning="Parada de línea > riesgo calidad."
        )
        
        # Escenario 3 - Para Planificadores (Compras)
        scen3 = ScenarioMRO(
            scenario_code="SCEN-MRO-003",
            title="Proveedor Entrega Material Incorrecto",
            description="Un proveedor entrega 50 filtros hidráulicos, pero la factura dice 100. El camión espera para la confirmación de recepción.",
            category="compras",
            target_roles="planificador,supervisor",
            difficulty=4,
            warehouse_zone="Zona Recepción",
            material_type="Consumible",
            criticality="medio",
            sap_transaction="MIGO",
            sap_data_json={
                "material": "FILTRO-HID-305",
                "pedido": 100,
                "proveedor": "Filtros S.A.",
                "unidades_entregadas": 50,
                "estado": "pendiente"
            },
            option_a="Recibir 100 como facturado y pedir el resto después",
            option_b="Rechazar toda la entrega",
            option_c="Recibir 50 y notificar a compras para ajuste",
            correct_option="C",
            points_aprendiz=0,
            points_tecnico=80,
            points_planificador=100,
            feedback_correct="Correcto. La recepción debe reflejar la realidad física.",
            feedback_incorrect="Error contable. El inventario debe coincidir con existencia física.",
            professional_analysis="El almacén recibe material físico, no papel.",
            sap_procedure="MIGO|Cantidad real|Marcar diferencia|Notificar compras",
            safety_considerations="Verificar etiquetas de riesgo químico.",
            key_learning="La cantidad real prevalece sobre documentación."
        )
        
        db.session.add(scen1)
        db.session.add(scen2)
        db.session.add(scen3)
        db.session.commit()
        
        print(f"Creados {ScenarioMRO.query.count()} escenarios MRO iniciales")
        print("Escenarios disponibles:")
        for scen in ScenarioMRO.query.all():
            print(f"  - {scen.scenario_code}: {scen.title} ({scen.target_roles})")

if __name__ == '__main__':
    create_initial_mro_scenarios()
