# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime

class EpsBase(models.Model):

    _name = 'eps.base'

    name = fields.Char('Identificador')
    period = fields.Char('Periodo')
    line_ids = fields.One2many('eps.base.line', 'eps_base_id', string='Lineas de EPS', ondelete='cascade')

	# @api.model
	# def create(self,vals):
	# 	return super(HrControlVacaciones,self).create(vals)

class EpsLine(models.Model):

    _name = 'eps.base.line'

    name = fields.Char('Identificador')
    period = fields.Char('Periodo')
    eps_base_id = fields.Many2one('eps.base')
    dni = fields.Integer(string='DNI')
    employee_id = fields.Many2one('hr.employee','Apellidos y Nombres')
    plan = fields.Char('Plan')
    base_afecta = fields.Float("Base Afecta ESSALUD")
    aporte_essalud = fields.Float("Aporte ESSALUD")
    credito_eps = fields.Float("Crédito EPS")
    costo = fields.Float("Costo")
    descuento = fields.Float("Descuento")

