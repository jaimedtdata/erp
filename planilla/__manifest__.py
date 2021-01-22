
# -*- coding: utf-8 -*-
{
    'name': "Modulo de planilla",
    'category': 'planilla',
    'author': 'ITGRUPO-OPCIONAL-RRHH-COMPATIBLE-BO',
    'depends': ['hr_payroll', 'hr_payroll_account'],
    'version': '1.0',
    'description': """
    - Agregado tabla de afiliacion
    - Agregado tabla de parametros
    """,
    'data': [
        'security/ir.model.access.csv',
        'views/planilla_menu.xml',
        'views/planilla_afiliacion_view.xml',
        'views/ajustes/planilla_ajustes_view.xml',
        'views/hr_base/hr_contract_view.xml',
        'views/hr_base/hr_salary_rule.xml',
        'views/hr_base/hr_payslip_view.xml',
        'views/hr_base/hr_payslip_run_view.xml',
        'views/hr_base/hr_payslip_worked_days.xml',
        'views/hr_base/hr_salary_rule_category.xml',
        'views/hr_base/hr_employee.xml',
        'views/planilla_afiliacion_line.xml',
        'views/planilla_afiliacion_action_server.xml',
        'views/planilla_worked_days_view.xml',
        'views/planilla_inputs_nomina_view.xml',
        'views/planilla_distribucion_analitica.xml',
        'views/planilla_tabular_view.xml',
        'views/importdata/planilla_import_worked_days.xml',
        'views/exportdata/planilla_export_file.xml',
        'wizards/planilla_afiliacion_line_wizard.xml',
        'wizards/planilla_actualizar_afps_wizard.xml',
        'wizards/planilla_tabular_wizard.xml',
        'wizards/planilla_liquidacion_pdf_wizard.xml',
        'views/popup/custom_popup.xml',
        'views/planilla_gratificacion_view.xml',
        'views/ajustes/planilla_parametros_gratificacion.xml',
        'views/ajustes/planilla_parametros_cts.xml',
        'views/ajustes/planilla_parametros_essalud_eps.xml',
        'views/ajustes/planilla_parametros_liquidacion.xml',
        'views/planilla_cts_view.xml',
        'views/tablas/planilla_tipo_documento_view.xml',
        'views/tablas/planilla_situacion_view.xml',
        'views/tablas/planilla_tipo_suspension_view.xml',
        'views/tablas/planilla_tipo_trabajador_view.xml',
        'views/contabilidad/planilla_detalle_linea_nomina_view.xml',
        'views/contabilidad/planilla_asiento_resumen_view.xml',
        'views/contabilidad/planilla_detalle_asiento_distribuido.xml',
        'views/contabilidad/planilla_asiento_distribuido.xml',
        'views/contabilidad/planilla_asiento_contable_view.xml',
        'views/liquidacion/planilla_liquidacion_view.xml',
        'views/liquidacion/planilla_liquidacion_cts_view.xml',
        'views/liquidacion/planilla_liquidacion_gratificacion_view.xml',
        'views/liquidacion/planilla_liquidacion_vacaciones_view.xml',


    ],
    'demo': [   ],
    'application': True,
}