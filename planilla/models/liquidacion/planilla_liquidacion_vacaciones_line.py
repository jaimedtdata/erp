# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.addons.base.res.res_request import referenceable_models
from datetime import datetime


class PlanillaVacacionesLine(models.Model):
    _name = 'planilla.liquidacion.vacaciones.line'

    planilla_liquidacion_id = fields.Many2one(
        'planilla.liquidacion', "Planilla Liquidacion")
    employee_id = fields.Integer(index=True)
    contract_id =  fields.Many2one(
        'hr.contract', "Planilla Contrato")
    identification_number = fields.Char("Nro Documento", size=9)
    last_name_father = fields.Char("Apellido Paterno")
    last_name_mother = fields.Char("Apellido Materno")
    names = fields.Char("Nombres")
    fecha_ingreso = fields.Date("Fecha Ingreso")
    fecha_computable = fields.Date("Fecha Computo")
    fecha_cese = fields.Date("Fecha Cese")
    faltas = fields.Integer("Faltas")
    basico = fields.Float(u"Básico", digits=(10, 2))
    comision = fields.Float(u"Comision", digits=(10, 2))
    bonificacion = fields.Float(u"Bonificación", digits=(10, 2))
    horas_extras_mean = fields.Float("Prom. Hras extras", digits=(10, 2))
    remuneracion_computable = fields.Float("Rem. Com.", digits=(10, 2))
    meses = fields.Integer("Meses")
    dias = fields.Integer("Dias")
    monto_x_mes = fields.Float("M. por Mes", digits=(10, 2))
    monto_x_dia = fields.Float(u"M. por Día", digits=(10, 2))
    vacaciones_devengadas = fields.Float(
        u"Vacaciones\n Devengadas", digits=(10, 2))
    vacaciones_truncas = fields.Float(u"Vacaciones\n truncas", digits=(10, 2))
    total_vacaciones = fields.Float(u"Total\n vacaciones", digits=(10, 2))
    onp = fields.Float(u"ONP", digits=(10, 2))
    afp_jub = fields.Float(u"AFP JUB", digits=(10, 2))
    afp_si = fields.Float(u"AFP SI", digits=(10, 2))
    afp_com = fields.Float(u"AFP COM", digits=(10, 2))
    neto_total = fields.Float(u"Neto Total", digits=(10, 2))

    @api.onchange('vacaciones_devengadas', 'vacaciones_truncas')
    def _recalcula_cts(self):
        self.total_vacaciones = self.vacaciones_devengadas+self.vacaciones_truncas
