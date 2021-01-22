import time
from datetime import datetime, timedelta
from dateutil import relativedelta

import babel

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval


'''
result = contract.wage + payslip.planilla_afiliacion_line_id.search([['periodo_id.code','=',payslip.periodo_id.code],['planilla_afiliacion_id.entidad','=',contract.afiliacion_id.entidad]]).fondo
'''


class hr_salary_rule(models.Model):

    _inherit = 'hr.salary.rule'
    code = fields.Char(required=True, index=True)# reescribiendo el codigo de arriba
    cod_sunat = fields.Char("Codigo Sunat")
    is_subtotal = fields.Boolean("Es un Subtotal")

    # @api.onchange('code')
    # @api.depends('code')
    # def contraint_code(self):
    #     line = self.env['hr.salary.rule'].search(
    #         [('code', '=', self.code)])
    #     if line:
    #         raise ValidationError(
    #             "la regla salarial %s ya existe" % self.code)


    @api.multi
    def write(self,vals):
        self.ensure_one()
        line=False
        if 'code' in vals:
            line = self.env['hr.salary.rule'].search(
                [('code', '=', vals['code'])])
        if line:
            raise ValidationError(
                "la regla salarial %s ya existe" % vals['code'])
        t = super(hr_salary_rule, self).write(vals)
        return t

class hr_salary_rule_line(models.Model):

    _inherit = 'hr.payslip.line'
    is_subtotal_ref = fields.Boolean(
        "Es un Subtotal", related="salary_rule_id.is_subtotal")
