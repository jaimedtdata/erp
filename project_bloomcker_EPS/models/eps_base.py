# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime

class EpsBase(models.Model):

    _name = 'eps.base'

    name = fields.Char('Identificador')
    period = fields.Date('Fecha Desde', required=True)
    nomina = fields.Many2one('hr.payslip.run', required=True)
    line_ids = fields.One2many('eps.base.line', 'eps_base_id', string='Lineas de EPS', ondelete='cascade')
    porcentaje_aporte = fields.Float("Aporte ESSALUD (%)", default=9)
    porcentaje_credito = fields.Float("Crédito ESSALUD (%)", default=25)
    porcentaje_descuento = fields.Float("Descuento ESSALUD (%)", default=18)

    def get_lines(self):

        if self.line_ids:
			self.line_ids.unlink()

        base = 0
        for i in self.nomina.slip_ids:
            for j in i.line_ids:
                if j.code == "AESSALUD":
                    base = j.total

            vals = {
                'eps_base_id':self.id,
                'dni':i.employee_id.identification_id,
                'employee_id':i.employee_id.id,
                'period':i.date_from,
                'base_afecta':base,
            }
            self.env['eps.base.line'].create(vals)

class EpsLine(models.Model):

    _name = 'eps.base.line'

    name = fields.Char('Identificador')
    period = fields.Date('Periodo')
    eps_base_id = fields.Many2one('eps.base', readonly=True)
    dni = fields.Integer(string='DNI')
    employee_id = fields.Many2one('hr.employee','Apellidos y Nombres')
    plan = fields.Char('Plan')
    base_afecta = fields.Float("Base Afecta ESSALUD")
    aporte_essalud = fields.Float("Aporte ESSALUD", compute="_get_amounts")
    credito_eps = fields.Float("Crédito EPS", compute="_get_amounts")
    costo = fields.Float("Costo", default=0)
    descuento = fields.Float("Descuento", compute="_get_amounts")

    def _get_amounts(self):
        for i in self:
            i.aporte_essalud = i.base_afecta*i.eps_base_id.porcentaje_aporte/100
            i.credito_eps = i.base_afecta*i.eps_base_id.porcentaje_credito*i.eps_base_id.porcentaje_aporte/10000
            i.descuento = (i.costo - i.credito_eps)*(1 + i.eps_base_id.porcentaje_descuento/100)