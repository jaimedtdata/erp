# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
import logging


class PayslipExt(models.Model):
    _inherit = 'hr.payslip'

    descuento_eps = fields.Float("Descuento EPS", readonly=True)