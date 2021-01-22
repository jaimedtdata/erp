# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _
from datetime import date, datetime
from odoo.exceptions import ValidationError, UserError
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.units import inch
from reportlab.lib.colors import magenta, red, black, blue, gray, Color, HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Paragraph, Table, PageBreak
from reportlab.lib.units import cm, mm
from reportlab.lib.utils import simpleSplit
from cgi import escape
import base64
import io
from xlsxwriter.workbook import Workbook
import sys
reload(sys)
sys.setdefaultencoding('iso-8859-1')
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, inch, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

import time
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

import calendar
from datetime import date, datetime
from xlsxwriter.workbook import Workbook


'''
Estoy usando un metodo que reemplazara al boton generar planillas
del apartado de generacion de planillas por lotes
el metodo original esta en: hr_payroll/wizards/hr_payroll_payslips_by_employees
'''


class HrPayslip(models.Model):

    _inherit = ['hr.payslip.run']
    _description = 'Genera planillas para todos los empleados'

    feriados = fields.Integer("Feriados y Domingos")
    dias_calendarios = fields.Integer(
        'Dias Calendarios', compute='_calcula_dias_calendarios')

    asiento_contable_id = fields.Many2one('account.move',
        string=u'Asiento Contable', ondelete='set null')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('generado', 'Asiento Generado'),
        ('close', 'Close'),
    ], string='Status', index=True, readonly=True, copy=False, default='draft')

    @api.depends('date_start', 'date_end')
    def _calcula_dias_calendarios(self):
        # print "mis dias calendarios"
        # start = self.date_start
        print "mi date_end ", self
        end = self.date_end
        # a = date(int(start[:4]), int(start[5:7]), int(start[8:10]))
        # b = date(int(end[:4]), int(end[5:7]), int(end[8:10]))

        # asigno = b-a

        # asigno = calendar.monthrange(int(end[:4]), int(start[5:7]))[1]

        self.dias_calendarios = calendar.monthrange(
            int(end[:4]), int(end[5:7]))[1]

    @api.multi
    def _wizard_generar_asiento_contable(self):

        query_vista = """  
            select * from (
            select 
            a6.date_end as fecha_fin,
            'ASIENTO DISTRIBUIDO DE LA PLANILLA DEL MES':: TEXT as concepto,
            a7.id as cuenta_debe,
            a10.id as cuenta_analitica_id,
            sum(a1.amount*(a9.porcentaje/100)) as debe,
            0 as haber
            from hr_payslip_line a1
            left join hr_payslip a2 on a2.id=a1.slip_id
            left join hr_contract a3 on a3.id=a1.contract_id
            left join hr_employee a4 on a4.id=a1.employee_id
            left join hr_salary_rule a5 on a5.id=a1.salary_rule_id
            left join hr_payslip_run a6 on a6.id=a2.payslip_run_id
            left join account_account a7 on a7.id=a5.account_debit
            left join planilla_distribucion_analitica a8 on a8.id=a3.distribucion_analitica_id
            left join planilla_distribucion_analitica_lines a9 on a9.distribucion_analitica_id=a8.id
            left join account_analytic_account a10 on a10.id=a9.cuenta_analitica_id
            where a7.code is not null and a1.amount<>0 and a6.date_start='%s' and a6.date_end='%s'
            group by a6.date_end,a7.id,a10.id
            order by a7.code)tt
            union all 
            select * from (
            select 
            a6.date_end as fecha_fin,
            a5.name as concepto,
            a7.id as cuenta_haber,
            0::integer as cuenta_analitica_id,
            0 as debe,
            sum(a1.amount) as haber
            from hr_payslip_line a1
            left join hr_payslip a2 on a2.id=a1.slip_id
            left join hr_contract a3 on a3.id=a1.contract_id
            left join hr_employee a4 on a4.id=a1.employee_id
            left join hr_salary_rule a5 on a5.id=a1.salary_rule_id
            left join hr_payslip_run a6 on a6.id=a2.payslip_run_id
            left join account_account a7 on a7.id=a5.account_credit
            where a7.code is not null and a6.date_start='%s' and a6.date_end='%s'
            group by a6.date_end,a6.name,a5.name,a7.id,a7.code
            having sum(a1.amount)<>0
            order by a7.code)tt
                       """ % (self.date_start, self.date_end, self.date_start, self.date_end)

        print query_vista
        self.env.cr.execute(query_vista)

        res = self.env.cr.dictfetchall()

        total_debe = sum([x['debe'] for x in res])
        total_haber = sum([x['haber'] for x in res])

        vals = {
            'total_debe': total_debe,
            'total_haber': total_haber,
            'diferencia': total_debe-total_haber
        }

        sfs_id = self.env['planilla.asiento.contable'].create(vals)

        return {
            'name': 'Asiento Contable',
            "type": "ir.actions.act_window",
            "res_model": "planilla.asiento.contable",
            'view_type': 'form',
            'view_mode': 'form',
            "views": [[False, "form"]],
            "res_id": sfs_id.id,
            "target": "new",
            'context': {'current_id': self.id, 'account_move_lines': res}
        }

    def buscar_empleado_en_tabla(self, tabla, employee_id):
        for line in tabla:
            print "my id ", employee_id
            print "line id ", line.employee_id.id
            if line.employee_id.id == employee_id:
                return line

    @api.multi
    def importar_beneficios_sociales(self):
        planilla_parametros_liq = self.env['planilla.parametros.liquidacion'].get_parametros_liquidacion()

        # buscar gratificacion
        gratificaciones = self.env['planilla.gratificacion'].search(
            [('date_start', '=', self.date_start), ('date_end', '=', self.date_end)])
        print self.date_start, ' - ', self.date_end
        if gratificaciones:
            print "hay gratificacion ",
            print gratificaciones
            gratificaciones_lines = gratificaciones.planilla_gratificacion_lines
            for gratificacion_empleado in gratificaciones_lines:
                payslip = self.buscar_empleado_en_tabla(
                    self.slip_ids, gratificacion_empleado.employee_id)
                if payslip:
                    gratificacion = payslip.input_line_ids.search(
                        [('payslip_id', '=', payslip.id), ('code', '=', planilla_parametros_liq.cod_gratificacion.codigo)])
                    gratificacion.amount = gratificacion_empleado.total_gratificacion
                    bon9 = payslip.input_line_ids.search([('payslip_id', '=', payslip.id), (
                        'code', '=', planilla_parametros_liq.cod_bonificacion_9.codigo)])
                    if bon9:
                        bon9.amount = gratificacion_empleado.plus_9

        # buscar cts
        cts = self.env['planilla.cts'].search(
            [('date_start', '=', self.date_start), ('date_end', '=', self.date_end)])
        if cts:
            cts_lines = cts.planilla_cts_lines
            for cts_empleado in cts_lines:
                payslip = self.buscar_empleado_en_tabla(
                    self.slip_ids, cts_empleado.employee_id)
                if payslip:
                    entrada_cts = payslip.input_line_ids.search(
                        [('payslip_id', '=', payslip.id), ('code', '=', planilla_parametros_liq.cod_cts.codigo)])
                    entrada_cts.amount = cts_empleado.cts_a_pagar

        # buscar liquidacion
        liquidaciones = self.env['planilla.liquidacion'].search(
            [('date_start', '=', self.date_start), ('date_end', '=', self.date_end)])

        if liquidaciones:
            planilla_gratificacion_lines = liquidaciones.planilla_gratificacion_lines
            planilla_cts_lines = liquidaciones.planilla_cts_lines
            planilla_vacaciones_lines = liquidaciones.planilla_vacaciones_lines

            for gratificacion_trunca_emp in planilla_gratificacion_lines:
                payslip = self.buscar_empleado_en_tabla(
                    self.slip_ids, gratificacion_trunca_emp.employee_id)
                if payslip:
                    gratificacion_trunca = payslip.input_line_ids.search(
                        [('payslip_id', '=', payslip.id), ('code', '=', planilla_parametros_liq.cod_gratificacion_trunca.codigo)])
                    gratificacion_trunca.amount = gratificacion_trunca_emp.total_gratificacion
                    bon9 = payslip.input_line_ids.search([('payslip_id', '=', payslip.id), (
                        'code', '=', planilla_parametros_liq.cod_bonificacion_9.codigo)])
                    if bon9:
                        bon9.amount = gratificacion_trunca_emp.plus_9

            for cts_trunca_emp in planilla_cts_lines:
                payslip = self.buscar_empleado_en_tabla(
                    self.slip_ids, cts_trunca_emp.employee_id)
                if payslip:
                    cts_trunca = payslip.input_line_ids.search(
                        [('payslip_id', '=', payslip.id), ('code', '=', planilla_parametros_liq.cod_cts_trunca.codigo)])
                    cts_trunca.amount = cts_trunca_emp.cts_a_pagar

            for vacaciones_truncas_emp in planilla_vacaciones_lines:
                payslip = self.buscar_empleado_en_tabla(
                    self.slip_ids, vacaciones_truncas_emp.employee_id)
                if payslip:
                    vacacion_devengada = payslip.input_line_ids.search(
                        [('payslip_id', '=', payslip.id), ('code', '=', planilla_parametros_liq.cod_vacacion_devengada.codigo)])
                    vacacion_devengada.amount = vacaciones_truncas_emp.vacaciones_devengadas
                    vacacion_trunca = payslip.input_line_ids.search(
                        [('payslip_id', '=', payslip.id), ('code', '=', planilla_parametros_liq.cod_vacacion_trunca.codigo)])
                    vacacion_trunca.amount = vacaciones_truncas_emp.vacaciones_truncas

        # buscar quita categoria

        return self.env['planilla.warning'].info(title='Resultado de importacion', message="LOS BENEFICIOS SOCIALES SE IMPORTARON DE MANEARON DE MANERA EXITOSA!")

    @api.multi
    def regulariza_dias_laborados(self):
        planilla_ajustes = self.env['planilla.ajustes'].get_parametros_ajustes()
        self.ensure_one()

        for payslip in self.slip_ids:
            print payslip.employee_id.name_related, ' - ', payslip.contract_id.date_start, ' - ', payslip.contract_id.date_end
            dias_laborados = payslip.worked_days_line_ids.search(
                [('payslip_id', '=', payslip.id), ('code', '=', planilla_ajustes.cod_dias_laborados.codigo)])

            if payslip.contract_id.date_start > self.date_start and payslip.contract_id.date_end < self.date_end:
                # dias_laborados=payslip.worked_days_line_ids.search([('payslip_id','=',payslip.id),('code','=',planilla_ajustes.cod_dias_laborados.codigo)])
                fecha_ini = fields.Date.from_string(
                    payslip.contract_id.date_start)
                fecha_fin = fields.Date.from_string(
                    payslip.contract_id.date_end)
                if fecha_ini and fecha_fin:
                    dias_laborados.number_of_days = abs(
                        fecha_fin.day-fecha_ini.day)+1
                else:
                    dias_laborados.number_of_days = abs(
                        30-fecha_ini.day)+1

            elif payslip.contract_id.date_start > self.date_start:
                fecha_ini = fields.Date.from_string(
                    payslip.contract_id.date_start)
                if fecha_ini:
                    dias_laborados.number_of_days = 30-fecha_ini.day+1
            elif payslip.contract_id.date_end < self.date_end:
                # dias_laborados=payslip.worked_days_line_ids.search([('payslip_id','=',payslip.id),('code','=',planilla_ajustes.cod_dias_laborados.codigo)])
                fecha_fin = fields.Date.from_string(
                    payslip.contract_id.date_end)
                if fecha_fin:
                    dias_laborados.number_of_days = fecha_fin.day
            else:
                dias_laborados.number_of_days = 30

        # return self.env['planilla.warning'].info(title='Resultados regularizacion dias', message="SE REGULARIZARON LOS DIAS LABORADOS DE MANERA EXITOSA!")

    @api.one
    def write(self, vals):
        print "guardando payslip_run ",vals
        line = False
        self.ensure_one()
        print vals
        if 'date_start' in vals and 'date_end' in vals:
            print vals
            line = self.env['hr.payslip.run'].search(
                [('date_start', '=', vals['date_start']), ('date_end', '=',  vals['date_start'])])
        if line:
            raise ValidationError(
                "Ya existe una nomina con las fechas  %s y %s" % (vals['date_start'], self.date_end))
        if 'date_start' in vals:
            print vals
            line = self.env['hr.payslip.run'].search(
                [('date_start', '=', vals['date_start']), ('date_end', '=', self.date_end)])

        if line:
            raise ValidationError(
                "Ya existe una nomina con las fechas  %s y %s" % (vals['date_start'], self.date_end))
        if 'date_end' in vals:
            print vals
            line = self.env['hr.payslip.run'].search(
                [('date_start', '=', self.date_start), ('date_end', '=', vals['date_end'])])

        if line:
            raise ValidationError(
                "Ya existe una nomina con las fechas  %s y %s" % (self.date_start, vals['date_end']))
        # self.asiento_contable_id=self.env['account.move'].search([('id','=',1)]).id#[(0,0,self.env['account.move'].browse(1) ) ]

        return super(HrPayslip, self).write(vals)

    @api.model
    def create(self, vals):
        print vals
        line = self.env['hr.payslip.run'].search(
            [('date_start', '=', vals['date_start']), ('date_end', '=', vals['date_end'])])
        if line:
            raise ValidationError(
                "Ya existe una nomina con las fechas  %s y %s" % (vals['date_start'], vals['date_end']))
        return super(HrPayslip, self).create(vals)

    def get_mes(self, mes):
        if mes == 1:
            return "Enero"
        elif mes == 2:
            return "Febrero"
        elif mes == 3:
            return "Marzo"
        elif mes == 4:
            return "Abril"
        elif mes == 5:
            return "Mayo"
        elif mes == 6:
            return "Junio"
        elif mes == 7:
            return "Julio"
        elif mes == 8:
            return "Agosto"
        elif mes == 9:
            return "Septiembre"
        elif mes == 10:
            return "Octubre"
        elif mes == 11:
            return "Noviembre"
        else:
            return "Diciembre"

    @api.multi
    def draft_payslip_run(self):
        if self.state =='generado':
            self.asiento_contable_id.unlink()
        else:
            for line in self.slip_ids:
                line.line_ids.unlink()
                line.write({'state': 'draft'})
        self.refresh()
        return super(HrPayslip, self).draft_payslip_run()

    @api.multi
    def close_payslip_run(self):
        for line in self.slip_ids:
            line.write({'state': 'done'})
        return super(HrPayslip, self).close_payslip_run()

    @api.multi
    def genera_planilla_afp_net(self):
        import io
        from xlsxwriter.workbook import Workbook
        output = io.BytesIO()
        workbook = Workbook('planilla_afp_net.xls')
        planilla_ajustes = self.env['planilla.ajustes'].search([], limit=1)
        for payslip_run in self.browse(self.ids):
            query_vista = """  DROP VIEW IF EXISTS planilla_afp_net_xlsx;
                create or replace view planilla_afp_net_xlsx as (

                select row_number() OVER () AS id,* from
                (

                    select  hc.cuspp,ptd.codigo_afp as tipo_doc,he.identification_id,he.a_paterno,he.a_materno,he.nombres,
                    case
                        when (hc.date_end isnull or hc.date_end<='%s' or hc.date_end>='%s') then 'S'
                    else 
                        'N' end as relacion_laboral,
                    case
                        when (hc.date_start between '%s' and '%s') then 'S'
                    else 
                        'N' end as inicio_relacion_laboral,
                    case
                        when (hc.date_end between '%s' and '%s') then 'S'
                    else 
                        'N' end as cese_relacion_laboral,
                        hc.excepcion_aportador,
                    (select total from hr_payslip_line
                            where slip_id = p.id and  code = '%s' ) as remuneracion_asegurable,
                    (SELECT ''::TEXT as aporte_fin_provisional),
                    (SELECT ''::TEXT as aporte_sin_fin_provisional),
                    (SELECT ''::TEXT as aporte_voluntario_empleador),
                    case
                        when (hc.regimen_laboral isnull) then 'N'
                    else 
                        hc.regimen_laboral end as regimen_laboral
                    from hr_payslip_run hpr
                    inner join hr_payslip p
                    on p.payslip_run_id = hpr.id
                    inner join hr_contract hc
                    on hc.id = p.contract_id
                    inner join hr_employee he
                    on he.id = hc.employee_id
                    left join planilla_tipo_documento ptd
                    on ptd.id = he.tablas_tipo_documento_id
                    where hc.afiliacion_id!=7 and hpr.id= %d
                        ) T
                )""" % (payslip_run.date_end, payslip_run.date_end,
                        payslip_run.date_start, payslip_run.date_end,
                        payslip_run.date_start, payslip_run.date_end,
                        planilla_ajustes.cod_remuneracion_asegurable.code if planilla_ajustes else '',
                        payslip_run.id)
            print query_vista
            self.env.cr.execute(query_vista)

            # PRIMERA HOJA DE LA DATA EN TABLA
            # workbook = Workbook(output, {'in_memory': True})

            # direccion = self.env['main.parameter'].search([])[0].dir_create_file

            worksheet = workbook.add_worksheet(
                str(payslip_run.id)+'-'+payslip_run.date_start+'-'+payslip_run.date_end)
            # Print Format
            worksheet.set_landscape()  # Horizontal
            worksheet.set_paper(9)  # A-4
            worksheet.set_margins(left=0.75, right=0.75, top=1, bottom=1)
            worksheet.fit_to_pages(1, 0)  # Ajustar por Columna

            bold = workbook.add_format({'bold': True})
            normal = workbook.add_format()
            boldbord = workbook.add_format({'bold': True})
            boldbord.set_border(style=2)
            boldbord.set_align('center')
            boldbord.set_align('vcenter')
            boldbord.set_text_wrap()
            boldbord.set_font_size(9)
            boldbord.set_bg_color('#DCE6F1')
            numbertres = workbook.add_format({'num_format': '0.000'})
            numberdos = workbook.add_format({'num_format': '0.00'})
            bord = workbook.add_format()
            bord.set_border(style=1)
            bord.set_text_wrap()
            # numberdos.set_border(style=1)
            numbertres.set_border(style=1)

            title = workbook.add_format({'bold': True})
            title.set_align('center')
            title.set_align('vcenter')
            title.set_text_wrap()
            title.set_font_size(20)
            # worksheet.set_row(0, 30)

            x = 0

            import sys
            reload(sys)
            sys.setdefaultencoding('iso-8859-1')

            filtro = []
            for line in self.env['planilla.afp.net.xlsx'].search(filtro):
                worksheet.write(x, 0, line.id if line.id else '')
                worksheet.write(
                    x, 1, line.cuspp if line.cuspp else '')
                worksheet.write(
                    x, 2, line.tipo_doc if line.tipo_doc else '')

                worksheet.write(
                    x, 3, line.identification_id if line.identification_id else '')
                worksheet.write(x, 4, line.a_paterno)
                worksheet.write(x, 5, line.a_materno)
                worksheet.write(x, 6, line.nombres)
                worksheet.write(
                    x, 7, line.relacion_laboral if line.relacion_laboral else '')
                worksheet.write(
                    x, 8, line.inicio_relacion_laboral if line.inicio_relacion_laboral else '')
                worksheet.write(
                    x, 9, line.cese_relacion_laboral if line.cese_relacion_laboral else '')
                worksheet.write(
                    x, 10, line.excepcion_aportador if line.excepcion_aportador else '')
                worksheet.write(
                    x, 11, line.remuneracion_asegurable, numberdos)
                worksheet.write(
                    x, 12, line.aporte_fin_provisional, numberdos)
                worksheet.write(
                    x, 13, line.aporte_sin_fin_provisional, numberdos)
                worksheet.write(
                    x, 14, line.aporte_voluntario_empleador, numberdos)
                worksheet.write(
                    x, 15, line.regimen_laboral if line.regimen_laboral else '')

                x = x + 1

                tam_col = [2, 15, 2, 10, 10, 10, 35, 1, 1, 1, 1,
                           8, 5, 5, 1, 1]

                worksheet.set_column('A:A', tam_col[0])
                worksheet.set_column('B:B', tam_col[1])
                worksheet.set_column('C:C', tam_col[2])
                worksheet.set_column('D:D', tam_col[3])
                worksheet.set_column('E:E', tam_col[4])
                worksheet.set_column('F:F', tam_col[5])
                worksheet.set_column('G:G', tam_col[6])
                worksheet.set_column('H:H', tam_col[7])
                worksheet.set_column('I:I', tam_col[8])
                worksheet.set_column('J:J', tam_col[9])
                worksheet.set_column('K:K', tam_col[10])
                worksheet.set_column('L:L', tam_col[11])
                worksheet.set_column('M:M', tam_col[12])
                worksheet.set_column('O:O', tam_col[13])
                worksheet.set_column('P:P', tam_col[14])

        workbook.close()

        f = open('planilla_afp_net.xls', 'rb')

        vals = {
            'output_name': 'planilla_afp_net.xls',
            'output_file': base64.encodestring(''.join(f.readlines())),
        }

        sfs_id = self.env['planilla.export.file'].create(vals)

        return {
            "type": "ir.actions.act_window",
            "res_model": "planilla.export.file",
            "views": [[False, "form"]],
            "res_id": sfs_id.id,
            "target": "new",
        }

    def get_col_widths(self, datos):
        # First we find the maximum length of the index column
        datos = zip(*datos)  # transponiendo filas por columnas
        column_len = []
        for i in range(len(datos)):
            max_col = 0
            for j in range(len(datos[i])):
                if len(str(datos[i][j]).strip()) > max_col:
                    max_col = len(str(datos[i][j]).strip())

            column_len.append(max_col+5)
        return column_len
        # idx_max = max([len(str(s)) for s in dataframe.index.values] + [len(str(dataframe.index.name))])
        # # Then, we concatenate this to the max of the lengths of column name and its values for each column, left to right
        # return [idx_max] + [max([len(str(s)) for s in dataframe[col].values] + [len(col)]) for col in dataframe.columns]

    @api.multi
    def exportar_plame(self):

        if len(self.ids) > 1:
            raise UserError(
                'Solo se puede mostrar una planilla a la vez, seleccione solo una nómina')

        output = io.BytesIO()
        directory = os.getcwd()
        # workbook = Workbook('planilla_plame.xls')
        planilla_ajustes = self.env['planilla.ajustes'].search([], limit=1)
        for payslip_run in self.browse(self.ids):
            query_vista = """  DROP VIEW IF EXISTS planilla_export_plame_rem;
                create or replace view planilla_export_plame_rem as (

                select row_number() OVER () AS id,* from
                (
                select  ptd.codigo_sunat as tipo_doc,e.identification_id ,sr.cod_sunat,hpl.total as monto_devengado,hpl.total as monto_pagado_descontado
                from hr_payslip_run hpr
                inner join hr_payslip hp
                on hpr.id= hp.payslip_run_id
                    inner join hr_payslip_line hpl
                    on hp.id=hpl.slip_id
                    inner join hr_salary_rule as sr
                    on sr.code = hpl.code
                    inner join hr_employee e 
                    on e.id = hpl.employee_id
                    inner join hr_salary_rule_category hsrc
                    on hsrc.id = hpl.category_id
                    left join planilla_tipo_documento ptd
                    on ptd.id = e.tablas_tipo_documento_id
                    where  hpr.id= %d and sr.cod_sunat!=''
                    and hpl.appears_on_payslip='t'  
                    order by e.id,hpl.sequence
                        ) T
                )""" % (payslip_run.id)

            print query_vista
            self.env.cr.execute(query_vista)

        docname = '0601%s%s%s.rem' % (
            self.date_end[:4], self.date_end[5:7], planilla_ajustes.ruc if planilla_ajustes else '')
        # REM
        sql_query = """SELECT * FROM planilla_export_plame_rem """

        self.env.cr.execute(sql_query)
        data = self.env.cr.fetchall()

        myfile = open(str(docname), 'w+')
        for item in data:
            print "escribiendo archivo rem", [i for i in item]
            myfile.write(
                '|'.join([str(item[i]) if item[i] != None else '' for i in range(1, len(item))]) + '|\n')
        myfile.close()

        # Caracteres Especiales
        import sys
        reload(sys)
        sys.setdefaultencoding('iso-8859-1')
        f = open(docname, 'rb')
        vals = {
            'output_name': docname,
            'output_file': base64.encodestring(''.join(f.readlines())),
        }

        sfs_id = self.env['planilla.export.file'].create(vals)
        os.remove(docname)
        return {
            "type": "ir.actions.act_window",
            "res_model": "planilla.export.file",
            "views": [[False, "form"]],
            "res_id": sfs_id.id,
            "target": "new",
        }

    @api.multi
    def exportar_plame_horas(self):

        if len(self.ids) > 1:
            raise UserError(
                'Solo se puede mostrar una planilla a la vez, seleccione solo una nómina')

        output = io.BytesIO()
        directory = os.getcwd()
        # workbook = Workbook('planilla_plame.xls')
        planilla_ajustes = self.env['planilla.ajustes'].search([], limit=1)
        for payslip_run in self.browse(self.ids):
            query_vista = """  DROP VIEW IF EXISTS planilla_export_plame_horas_rem;
                create or replace view planilla_export_plame_horas_rem as (

                select row_number() OVER () AS id,* from
                (
                select  ptd.codigo_sunat as tipo_doc,e.identification_id ,
		(30-hp.feriados-(select sum(number_of_days) as dias from hr_payslip_worked_days
                where (code = '%s')
                and payslip_id=hp.id))*8 as horas_ordinarias,
                (select 0.0 as minutos_ordinarios) ,
                (select sum(number_of_hours) as horas from hr_payslip_worked_days
                where (code = 'HE25' OR code = 'HE35' or code = 'HE100')
                and payslip_id=hp.id),
                   coalesce( (select sum(minutos) as minutos from hr_payslip_worked_days
                where (code = 'HE25' OR code = 'HE35' or code = 'HE100')
                and payslip_id=hp.id),0) as minutos                
                from hr_payslip_run hpr
                inner join hr_payslip hp
                on hpr.id= hp.payslip_run_id
		inner join hr_employee e
		on e.id = hp.employee_id
		left join planilla_tipo_documento ptd
		on ptd.id = e.tablas_tipo_documento_id
		where  hpr.id= %d 
		order by e.id
                        ) T
                )""" % (planilla_ajustes.cod_dias_no_laborados.codigo if planilla_ajustes else '',
                        payslip_run.id)

            print query_vista
            self.env.cr.execute(query_vista)

        docname = '0601%s%s%s.jor' % (
            self.date_end[:4], self.date_end[5:7], planilla_ajustes.ruc if planilla_ajustes else '')
        # REM
        sql_query = """SELECT * FROM planilla_export_plame_horas_rem """

        self.env.cr.execute(sql_query)
        data = self.env.cr.fetchall()

        myfile = open(str(docname), 'w+')
        for item in data:
            print "escribiendo archivo rem", [i for i in item]
            myfile.write(
                '|'.join([str(item[i]) if item[i] != None else '' for i in range(1, len(item))]) + '|\n')
        myfile.close()

        # Caracteres Especiales
        import sys
        reload(sys)
        sys.setdefaultencoding('iso-8859-1')
        f = open(docname, 'rb')
        vals = {
            'output_name': docname,
            'output_file': base64.encodestring(''.join(f.readlines())),
        }

        sfs_id = self.env['planilla.export.file'].create(vals)
        os.remove(docname)
        return {
            "type": "ir.actions.act_window",
            "res_model": "planilla.export.file",
            "views": [[False, "form"]],
            "res_id": sfs_id.id,
            "target": "new",
        }

    @api.multi
    def exportar_planilla_tabular_xlsx(self):
        if len(self.ids) > 1:
            raise UserError(
                'Solo se puede mostrar una planilla a la vez, seleccione solo una nómina')

        self.env['planilla.planilla.tabular.wizard'].reconstruye_tabla(self.date_start,self.date_end)

        workbook = Workbook('planilla_tabular.xls')
        worksheet = workbook.add_worksheet(
            str(self.id)+'-'+self.date_start+'-'+self.date_end)
        # Print Format
        worksheet.set_landscape()  # Horizontal
        worksheet.set_paper(9)  # A-4
        worksheet.set_margins(left=0.75, right=0.75, top=1, bottom=1)
        worksheet.fit_to_pages(1, 0)  # Ajustar por Columna

        fontSize = 8
        bold = workbook.add_format(
            {'bold': True, 'font_name': 'Arial', 'font_size': fontSize})
        normal = workbook.add_format()
        boldbord = workbook.add_format({'bold': True, 'font_name': 'Arial'})
        # boldbord.set_border(style=1)
        boldbord.set_align('center')
        boldbord.set_align('bottom')
        boldbord.set_text_wrap()
        boldbord.set_font_size(fontSize)
        boldbord.set_bg_color('#99CCFF')
        numberdos = workbook.add_format(
            {'num_format': '0.00', 'font_name': 'Arial', 'align': 'right'})
        formatLeft = workbook.add_format(
            {'num_format': '0.00', 'font_name': 'Arial', 'align': 'left', 'font_size': fontSize})
        formatLeftColor = workbook.add_format(
            {'bold': True, 'num_format': '0.00', 'font_name': 'Arial', 'align': 'left', 'bg_color': '#99CCFF', 'font_size': fontSize})
        styleFooterSum = workbook.add_format(
            {'bold': True, 'num_format': '0.00', 'font_name': 'Arial', 'align': 'right', 'font_size': fontSize, 'top': 1, 'bottom': 2})
        styleFooterSum.set_bottom(6)
        numberdos.set_font_size(fontSize)
        bord = workbook.add_format()
        bord.set_border(style=1)
        bord.set_text_wrap()
        # numberdos.set_border(style=1)

        title = workbook.add_format({'bold': True, 'font_name': 'Arial'})
        title.set_align('center')
        title.set_align('vcenter')
        # title.set_text_wrap()
        title.set_font_size(18)
        company = self.env['res.company'].search([], limit=1)[0]

        x = 0

        import sys
        reload(sys)
        sys.setdefaultencoding('iso-8859-1')
        worksheet.merge_range(
            'D1:O1', u"PLANILLA DE SUELDOS Y SALARIOS", title)
        worksheet.set_row(x, 29)
        x = x+2

        worksheet.write(x, 0, u"Empresa:", bold)
        worksheet.write(x, 1, company.name, formatLeft)

        x = x+1
        worksheet.write(x, 0, u"Mes:", bold)
        worksheet.write(
            x, 1, self.get_mes(int(self.date_end[5:7]) if self.date_end else 0).upper()+"-"+self.date_end[:4], formatLeft)

        x = x+3

        header_planilla_tabular = self.env['ir.model.fields'].search(
            [('name', 'like', 'x_%'), ('model', '=', 'planilla.tabular')], order="create_date")

        worksheet.write(
            x, 0, header_planilla_tabular[0].field_description, formatLeftColor)
        for i in range(1, len(header_planilla_tabular)):
            worksheet.write(
                x, i, header_planilla_tabular[i].field_description, boldbord)

        worksheet.set_row(x, 50)

        fields = ['\"'+column.name+'\"' for column in header_planilla_tabular]

        x = x+1

        filtro = []

        query = 'select %s from planilla_tabular' % (','.join(fields))
        print query
        self.env.cr.execute(query)
        datos_planilla = self.env.cr.fetchall()
        range_row = len(datos_planilla[0] if len(datos_planilla) > 0 else 0)
        x_ini = x
        for i in range(len(datos_planilla)):
            for j in range(range_row):
                if j == 0 or j == 1:
                    worksheet.write(
                        x, j, datos_planilla[i][j] if datos_planilla[i][j] else '0.00', formatLeft)
                else:
                    worksheet.write(
                        x, j, datos_planilla[i][j] if datos_planilla[i][j] else '0.00', numberdos)
            x = x+1
        x = x + 1
        datos_planilla_transpuesta = zip(*datos_planilla)

        for j in range(3, len(datos_planilla_transpuesta)):
            worksheet.write(
                x, j, sum([float(d) for d in datos_planilla_transpuesta[j]]), styleFooterSum)

        # seteando tamaño de columnas
        col_widths = self.get_col_widths(datos_planilla)
        worksheet.set_column(0, 0, col_widths[0]-10)
        worksheet.set_column(1, 1, col_widths[1]-7)
        for i in range(2, len(col_widths)):
            worksheet.set_column(i, i, col_widths[i])

        workbook.close()

        f = open('planilla_tabular.xls', 'rb')

        vals = {
            'output_name': 'planilla_tabular.xls',
            'output_file': base64.encodestring(''.join(f.readlines())),
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
    def generar_planillas_lotes(self):
        payslips = self.env['hr.payslip']

        # print "mi usuario activo ", self.id
        from_date = self.date_start  # run_data.get('date_start')
        to_date = self.date_end  # $run_data.get('date_end')

        query = """
        select * from hr_contract hr_contr
        inner join hr_employee hr_emp
        on hr_contr.employee_id = hr_emp.id
        where 
        (date_end >= '%s' and date_end <= '%s') or
        (date_start <= '%s' and date_start >='%s'   ) or
        (
            date_start <='%s' 		and (date_end is null or date_end >= '%s' )
        )
        """ % (from_date, to_date,
               to_date, from_date,
               from_date, to_date
               )
        print query
        self.env.cr.execute(query)
        employee_aux_ids = self.env.cr.dictfetchall()
        self.slip_ids.unlink()
        for employee in self.env['hr.employee'].browse([row['employee_id'] for row in employee_aux_ids]):
            slip_data = self.env['hr.payslip'].onchange_employee_id(
                from_date, to_date, employee.id, contract_id=False)
            res = {
                'employee_id': employee.id,
                'name': slip_data['value'].get('name'),
                'struct_id': slip_data['value'].get('struct_id'),
                'contract_id': slip_data['value'].get('contract_id'),
                'payslip_run_id': self.id,
                'input_line_ids': [(0, 0, x) for x in slip_data['value'].get('input_line_ids')],
                'worked_days_line_ids': [(0, 0, x) for x in slip_data['value'].get('worked_days_line_ids')],
                'date_from': from_date,
                'date_to': to_date,
                'credit_note': self.credit_note,
                'company_id': employee.company_id.id,
            }
            payslip = self.env['hr.payslip'].create(res)
            payslip.load_entradas_tareos()
            payslips += payslip
        return self.env['planilla.warning'].info(title='Resultado de generacion', message="SE GENERO LA PLANILLA DE MANERA EXITOSA!")

    @api.multi
    def calcular_reglas_salariales(self):
        for employee_payroll in self.slip_ids:
            employee_payroll.dias_calendarios = self.dias_calendarios
            employee_payroll.feriados = self.feriados
            employee_payroll.compute_sheet()
        self.slip_ids.refresh()
        return self.env['planilla.warning'].info(title='Resultado de calculo', message="SE CALCULO  REGLAS SALARIALES DE MANERA EXITOSA!")

    @api.multi
    def generar_planilla_tabular(self):
        if len(self.ids) > 1:
            raise UserError(
                'Solo se puede generar una planilla a la vez, seleccione solo una')

        return self.env['planilla.planilla.tabular.wizard'].create({'fecha_ini': self.date_start, 'fecha_fin': self.date_end}).do_rebuild()
        # return self.env['planilla.warning'].info(title='Resultado de Generación', message="SE GENERARON LOS DATOS EXITOSAMENTE PARA VER EN PANTALLA O EXPORTAR A EXCEL!")

    @api.multi
    def ver_pantalla_planilla_tabular(self):
        if len(self.ids) > 1:
            raise UserError(
                'Solo se puede mostrar una planilla a la vez, seleccione solo una nómina')
        if not self.env['planilla.tabular'].search([]):
            raise UserError(
                'No hay Datos para mostrar,intente el boton generar planilla tabular')
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'planilla.tabular',
            'view_type': 'form',
            'view_mode': 'tree',
            'target': 'current'
        }

    @api.multi
    def generar_boletas(self):
        # import pudb;pudb.set_trace()

        self.reporteador()
        # direccion = self.env['main.parameter'].search([])[0].dir_create_file

        vals = {
            'output_name': 'Planilla.pdf',
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
    def reporteador(self):
        # CREANDO ARCHIVO PDF
        # direccion = self.env['main.parameter'].search([])[0].dir_create_file
        archivo_pdf = SimpleDocTemplate(
            "planilla_tmp.pdf", pagesize=A4, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=20)

        elements = []

        categories = self.env['hr.salary.rule.category'].search(
            [('aparece_en_nomina', '=', True)], order="secuencia")
        planilla_ajustes = self.env['planilla.ajustes'].search([], limit=1)
        print "MIS PLANILLAS AJUSTES ", planilla_ajustes, "LEN ", len(
            planilla_ajustes)
        # genero boletas por cada payslip seleccionada en el treeview
        for payslip_run in self.browse(self.ids):  # lotes de nominas
            # import pudb; pudb.set_trace()
            for payslip in payslip_run.slip_ids:  # lista de nominas
                # for empleado in self.env['hr.employee'].search([]):
                company = payslip.company_id.partner_id
                dias_no_laborados = int(payslip.worked_days_line_ids.search(
                    [('code', '=', planilla_ajustes.cod_dias_no_laborados.codigo if len(planilla_ajustes) > 0 else ''), ('payslip_id', '=', payslip.id)], limit=1).number_of_days)
                print "mi payslip_run ", payslip_run
                print "mis dias no laborados ", dias_no_laborados
                print "mis dias calendarios ", str(
                    payslip.dias_calendarios), " fin "
                # dias_laborados = int(
                #     payslip.dias_calendarios-dias_no_laborados)
                dias_laborados = int(payslip.worked_days_line_ids.search(
                    [('code', '=', planilla_ajustes.cod_dias_laborados.codigo if len(planilla_ajustes) > 0 else ''), ('payslip_id', '=', payslip.id)], limit=1).number_of_days)

                dias_subsidiados = int(payslip.worked_days_line_ids.search(
                    [('code', '=', planilla_ajustes.cod_dias_subsidiados.codigo if len(planilla_ajustes) > 0 else ''), ('payslip_id', '=', payslip.id)], limit=1).number_of_days)

                query_horas_sobretiempo = '''
                select sum(number_of_days) as dias ,sum(number_of_hours) as horas ,sum(minutos) as minutos from hr_payslip_worked_days
                where (code = 'HE25' OR code = 'HE35' or code = 'HE100')
                and payslip_id=%d
                ''' % (payslip.id)

                print "HORAS SOBRETIEMPO QUERY ", query_horas_sobretiempo

                self.env.cr.execute(query_horas_sobretiempo)
                # str(int(self.env.cr.dictfetchone()['sum']))
                total_sobretiempo = self.env.cr.dictfetchone()

                # formula para los dias laborados segun sunat
                # total_horas_jornada_ordinaria = (30-payslip_run.feriados)*8

                dias_faltas = self.env['hr.payslip.worked_days'].search(
                    [('code', '=', planilla_ajustes.cod_dias_no_laborados.codigo if planilla_ajustes else ''),
                     ('payslip_id', '=', payslip.id)], limit=1)
                print "MIS HORAS SOBRETIEMPO ", query_horas_sobretiempo
                # formula para los dias laborados segun sunat
                total_horas_jornada_ordinaria = int(
                    dias_laborados-payslip.feriados-dias_faltas.number_of_days if dias_faltas else 0)*8

                print dias_laborados, dias_no_laborados, dias_subsidiados, total_horas_jornada_ordinaria, total_sobretiempo,

                self.genera_boleta_empleado(payslip_run.date_start, payslip_run.date_end, payslip.employee_id, str(dias_no_laborados), str(dias_laborados), str(total_horas_jornada_ordinaria), (total_sobretiempo), str(dias_subsidiados), elements,
                                            company, categories, planilla_ajustes)

        archivo_pdf.build(elements)

    @api.multi
    def genera_boleta_empleado(self, date_start, date_end, empleado, dias_no_laborados, dias_laborados, total_horas_jornada_ordinaria, total_sobretiempo, dias_subsidiados, elements, company, categories, planilla_ajustes):

        style_title = ParagraphStyle(
            name='Center', alignment=TA_LEFT, fontSize=14, fontName="times-roman")
        style_form = ParagraphStyle(
            name='Justify', alignment=TA_JUSTIFY, fontSize=10, fontName="times-roman")
        style_cell = ParagraphStyle(
            name='Center', alignment=TA_CENTER, fontSize=9.6, fontName="times-roman")
        style_cell_right = ParagraphStyle(
            name='Right', alignment=TA_RIGHT, fontSize=9.6, fontName="times-roman")
        style_cell_left = ParagraphStyle(
            name='Left', alignment=TA_LEFT, fontSize=9.6, fontName="times-roman")
        style_cell_bold = ParagraphStyle(
            name='centerBold', alignment=TA_CENTER, fontSize=8, fontName="Times-Bold")

        colorHeader = colors.Color(
            red=(219/255.0), green=(229/255.0), blue=(241/255.0))

        texto = "Trabajador – Datos de boleta de pago"
        elements.append(Paragraph(texto, style_title))
        elements.append(Spacer(1, 30))

        colorTitle = colors.Color(
            red=(197/255.0), green=(217/255.0), blue=(241/255.0))

        data = [
            [Paragraph('RUC: ' + planilla_ajustes.ruc if planilla_ajustes.ruc else '', style_cell_left),
             '', '', '', '', '', '', ''],
            [Paragraph('Empleador: ' + str(company.name),
                       style_cell_left), '', '', '', '', '', '', ''],
            [Paragraph('Periodo: ' + date_start + ' - ' + date_end,
                       style_cell_left), '', '', '', '', '', '', '']
        ]
        t = Table(data, style=[
            # ('SPAN', (1, 0), (4, 0)),  # cabecera

            ('BACKGROUND', (0, 0), (-1, -1), colorTitle),  # fin linea 3
            ('SPAN', (0, 0), (7, 0)),
            ('SPAN', (0, 1), (7, 1)),
            ('SPAN', (0, 2), (7, 2)),

            ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
            ('BOX', (0, 0), (-1, -1), 0.1, colors.black),
            ('LEFTPADDING', (0, 0), (-1, -1), 1),
            ('RIGHTPADDING', (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('TOPPADDING', (0, 0), (-1, -1), 1),

        ])
        t._argW[3] = 1.0*inch
        elements.append(t)

        elements.append(Spacer(1, 30))
        print "MI DATE START ", date_start
        print "MI DATE END ", date_end
        contract_employee = self.env['hr.contract'].exist_contract(
            empleado.id, date_start, date_end)

        # search(
        #     [('employee_id', '=', empleado.id), '&', ('date_start', '<=', date_start), '|', ('date_end', '=', None), ('date_end', '>=', date_end)])

        for contract in contract_employee:
            print "CONTRACT  ", contract.date_start, " - ", contract.date_end

        if len(contract_employee) > 1:
            raise UserError('El empleado '+empleado.name_related +
                            u' tiene más de un contrato activo(Contrato->%s->Informacion->Duracion->date_end)' % empleado.name_related)

        row_empleado = [Paragraph(empleado.tablas_tipo_documento_id.descripcion_abrev if empleado.tablas_tipo_documento_id.descripcion_abrev else '', style_cell), Paragraph(empleado.identification_id if empleado.identification_id else '', style_cell), Paragraph(
            empleado.name_related.strip().title(), style_cell), '', '', '', Paragraph(contract_employee.situacion_id.descripcion_abrev if contract_employee.situacion_id.descripcion_abrev else '', style_cell), '']

        row_empleado_line_4 = [Paragraph(contract_employee.date_start if contract_employee.date_start else '', style_cell), '', Paragraph(contract_employee.tipo_trabajador_id.descripcion_abrev.title() if contract_employee.tipo_trabajador_id.descripcion_abrev else '', style_cell), '', Paragraph(
            contract_employee.afiliacion_id.entidad if contract_employee.afiliacion_id.entidad else '', style_cell), '', Paragraph(contract_employee.cuspp if contract_employee.cuspp else '', style_cell), '']

        horas_sobretiempo = int(
            total_sobretiempo['horas']) if total_sobretiempo['horas'] else 0
        minutos_sobretiempo = int(
            total_sobretiempo['minutos']) if total_sobretiempo['minutos'] else 0
        row_empleado_line_5 = [Paragraph(dias_laborados, style_cell), Paragraph(dias_no_laborados, style_cell), Paragraph(dias_subsidiados, style_cell), Paragraph(
            dict(empleado._fields['condicion'].selection).get(empleado.condicion), style_cell), Paragraph(total_horas_jornada_ordinaria, style_cell), Paragraph('0', style_cell), Paragraph(str(horas_sobretiempo), style_cell), Paragraph(str(minutos_sobretiempo), style_cell)]
        row_empleado_line_6 = [Paragraph(contract_employee.tipo_suspension_id.descripcion_abrev if contract_employee.tipo_suspension_id else '', style_cell), Paragraph(contract_employee.motivo.strip() if contract_employee.motivo else '', style_cell), '', '', '',
                               Paragraph(contract_employee.nro_dias if contract_employee.nro_dias else '', style_cell), Paragraph(contract_employee.otros_5ta_categoria.strip() if contract_employee.otros_5ta_categoria else '', style_cell), '']

        data = [[Paragraph('Documento de identidad', style_cell), '', Paragraph('Nombres y Apellidos', style_cell), '', '', '', Paragraph('Situacion', style_cell), ''],
                [Paragraph('Tipo', style_cell), Paragraph(
                    'Numero', style_cell), '', '', '', '', '', ''],
                row_empleado,
                [Paragraph('Fecha de ingreso', style_cell), '', Paragraph('Tipo de trabajador', style_cell), '', Paragraph(
                    'Regimen Pensionario', style_cell), '', Paragraph('CUSPP', style_cell), ''],
                row_empleado_line_4,
                [Paragraph('Dias\nlaborados', style_cell), Paragraph('Dias\nno laborados', style_cell), Paragraph('Dias\nSubsidiados', style_cell), Paragraph(
                    'Condicion', style_cell), Paragraph('Jornada Ordinaria', style_cell), '', Paragraph('Sobretiempo', style_cell), ''],
                ['1', '2', '3', '4', Paragraph('Horas', style_cell), Paragraph(
                    'Minutos', style_cell), Paragraph('Horas', style_cell), Paragraph('Minutos', style_cell)],
                row_empleado_line_5,
                [Paragraph('Motivo de suspención de labores', style_cell), '', '', '', '', '', Paragraph(
                    'Otros empleadores por\nrentas de 5ta categoría', style_cell), ''],
                [Paragraph('Tipo', style_cell), Paragraph('Motivo', style_cell),
                 '', '', '', Paragraph('Nº Días', style_cell), '', ''],
                row_empleado_line_6,
                ]

        t = Table(data, style=[
            ('SPAN', (0, 0), (1, 0)),  # cabecera
            ('SPAN', (2, 0), (5, 1)),  # cabecera
            ('SPAN', (6, 0), (7, 1)),  # cabecera
            ('BACKGROUND', (0, 0), (7, 0), colorHeader),  # fin linea 1
            ('SPAN', (2, 2), (5, 2)),  # empleado
            ('SPAN', (6, 2), (7, 2)),  # empleado
            ('BACKGROUND', (0, 1), (7, 1), colorHeader),  # fin linea 2
            ('SPAN', (0, 3), (1, 3)),  # linea 3
            ('SPAN', (2, 3), (3, 3)),
            ('SPAN', (4, 3), (5, 3)),
            ('SPAN', (6, 3), (7, 3)),
            ('BACKGROUND', (0, 3), (7, 3), colorHeader),  # fin linea 3
            ('SPAN', (0, 4), (1, 4)),  # linea 4
            ('SPAN', (2, 4), (3, 4)),
            ('SPAN', (4, 4), (5, 4)),
            ('SPAN', (6, 4), (7, 4)),  # fin linea 4
            # linea 5 y 6 horas y sobretiempos
            ('SPAN', (0, 5), (0, 6)),
            ('SPAN', (1, 5), (1, 6)),
            ('SPAN', (2, 5), (2, 6)),
            ('SPAN', (3, 5), (3, 6)),
            ('SPAN', (4, 5), (5, 5)),
            ('SPAN', (6, 5), (7, 5)),
            ('BACKGROUND', (0, 5), (7, 6), colorHeader),  # fin linea 6
            ('SPAN', (0, 8), (5, 8)),  # linea 8 y 9 horas y sobretiempos
            ('SPAN', (1, 9), (4, 9)),
            ('SPAN', (6, 8), (7, 9)),
            ('BACKGROUND', (0, 8), (7, 9), colorHeader),  # fin linea 9
            ('SPAN', (1, 10), (4, 10)),  # linea 10
            ('SPAN', (6, 10), (7, 10)),  # fin linea 10
            ('LEFTPADDING', (0, 0), (-1, -1), 1),
            ('RIGHTPADDING', (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('TOPPADDING', (0, 0), (-1, -1), 1),

            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (7, 0), 'BOTTOM'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ])

        t._argW[3] = 1*inch

        elements.append(t)
        elements.append(Spacer(1, 30))

        detalle_trabajador = []
        positions_in_tables = []
        i = 1
        for j in range(len(categories)-1):
            category = categories[j]
            reglas_salariales_empleado = """
            select e.name_related,e.identification_id,hpl.sequence,hpl.total,hpl.code,hpl.name ,sr.cod_sunat,hsrc.is_ing_or_desc
            from hr_payslip hp
            inner join hr_payslip_line hpl
            on hp.id=hpl.slip_id
            inner join hr_salary_rule as sr
            on sr.code = hpl.code
            inner join hr_employee e 
            on e.id = hpl.employee_id
            inner join hr_salary_rule_category hsrc
            on hsrc.id = hpl.category_id
            where date_from ='%s' and  date_to='%s' and e.identification_id='%s'
            and hpl.appears_on_payslip='t' and sr.appears_on_payslip='t'  and hpl.category_id=%d  and  hpl.total>0
            order by e.id,hpl.sequence
            """ % (date_start, date_end, empleado.identification_id, category.id)

            print reglas_salariales_empleado

            self.env.cr.execute(reglas_salariales_empleado)
            reglas_salariales_list = self.env.cr.dictfetchall()

            # if len(reglas_salariales_list) > 0:
            detalle_trabajador.append(
                [Paragraph(category.name.title(), style_cell_left), '', '', '', '', '', '', ''])
            positions_in_tables.append(('SPAN', (0, i), (7, i)))
            positions_in_tables.append(
                ('BACKGROUND', (0, i), (7, i), colorHeader))
            i = i+1

            for regla_salarial in reglas_salariales_list:
                # print "evaluando regla", regla_salarial
                # print regla_salarial['total']
                cod_sunat = Paragraph(
                    regla_salarial['cod_sunat'] if regla_salarial['cod_sunat'] else '', style_cell_left)
                namee = Paragraph(
                    regla_salarial['name'] if regla_salarial['name'] else '', style_cell_left)
                total = Paragraph('{0:.2f}'.format(
                    regla_salarial['total'] if regla_salarial['total'] else ''), style_cell_right)
                print regla_salarial['is_ing_or_desc']
                detalle_trabajador.append(
                    [cod_sunat, namee, '', '', '', total, '', ''] if regla_salarial['is_ing_or_desc'] == 'ingreso' else [cod_sunat, namee, '', '', '', '', total, ''])
                positions_in_tables.append(('SPAN', (1, i), (4, i)))
                i = i+1

        query_neto_pagar = """select e.name_related,e.identification_id,hpl.sequence,hpl.total,hpl.code,hpl.name ,sr.cod_sunat,hsrc.is_ing_or_desc
        from hr_payslip hp
        inner join hr_payslip_line hpl
        on hp.id=hpl.slip_id
        inner join hr_salary_rule as sr
        on sr.code = hpl.code
        inner join hr_employee e
        on e.id = hpl.employee_id
        inner join hr_salary_rule_category hsrc
        on hsrc.id = hpl.category_id
        where date_from ='%s' and  date_to='%s' and e.identification_id='%s' and hpl.code='%s'
        order by e.id,hpl.sequence""" % (date_start, date_end, empleado.identification_id, planilla_ajustes.cod_neto_pagar.code if planilla_ajustes else '')

        self.env.cr.execute(query_neto_pagar)
        neto_pagar = self.env.cr.dictfetchone()

        detalle_trabajador.append(
            [Paragraph(neto_pagar['name'].title() if neto_pagar else '', style_cell_left), '', '', '', '', '', '', Paragraph('{0:.2f}'.format(neto_pagar['total']) if neto_pagar else '', style_cell_right)])

        positions_in_tables.append(('SPAN', (0, i), (6, i)))
        positions_in_tables.append(
            ('BACKGROUND', (0, i), (7, i), colorHeader))
        i = i+1

        data = [
            [Paragraph('Codigo', style_cell), Paragraph('Conceptos', style_cell), '', '', '', Paragraph(
                'Ingresos S/.', style_cell), Paragraph('Descuentos S/.', style_cell), Paragraph('Neto S/.', style_cell)],
        ]+detalle_trabajador  # +[['1', '2', '3', '4', '5', '6', '7', '8']]

        t = Table(data, style=[
            ('SPAN', (1, 0), (4, 0)),  # cabecera

            ('BACKGROUND', (0, 0), (7, 0), colorHeader),  # fin linea 3

            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (7, 0), 'BOTTOM'),
            ('GRID', (0, 0), (7, 0), 0.5, colors.black),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
            ('LEFTPADDING', (0, 0), (-1, -1), 1),
            ('RIGHTPADDING', (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
        ]+positions_in_tables)
        t._argW[3] = 1.5*inch
        elements.append(t)
        elements.append(Spacer(1, 30))

        i = 0

        detalle_trabajador = []
        positions_in_tables = []
        category = categories[len(categories)-1]
        reglas_salariales_empleado = """
        select e.name_related,e.identification_id,hpl.sequence,hpl.total,hpl.code,hpl.name ,sr.cod_sunat,hsrc.is_ing_or_desc
        from hr_payslip hp
        inner join hr_payslip_line hpl
        on hp.id=hpl.slip_id
        inner join hr_salary_rule as sr
        on sr.code = hpl.code
        inner join hr_employee e 
        on e.id = hpl.employee_id
        inner join hr_salary_rule_category hsrc
        on hsrc.id = hpl.category_id
        where date_from ='%s' and  date_to='%s' and e.identification_id='%s'
        and hpl.appears_on_payslip='t' and sr.appears_on_payslip='t' and hpl.category_id=%d  and  hpl.total>0
        order by e.id,hpl.sequence
        """ % (date_start, date_end, empleado.identification_id, category.id)

        print reglas_salariales_empleado

        self.env.cr.execute(reglas_salariales_empleado)
        reglas_salariales_list = self.env.cr.dictfetchall()

        # if len(reglas_salariales_list) > 0:
        detalle_trabajador.append(
            [Paragraph(category.name.title(), style_cell_left), '', '', '', '', '', '', ''])
        positions_in_tables.append(('SPAN', (0, i), (7, i)))
        positions_in_tables.append(
            ('BACKGROUND', (0, i), (7, i), colorHeader))
        i = i+1

        for regla_salarial in reglas_salariales_list:
            print "evaluando regla", regla_salarial
            # print regla_salarial['total']
            cod_sunat = Paragraph(
                regla_salarial['cod_sunat'] if regla_salarial['cod_sunat'] else '', style_cell_left)
            namee = Paragraph(
                regla_salarial['name'] if regla_salarial['name'] else '', style_cell_left)
            total = Paragraph('{0:.2f}'.format(
                regla_salarial['total'] if regla_salarial['total'] else ''), style_cell_right)
            print regla_salarial['is_ing_or_desc']
            detalle_trabajador.append(
                [cod_sunat, namee, '', '', '', total, '', ''] if regla_salarial['is_ing_or_desc'] == 'ingreso' else [cod_sunat, namee, '', '', '', '', '', total])
            positions_in_tables.append(('SPAN', (1, i), (4, i)))
            i = i+1

        # +[['1', '2', '3', '4', '5', '6', '7', '8']]
        data = detalle_trabajador

        t = Table(data, style=[
            ('SPAN', (1, 0), (4, 0)),  # cabecera
            ('BACKGROUND', (0, 0), (7, 0), colorHeader),  # fin linea 3
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (7, 0), 'BOTTOM'),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.black),
            ('GRID', (0, 0), (7, 0), 0.5, colors.black),
            ('LEFTPADDING', (0, 0), (-1, -1), 1),
            ('RIGHTPADDING', (0, 0), (-1, -1), 1),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ('TOPPADDING', (0, 0), (-1, -1), 1),
        ]+positions_in_tables)
        t._argW[3] = 1.5*inch
        elements.append(t)

        data = [
            [' ', ' ',  ' ', ' ', ' ', ' ', ' ', ' ', ' '],
            [' ', ' ',  ' ', ' ', ' ', ' ', ' ', ' ', ' '],
            [' ', ' ',  ' ', ' ', ' ', ' ', ' ', ' ', ' '],
            [' ', ' ',  ' ', ' ', ' ', ' ', ' ', ' ', ' '],
            [' ', ' ',  ' ', ' ', ' ', ' ', ' ', ' ', ' '],
            [' ', ' ',  ' ', ' ', ' ', ' ', ' ', ' ', ' '],
            [' ', ' ',  ' ', ' ', ' ', ' ', ' ', ' ', ' '],
            [' ', ' ',  ' ', ' ', ' ', ' ', ' ', ' ', ' '],
            ['  ', 'FIRMA TRABAJADOR', ' ', '  ', ' ',
             ' ', '  ', 'FIRMA EMPLEADOR', '  ']
        ]

        t = Table(data, style=[
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),

            ('LINEABOVE', (0, -1), (2, -1), 1, colors.black),
            ('LINEABOVE', (6, -1), (8, -1), 1, colors.black),
        ])
        t._argW[3] = 1.5*inch
        elements.append(t)

        elements.append(PageBreak())
