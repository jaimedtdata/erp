import time
from datetime import datetime, timedelta
from dateutil import relativedelta

import babel

from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval


class HrEmployee(models.Model):

    _inherit = 'hr.employee'
    tablas_tipo_documento_id = fields.Many2one('planilla.tipo.documento', 'Tipo Documento')
    identification_id = fields.Char(string='Identification No', groups='hr.group_hr_user',required=True)
    # tipo_trabajador_id = fields.Many2one('planilla.tipo.trabajador','Tipo Trabajador',required=True)

    
    condicion = fields.Selection([
        ('domiciliado', 'Domiciliado'),
        ('nodomiciliado', 'No Domiciliado'),
    ], string='Condicion', required=True, default='domiciliado', help="Domiciliado o No Domiciliado")

    a_paterno = fields.Char('Apellido Paterno')
    a_materno = fields.Char('Apellido Materno')
    nombres = fields.Char('Nombres') 

    tipo_empresa = fields.Selection([
        ('microempresa', 'Micro empresa'),
        ('pequenhaempresa', 'Pequenha empresa')
    ], string='Tipo Empresa', help="Tipo de empresa")

    @api.onchange('a_paterno','a_materno','nombres')
    def onchange_name_last_fp(self):
        self.name = ( (self.a_paterno if self.a_paterno else '') + " " + (self.a_materno if self.a_materno else '' ) + " " + (self.nombres if self.nombres else '' ) ).strip()