# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import datetime
import logging



class ProjectExt(models.Model):
    _inherit = 'hr.control.vacaciones.line'

    total = fields.Integer('Total', compute="_get_total_days", readonly=True)
    sald_sugerido = fields.Integer('Saldo Sugerido', compute="_get_sal_sugerido", readonly=True)
    fecha_inicio = fields.Char('Fecha de Inicio', compute="_get_fecha_inicio", readonly=True)

    def _get_fecha_inicio(self):
        for i in self:
            i.fecha_inicio = str(i.employee_id.contract_id.date_start)
            
    def _get_sal_sugerido(self):
        for i in self:
            calculo = fields.Datetime.from_string(str(i.employee_id.contract_id.date_start)) - datetime.now()
            i.sald_sugerido = int(calculo.days * -2.5 / 30)

    @api.model
    def _get_total_days(self):
        for i in self:
            try:
                i.total = i.saldo_vacaciones - i.dias_gozados
            except:
                i.total = 0

    @api.onchange('saldo_vacaciones', 'dias_gozados')
    def _onchange_total(self):
        try:
            self.total = self.saldo_vacaciones - self.dias_gozados
        except:
            self.total = 0

        
