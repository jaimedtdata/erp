# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _
import logging
_logger = logging.getLogger(__name__)
from odoo.exceptions import ValidationError


class hr_contract(models.Model):

    _inherit = 'hr.contract'
    _description = 'Employee Contract'

    afiliacion_id = fields.Many2one(
        'planilla.afiliacion', 'AFP', required=True)
    distribucion_analitica_id = fields.Many2one(
        'planilla.distribucion.analitica', string='Distribucion Gastos', required=True)

    cuspp = fields.Char("CUSPP")

    tipo_comision = fields.Selection(
        string=u'Tipo de Comision',
        selection=[(1, 'Flujo'), (2, 'Mixta')]
    )

    situacion_id = fields.Many2one(
        'planilla.situacion', string="Situacion", required=True)
    tipo_trabajador_id = fields.Many2one(
        'planilla.tipo.trabajador', string="Tipo trabajador", required=True)

    tipo_suspension_id = fields.Many2one(
        'planilla.tipo.suspension', string="Tipo suspension")
    motivo = fields.Char("Motivo")
    nro_dias = fields.Char("N° dias")
    otros_5ta_categoria = fields.Char(
        "Otros empleadores por Rentas de 5ta categorías")

    regimen_laboral = fields.Selection(
        string=u'Régimen Laboral',
        index=True,
        selection=[
            ('N', 'N'),
            ('C', 'C'),
            ('M', 'M'),
            ('P', 'P')
        ],
        help="""
            N - Dependiente Normal\n
            C - Dependiente Construccion\n
            M - Dependiente Mineria\n
            P - Dependiente Pesqueria        
        """,
        default='N'
    )

    excepcion_aportador = fields.Selection(
        string=u'Excepcion Aportador',
        index=True,
        selection=[
            ('L', 'L'),
            ('U', 'U'),
            ('J', 'J'),
            ('I', 'I'),
            ('P', 'P'),
            ('O', 'O')
        ],
        help="""L - No corresponde aportar debido a LICENCIA sin renumeracion \n
             U - No corresponde aportar porque existe un subsidio pagado directamente por essalud y en el mes no hubo remuneracion pagada por el empleador \n
             J - No corresponde aportar porque el trabajador se encuentra jubilado \n
             I - No corresponde aportar porque el trabajador pensionado por invalidez en el mes \n
             P - No corresponde aportar debido a que la relacion laboral se iicio en el mes despues del cierre de planillas , el aporte del mes se incluira en el mes siguiente  \n
             O - No corresponde aportar debido a otro motivo , no hubo remuneracion en el mes
        """
    )

    tipo_seguro = fields.Selection(
        string=u'Tipo Seguro',
        index=True,
        selection=[
            ('essalud', 'EsSalud'),
            ('eps', 'EPS'),
        ],
        help="""
        """,
        default='essalud',
        required=True
    )

    @api.model
    def exist_contract(self, employee, date_from, date_to):

        # a contract is valid if it ends between the given dates
        clause_1 = ['&', ('date_end', '<=', date_to),
                    ('date_end', '>=', date_from)]
        # OR if it starts between the given dates
        clause_2 = ['&', ('date_start', '<=', date_to),
                    ('date_start', '>=', date_from)]
        # OR if it starts before the date_from and finish after the date_end (or never finish)
        clause_3 = ['&', ('date_start', '<=', date_from), '|',
                    ('date_end', '=', False), ('date_end', '>=', date_to)]
        clause_final = [('employee_id', '=', employee), '|',
                        '|'] + clause_1 + clause_2 + clause_3
        dat = self.env['hr.contract'].search(clause_final)
        return dat

    @api.model
    def exist_contract_with_id(self, employee, date_from, date_to, id):
        # a contract is valid if it ends between the given dates
        clause_1 = ['&', ('date_end', '<=', date_to),
                    ('date_end', '>=', date_from)]
        # OR if it starts between the given dates
        clause_2 = ['&', ('date_start', '<=', date_to),
                    ('date_start', '>=', date_from)]
        # OR if it starts before the date_from and finish after the date_end (or never finish)
        clause_3 = ['&', ('date_start', '<=', date_from), '|',
                    ('date_end', '=', False), ('date_end', '>=', date_to)]

        clause_final = [('employee_id', '=', employee), ('id',
                                                         '!=', id), '|', '|'] + clause_1 + clause_2 + clause_3
        dat = self.env['hr.contract'].search(clause_final)
        return dat

    @api.multi
    def write(self, vals):
        date_start = vals['date_start'] if 'date_start' in vals else self.date_start
        date_end = vals['date_end'] if 'date_end' in vals else self.date_end
        employee_id = vals['employee_id'] if 'employee_id' in vals else self.employee_id.id

        if not date_end:


            dat = self.env['hr.contract'].search([('employee_id', '=', employee_id), ('id', '!=', self.id), 
            ('date_start', '>=', date_start),('date_end', '=', False)  ])

            if dat:
                raise ValidationError(
                    _('La fecha del contrato se esta intersecando con otro rango de fechas del empleado (%s - %s)' % (dat.date_start, dat.date_end)))
                return False

            dat = self.env['hr.contract'].search([('employee_id', '=', employee_id), ('id', '!=', self.id), 
            ('date_start', '<=', date_start),('date_end', '=', False)  ])

            if dat:
                raise ValidationError(
                    _('La fecha del contrato se esta intersecando con otro rango de fechas del empleado (%s - %s)' % (dat.date_start, dat.date_end)))
                return False

            dat = self.env['hr.contract'].search([('employee_id', '=', employee_id), ('id', '!=', self.id), 
            ('date_start', '<=', date_start), ('date_end', '>=', date_start)])
            if dat:
                raise ValidationError(
                    _('La fecha del contrato se esta intersecando con otro rango de fechas del empleado (%s - %s)' % (dat.date_start, dat.date_end)))
                return False

        num_row = self.exist_contract_with_id(
            employee_id, date_start, date_end, self.id)

        if len(num_row) > 0:
            raise ValidationError(
                _('La fecha del contrato se esta intersecando con otro rango de fechas del empleado (%s - %s)' % (num_row.date_start, num_row.date_end)))
            return False
        return super(hr_contract, self).write(vals)

    @api.model
    def create(self, vals):

        num_row = self.exist_contract(
            vals['employee_id'], vals['date_start'], vals['date_end'])

        if len(num_row) > 0:
            raise ValidationError(
                _('El empleado ya tiene un contrato en las fechas %s %s ') % (vals['date_start'], vals['date_end']))
            return False
        return super(hr_contract, self).create(vals)

    @api.multi
    def copy(self, default=None):
        default = dict(default or {})
        default.update({'date_start': '1000-01-01', 'date_end': ''})
        default_return_value = super(hr_contract, self).copy(default)
        return default_return_value
