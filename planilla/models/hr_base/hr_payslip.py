import time
from datetime import datetime, timedelta
from dateutil import relativedelta

import babel

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_RIGHT, TA_LEFT


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'
    _description = 'Pay Slip'

    payslip_run_id = fields.Many2one('hr.payslip.run', string='Payslip Batches', readonly=True,
                                     copy=False, states={
                                         'draft': [('readonly', False)]},
                                     ondelete='cascade'
                                     )

    line_ids = fields.One2many('hr.payslip.line', 'slip_id', string='Payslip Lines', readonly=True,
                               states={'draft': [('readonly', False)]}, domain=[('appears_on_payslip', '=', True)])

    feriados = fields.Integer("Feriados y Domingos")
    dias_calendarios = fields.Integer(
        'Dias Calendarios')

    # variables que se usaran en la nomina
    basico = fields.Float(string='Basico', digits=(12, 2))
    asignacion_familiar = fields.Float(
        string='Asignacion Familiar', digits=(12, 2))
    bonificacion_9 = fields.Float(string='Bonificacion 9%', digits=(12, 2))
    dias_faltas = fields.Float(string='Faltas', digits=(12, 2))
    comisiones = fields.Float(string='Comisiones', digits=(12, 2))
    bonificaciones = fields.Float(string='Bonificaciones', digits=(12, 2))
    sobretiempos = fields.Float(string='sobretiempos', digits=(12, 2))

    basico_cts = fields.Float(string='Basico CTS', digits=(12, 2))
    asignacion_familiar_cts = fields.Float(
        string='Asignacion Familiar CTS', digits=(12, 2))
    dias_faltas_cts = fields.Float(string='Faltas CTS', digits=(12, 2))
    sobretiempos_cts = fields.Float(string='sobretiempos CTS', digits=(12, 2))

    afiliacion_rel = fields.Char(
        'Afiliacion', related='contract_id.afiliacion_id.entidad')

    @api.multi
    def action_payslip_cancel(self):
        self.line_ids.unlink()
        return super(HrPayslip, self).action_payslip_cancel()

    @api.multi
    def imprimir_boleta(self):
        self.ensure_one()
        payslip = self
        planilla_ajustes = self.env['planilla.ajustes'].search([], limit=1)

        archivo_pdf = SimpleDocTemplate(
            "planilla_tmp.pdf", pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=20)

        elements = []
        company = payslip.company_id.partner_id
        categories = self.env['hr.salary.rule.category'].search(
            [('aparece_en_nomina', '=', True)], order="secuencia")
        print "mis codigos ", planilla_ajustes.cod_dias_no_laborados.codigo
        dias_no_laborados = int(payslip.worked_days_line_ids.search(
            [('code', '=', planilla_ajustes.cod_dias_no_laborados.codigo if planilla_ajustes else ''), ('payslip_id', '=', payslip.id)], limit=1).number_of_days)
        print "mi payslip_run ", payslip
        print "mis dias no laborados ", dias_no_laborados
        print "mis dias calendarios ", str(
            payslip.dias_calendarios), " fin "
        dias_laborados = int(payslip.dias_calendarios-dias_no_laborados)
        dias_subsidiados = int(payslip.worked_days_line_ids.search(
            [('code', '=', planilla_ajustes.cod_dias_subsidiados.codigo if planilla_ajustes else ''), ('payslip_id', '=', payslip.id)]).number_of_days)

        query_horas_sobretiempo = '''
        select sum(number_of_days) as dias ,sum(number_of_hours) as horas ,sum(minutos) as minutos from hr_payslip_worked_days
        where (code = 'HE25' OR code = 'HE35' or code = 'HE100')
        and payslip_id=%d
        ''' % (payslip.id)

        self.env.cr.execute(query_horas_sobretiempo)
        # str(int(self.env.cr.dictfetchone()['horas']))
        total_sobretiempo = self.env.cr.dictfetchone()

        dias_faltas = self.env['hr.payslip.worked_days'].search(
            [('code', '=', planilla_ajustes.cod_dias_no_laborados.codigo if planilla_ajustes else ''), ('payslip_id', '=', payslip.id)], limit=1)
        print "MIS HORAS SOBRETIEMPO ", query_horas_sobretiempo
        # formula para los dias laborados segun sunat
        total_horas_jornada_ordinaria = int(
            30-payslip.feriados-dias_faltas.number_of_days if dias_faltas else 0)*8

        print dias_laborados, dias_no_laborados, dias_subsidiados, total_horas_jornada_ordinaria, total_sobretiempo,

        # busco cualquier campo ya que lo unico que quiero es usar la funcionalidad de la generacion de la boleta
        payslip_run = self.env['hr.payslip.run']

        payslip_run.genera_boleta_empleado(self.date_from, self.date_to, payslip.employee_id, str(dias_no_laborados), str(dias_laborados), str(total_horas_jornada_ordinaria), (total_sobretiempo), str(dias_subsidiados), elements,
                                           company, categories, planilla_ajustes)

        archivo_pdf.build(elements)

        import sys
        reload(sys)
        sys.setdefaultencoding('iso-8859-1')
        import os
        vals = {
            'output_name': 'Boleta-%s.pdf' % (payslip.employee_id.name+'-'+payslip.date_from+'-'+payslip.date_to),
            'output_file': open("planilla_tmp.pdf", "rb").read().encode("base64"),
        }
        sfs_id = self.env['planilla.export.file'].create(vals)
        return {
            "type": "ir.actions.act_window",
            "res_model": "planilla.export.file",
            "views": [[False, "form"]],
            "res_id": sfs_id.id,
            "target": "new",
        }

    @api.multi
    def reabrir(self):
        self.state = 'draft'

    '''
    hr_payroll_account crea asientos contables
    estoy sobrescribiendo la funcion
    para que no escriba los asientos contables y vaya directo al padre
    y solo genere las hojas
    '''
    @api.multi
    def action_payslip_done(self):
        if self.line_ids:
            self.line_ids.unlink()
        self.compute_sheet()
        return self.write({'state': 'done'})

    @api.multi
    def compute_sheet(self):
        print("Reescribiendo compute_sheet")
        super(HrPayslip, self).compute_sheet()

        # parametros_gratificacion = self.env['planilla.gratificacion'].search(
        #     [], limit=1).get_parametros_gratificacion()
        # self.basico = self.line_ids.search(
        #     [('code', '=', parametros_gratificacion.cod_basico.code), ('slip_id', '=', self.id)], limit=1).total
        # self.asignacion_familiar = self.line_ids.search(
        #     [('code', '=', parametros_gratificacion.cod_asignacion_familiar.code), ('slip_id', '=', self.id)], limit=1).total
        # self.bonificacion_9 = self.line_ids.search(
        #     [('code', '=', parametros_gratificacion.cod_bonificacion_9.code), ('slip_id', '=', self.id)], limit=1).total
        # self.dias_faltas = self.worked_days_line_ids.search(
        #     [('code', '=', parametros_gratificacion.cod_dias_faltas.codigo), ('payslip_id', '=', self.id)], limit=1).number_of_days
        # self.comisiones = self.line_ids.search(
        #     [('code', '=', parametros_gratificacion.cod_comisiones.code), ('slip_id', '=', self.id)], limit=1).total
        # self.bonificaciones = self.line_ids.search(
        #     [('code', '=', parametros_gratificacion.cod_bonificaciones.code), ('slip_id', '=', self.id)], limit=1).total
        # self.sobretiempos = self.line_ids.search(
        #     [('code', '=', parametros_gratificacion.cod_sobretiempos.code), ('slip_id', '=', self.id)], limit=1).total

        # parametros_cts = self.env['planilla.cts'].search(
        #     [], limit=1).get_parametros_cts()
        # self.basico_cts = self.line_ids.search(
        #     [('code', '=', parametros_cts.cod_basico.code), ('slip_id', '=', self.id)], limit=1).total
        # self.asignacion_familiar_cts = self.line_ids.search(
        #     [('code', '=', parametros_cts.cod_asignacion_familiar.code), ('slip_id', '=', self.id)], limit=1).total

        # self.dias_faltas_cts = self.worked_days_line_ids.search(
        #     [('code', '=', parametros_cts.cod_dias_faltas.codigo), ('payslip_id', '=', self.id)]).number_of_days

        # self.sobretiempos_cts = self.line_ids.search(
        #     [('code', '=', parametros_cts.cod_sobretiempos.code), ('slip_id', '=', self.id)], limit=1).total



    @api.multi
    def load_entradas_tareos(self):
        #import pudb; pudb.set_trace()

        self.worked_days_line_ids.unlink()
        self.input_line_ids.unlink()

        inputs = self.env['planilla.inputs.nomina'].search([])
        worked_days = self.env['planilla.worked.days'].search([])

        for worked_day in worked_days:
            data = {'name': worked_day.descripcion,
                    'payslip_id': self.id,
                    'code': worked_day.codigo,
                    'number_of_days': worked_day.dias,
                    'number_of_hours': worked_day.horas,
                    'minutos': worked_day.minutos,
                    'tasa': worked_day.tasa_monto,
                    'contract_id': self.contract_id.id,
                    }
            self.env['hr.payslip.worked_days'].create(data)

        for my_input in inputs:
            data = {'name': my_input.descripcion,
                    'payslip_id': self.id,
                    'code': my_input.codigo,
                    'amount': 0,
                    'contract_id': self.contract_id.id,
                    }
            self.env['hr.payslip.input'].create(data)

    # name = fields.Char(string='Description', required=True)
    # payslip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade', index=True)
    # sequence = fields.Integer(required=True, index=True, default=10)
    # code = fields.Char(required=True, help="The code that can be used in the salary rules")
    # amount = fields.Float(help="It is used in computation. For e.g. A rule for sales having "
    #                            "1% commission of basic salary for per product can defined in expression "
    #                            "like result = inputs.SALEURO.amount * contract.wage*0.01.")
    # contract_id = fields.Many2one('hr.contract', string='Contract', required=True,
    #     help="The contract for which applied this input")

    # name = fields.Char(string='Description', required=True)
    # payslip_id = fields.Many2one('hr.payslip', string='Pay Slip', required=True, ondelete='cascade', index=True)
    # sequence = fields.Integer(required=True, index=True, default=10)
    # code = fields.Char(required=True, help="The code that can be used in the salary rules")
    # number_of_days = fields.Float(string='Number of Days')
    # number_of_hours = fields.Float(string='Number of Hours')
    # contract_id = fields.Many2one('hr.contract', string='Contract', required=True,
    #     help="The contract for which applied this input")


# class HrPayslipGratificacion(models.Model):
#     _inherit = 'planilla.gratificacion.params.dic'
#     _description = 'gratificacion de la nomina'
#     # variables que se usaran en la nomina
#     slip_id=fields.Many2one('hr.payslip')
#     basico = fields.Float(string='Basico', digits=(12, 2))
#     asignacion_familiar = fields.Float(
#         string='Asignacion Familiar', digits=(12, 2))
#     bonificacion_9 = fields.Float(string='Bonificacion 9%', digits=(12, 2))
#     dias_faltas = fields.Float(string='Faltas', digits=(12, 2))

# class HrPayslipGratificacion(models.Model):
#     _inherit = 'planilla.gratificacion.params.dic'
#     _description = 'gratificacion de la nomina'
#     # variables que se usaran en la nomina
#     slip_id=fields.Many2one('hr.payslip')
#     basico = fields.Float(string='Basico', digits=(12, 2))
#     asignacion_familiar = fields.Float(
#         string='Asignacion Familiar', digits=(12, 2))
#     bonificacion_9 = fields.Float(string='Bonificacion 9%', digits=(12, 2))
#     dias_faltas = fields.Float(string='Faltas', digits=(12, 2))
