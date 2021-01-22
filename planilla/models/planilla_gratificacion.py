# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.addons.base.res.res_request import referenceable_models
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
import sys
import io
from xlsxwriter.workbook import Workbook
import base64


class PlanillaGratificacion(models.Model):
    _name = "planilla.gratificacion"
    _rec_name = 'year'

    year = fields.Selection([
        ('2017', '2017'),
        ('2018', '2018'),
        ('2019', '2019'),
        ('2020', '2020'),
        ('2021', '2021'),
        ('2022', '2022'),
        ('2023', '2023'),
        ('2024', '2024'),
        ('2025', '2025'),
        ('2026', '2026'),
        ('2027', '2027'),
        ('2028', '2028'),
        ('2029', '2029'),
        ('2030', '2030'),
    ], string=u"Año")

    tipo = fields.Selection([('07', u"Gratificación Fiestas Patrias"),
                             ('12', u"Gratificación Navidad")], "Mes", required=1)

    date_start = fields.Date()
    date_end = fields.Date()

    plus_9 = fields.Boolean("Considerar Bono 9%")
    planilla_gratificacion_lines = fields.One2many(
        'planilla.gratificacion.line', 'planilla_gratificacion_id', "Lineas")

    deposit_date = fields.Date(u'Fecha depósito')

    @api.multi
    @api.depends('tipo','year')
    @api.onchange('tipo','year')
    def change_dates(self):
        self.ensure_one()
        if self.year:
            if self.tipo == '07':
                self.date_start = date(int(self.year), 6, 1)
                self.date_end = date(int(self.year), 6, 30)
            else:
                self.date_start = date(int(self.year), 12, 1)
                self.date_end = date(int(self.year), 12, 31)

    @api.multi
    def write(self, vals):
        print "vals ", vals
        if vals and "tipo"in vals:
            if vals['tipo'] == '07':
                vals['date_start'] = date(int(self.year), 6, 1)
                vals['date_end'] = date(int(self.year), 6, 30)
            else:
                vals['date_start'] = date(int(self.year), 12, 1)
                vals['date_end'] = date(int(self.year), 12, 31)
        return super(PlanillaGratificacion, self).write(vals)

    @api.model
    def create(self, vals):
        print vals
        if len(self.search([('year', '=', vals['year']), ('tipo', '=', vals['tipo'])])) >= 1:
            raise UserError(
                "Ya existe un registros %s %s" % (vals['year'], vals['tipo']))
        else:
            print "MIS AÑOS ",self.year
            if vals['tipo'] == '07':
                vals['date_start'] = date(int(vals['year']), 6, 1)
                vals['date_end'] = date(int(vals['year']), 6, 30)
            else:
                vals['date_start'] = date(int(vals['year']), 12, 1)
                vals['date_end'] = date(int(vals['year']), 12, 31)
            return super(PlanillaGratificacion, self).create(vals)

    @api.model
    def get_parametros_gratificacion(self):

        parametros_gratificacion = self.env['planilla.parametros.gratificacion'].search([
        ], limit=1)
        # if not parametros_gratificacion.cod_he25.codigo:
        #     raise UserError(
        #         'Debe configurar parametros de gratificacion cod_he25 Nomina->configuracion->parametros gratificacion')
        # elif not parametros_gratificacion.cod_he35.codigo:
        #     raise UserError(
        #         'Debe configurar parametros de gratificacion cod_he35 Nomina->configuracion->parametros gratificacion')
        # elif not parametros_gratificacion.cod_he100.codigo:
        # raise UserError(
        # 'Debe configurar parametros de gratificacion cod_he100 Nomina->configuracion->parametros gratificacion')
        if not parametros_gratificacion.cod_gratificacion.codigo:
            raise UserError(
                'Debe configurar parametros de gratificacion cod_gratificacion Nomina->configuracion->parametros gratificacion')
        elif not parametros_gratificacion.cod_bonificaciones.code:
            raise UserError(
                'Debe configurar parametros de gratificacion cod_bonificaciones Nomina->configuracion->parametros gratificacion')
        elif not parametros_gratificacion.cod_basico.code:
            raise UserError(
                'Debe configurar parametros de gratificacion cod_basico Nomina->configuracion->parametros gratificacion')
        elif not parametros_gratificacion.cod_asignacion_familiar.code:
            raise UserError(
                'Debe configurar parametros de gratificacion cod_asignacion_familiar Nomina->configuracion->parametros gratificacion')
        elif not parametros_gratificacion.cod_bonificacion_9.code:
            raise UserError(
                'Debe configurar parametros de gratificacion cod_bonificacion_9 Nomina->configuracion->parametros gratificacion')
        elif not parametros_gratificacion.cod_dias_faltas.codigo:
            raise UserError(
                'Debe configurar parametros de gratificacion cod_dias_faltas Nomina->configuracion->parametros gratificacion')
        elif not parametros_gratificacion.cod_comisiones.code:
            raise UserError(
                'Debe configurar parametros de gratificacion cod_comisiones Nomina->configuracion->parametros gratificacion')
        elif not parametros_gratificacion.cod_sobretiempos.code:
            raise UserError(
                'Debe configurar parametros de gratificacion cod_sobretiempos Nomina->configuracion->parametros gratificacion')
        else:
            return parametros_gratificacion

    @api.multi
    def calcular_gratificacion(self):
        print "========0CALCULANDO GRATIFICACION =================="
        self.ensure_one()
        helper_liquidacion = self.env['planilla.helpers']
        self.planilla_gratificacion_lines.unlink()
        tabla_montos_primera_mitad = False
        parametros_gratificacion = self.get_parametros_gratificacion()
        parametros_eps = self.env['planilla.parametros.essalud.eps'].get_parametros_essalud_eps(
        )

        # print parametros_gratificacion.cod_he100.codigo
        # import pudb;pudb.set_trace()
        if self.tipo == '07':
            # el rango fin deberia ser 30 del mes 6
            # pero para asegurarme que al menos haya
            # un mes para que se le pague la gratificacion
            # le aumentare la fecha final que sea mayor a 31 del mes 7
            # ya que si es menor a esa fecha o bien seso y bien sesara el mes 7
            # por lo que le corresponderia no gratificacion sino liquidacion
            #
            # para el rango de inicio para asegurarme de que tenga al menos un mes
            # el rango de inicio de resumen_periodo deberia ser como minimo menor o igual a el 1 del mes 6
            rango_inicio_contrato = date(int(self.year), 6, 1)
            rango_fin_contrato = date(int(self.year), 6, 30)
            rango_inicio_planilla = date(int(self.year), 1, 1)
            rango_fin_planilla = date(int(self.year), 6, 30)
            tabla_montos_primera_mitad = True
        else:
            rango_inicio_contrato = date(int(self.year), 11, 1)
            # rango_fin_contrato = date(int(self.year), 12, 31) #30 nov
            rango_fin_contrato = date(int(self.year), 11, 30)  # 30 nov
            rango_inicio_planilla = date(int(self.year), 7, 1)
            # rango_fin_planilla = date(int(self.year), 12, 31)
            rango_fin_planilla = date(int(self.year), 11, 30)

        query_gratificacion = """
        select T.tipo_empresa,T.id,T.employee_id,T.identification_id, T.a_paterno,T.a_materno,T.nombres,T.date_start,T.date_end,sum(faltas) as faltas,max(T.basico) as basico,max(T.afam) as afam,max(T.bo9) as bo9
        from (
        select hc.id,hc.employee_id, hc.date_start,hc.date_end,
        he.identification_id,
        he.tipo_empresa,
        he.a_paterno,
        he.a_materno,   
        he.nombres,
        (case when  hp.date_from>='%s' and hp.date_to<='%s'   then hp.basico else 0 end) as basico ,
        (case when ( date_from>='%s' and date_to<='%s'  ) then hp.asignacion_familiar else 0 end) as afam,
        (case when ( date_from>='%s' and date_to<='%s'  ) then hp.bonificacion_9 else 0 end) as bo9,
        hp.dias_faltas  as faltas
        from hr_payslip hp
        inner join hr_contract hc
        on hc.id = hp.contract_id
        inner join hr_employee he
        on he.id = hp.employee_id
        where ( date_start <= '%s' ) and (date_end is null or date_end>'%s')
        and( date_from>='%s' and date_to<='%s'  )
        ) as T
        group by T.id,T.employee_id,T.identification_id, T.a_paterno,T.a_materno,T.nombres,T.date_start,T.date_end,T.tipo_empresa
        order by T.id
        """ % (rango_inicio_contrato, rango_fin_planilla,
               rango_inicio_contrato, rango_fin_planilla,
               rango_inicio_contrato, rango_fin_planilla,
               rango_inicio_contrato, rango_fin_contrato,
               rango_inicio_planilla, rango_fin_planilla)

        print query_gratificacion
        self.env.cr.execute(query_gratificacion)


        contratos = self.env.cr.dictfetchall()
        # itero los rangos de fechas de cada resumen_periodo
        # el objetivo es encontrar el maximo rango de
        # fechas continuas
        fechas = list()
        for i in range(len(contratos)):
            resumen_periodo = contratos[i]
            print "mi resumen_periodo actual ", resumen_periodo
            contratos_empleado = self.env['hr.contract'].search(
                [('employee_id', '=',  resumen_periodo['employee_id']), ('date_end', '<=', resumen_periodo['date_end'])], order='date_end desc')

            fecha_ini = fields.Date.from_string(
                contratos_empleado[0].date_start)
            fecha_fin_contrato = fields.Date.from_string(
                contratos_empleado[0].date_end)
            # 2 busco los contratos anteriores que esten continuos(no mas de un dia de diferencia entre contratos)
            for i in range(1, len(contratos_empleado)):
                c_empleado = contratos_empleado[i]
                fecha_fin = fields.Date.from_string(c_empleado.date_end)
                if abs(((fecha_fin)-(fecha_ini)).days) == 1:
                    fecha_ini = fields.Date.from_string(c_empleado.date_start)
            fecha_fin = fecha_fin_contrato
            # datetime.combine(d, datetime.min.time()) fecha_ini#datetime(int(fecha_ini[:4]), int(fecha_ini[5:7]), int(fecha_ini[8:10]))

            # if fecha_ini < rango_inicio_planilla:
            #     meses = 6
            # elif fecha_ini.day > 1:
            #     # el mes que esta no cuenta por eso se deja como esta la resta
            #     meses = helper_liquidacion.diferencia_meses_gratificacion(fecha_ini,rango_fin_planilla)
            # else:
            #     # mas un mes por que el mes que esta iniciando cuenta
            meses = helper_liquidacion.diferencia_meses_gratificacion(
                fecha_ini, rango_fin_planilla)

            if fecha_ini < rango_inicio_planilla:
                fecha_computable = rango_inicio_planilla
            else:
                fecha_computable = fecha_ini

            fecha_inicio_nominas = date(
                fecha_computable.year, fecha_computable.month, 1)

            conceptos = self.env['hr.payslip'].search([('date_from', '>=', fecha_inicio_nominas), (
                'date_to', '<=', rango_fin_planilla), ('employee_id', '=', resumen_periodo['employee_id'])], order='date_to desc')

            verificar_meses, _ = helper_liquidacion.diferencia_meses_dias(
                fecha_inicio_nominas, rango_fin_planilla)
            print "VERIFICAR MESES ", verificar_meses

            # if dias==0:
            #     verificar_meses-=1

            if len(conceptos) != verificar_meses:
                fecha_encontradas = ' '.join(
                    ['\t-'+x.name+'\n' for x in conceptos])
                if not fecha_encontradas:
                    fecha_encontradas = '"No tiene nominas"'
                raise UserError(
                    'Error en GRATIFICACION: El empleado %s debe tener nominas desde:\n %s hasta %s pero solo tiene nominas en las siguientes fechas:\n %s \nfaltan %d nominas, subsanelas por favor ' % (
                        contratos_empleado[0].employee_id.name_related, fecha_inicio_nominas, rango_fin_planilla, fecha_encontradas, abs(len(
                            conceptos) - (verificar_meses))
                    ))

            basico = helper_liquidacion.getBasicoByDate(date(rango_fin_planilla.year, rango_fin_planilla.month, 1),rango_fin_planilla,resumen_periodo['employee_id'],parametros_gratificacion.cod_basico.code )  # conceptos[0].basico if conceptos else 0.0
            faltas = helper_liquidacion.getSumFaltas(date(rango_fin_planilla.year, rango_fin_planilla.month, 1),rango_fin_planilla,resumen_periodo['employee_id'],parametros_gratificacion.cod_dias_faltas.codigo ) #sum([x.dias_faltas for x in conceptos])
            afam = helper_liquidacion.getAsignacionFamiliarByDate(fecha_inicio_nominas,rango_fin_planilla,resumen_periodo['employee_id'],parametros_gratificacion.cod_asignacion_familiar.code )  #conceptos[0].asignacion_familiar if conceptos else 0.0

            comisiones_periodo, promedio_bonificaciones, promedio_horas_trabajo_extra = helper_liquidacion.calcula_comision_gratificacion_hrs_extras(
                contratos_empleado[0], fecha_computable, rango_fin_planilla, meses, rango_fin_planilla)

            bonificacion_9 = 0
            bonificacion = promedio_bonificaciones
            comision = comisiones_periodo
            dias = 0
            # faltas = float(resumen_periodo['faltas']
            #                ) if resumen_periodo['faltas'] else 0.0

            rem_computable = basico + \
                bonificacion+comision + \
                afam+promedio_horas_trabajo_extra
            monto_x_mes = round(rem_computable/6.0, 2)
            monto_x_dia = round(monto_x_mes/30.0, 2)
            monto_x_meses = round(
                monto_x_mes*meses, 2) if meses != 6 else rem_computable
            monto_x_dias = round(monto_x_dia*dias, 2)
            total_faltas = round(monto_x_dia*faltas, 2)
            total_gratificacion = (monto_x_meses+monto_x_dias)-total_faltas

            if  resumen_periodo['tipo_empresa']=='microempresa':
                total_gratificacion=0
            elif resumen_periodo['tipo_empresa']=='pequenhaempresa':
                total_gratificacion/=2.0

            

            print "mi resumen_periodo ", resumen_periodo
            print "mi plus9 ",  self.plus_9
            if self.plus_9:
                print contratos_empleado[0].tipo_seguro 
                if contratos_empleado[0].tipo_seguro == 'essalud':
                    bonificacion_9 = parametros_eps.ratio_essalud / \
                        100.0*float(total_gratificacion)
                else:
                    bonificacion_9 = parametros_eps.ratio_eps / \
                        100.0*float(total_gratificacion)

            vals = {
                'planilla_gratificacion_id': self.id,
                'employee_id': resumen_periodo['employee_id'],
                'identification_number': resumen_periodo['identification_id'],
                'last_name_father': resumen_periodo['a_paterno'],
                'last_name_mother': resumen_periodo['a_materno'],
                'names': resumen_periodo['nombres'],
                'fecha_ingreso': fecha_ini,
                'meses': meses,
                'faltas': faltas,
                'basico': basico,
                'a_familiar': afam,
                'comision': comisiones_periodo,
                'bonificacion': bonificacion,
                'horas_extras_mean': promedio_horas_trabajo_extra,
                'remuneracion_computable': rem_computable,
                'monto_x_mes': monto_x_mes,
                'monto_x_dia': monto_x_dia,
                'monto_x_meses': monto_x_meses,
                'monto_x_dias': monto_x_dias,
                'total_faltas': total_faltas,
                'total_gratificacion': total_gratificacion,
                'plus_9': bonificacion_9,
                'total': total_gratificacion+bonificacion_9
            }
            print "datos finales para ", resumen_periodo['nombres']
            print "datos finales para ", vals
            self.planilla_gratificacion_lines.create(vals)
        return True

        # abs(datetime(2017,2,1).month-datetime(2017,6,30).month)

        # # return date(self._default_fecha_fin().year, 1, 1)
        # todayDate = date.today()
        # # if todayDate.day > 25:
        # #     todayDate += timedelta(7)
        # return todayDate.replace(day=1)

    @api.multi
    def get_excel(self):
        # -------------------------------------------Datos---------------------------------------------------
        reload(sys)
        sys.setdefaultencoding('iso-8859-1')
        output = io.BytesIO()

        # direccion = self.env['main.parameter'].search([])[0].dir_create_file
        workbook = Workbook('CTS%s-%s.xlsx' % (self.year, self.tipo))
        worksheet = workbook.add_worksheet(
            'CTS%s-%s.xlsx' % (self.year, self.tipo))
        lines = self.env['planilla.gratificacion.line'].search(
            [('planilla_gratificacion_id', "=", self.id)])
        self.getSheetGratificacion(workbook,worksheet,lines)
        
        workbook.close()

        f = open('CTS%s-%s.xlsx' % (self.year, self.tipo), 'rb')

        vals = {
            'output_name': 'CTS%s-%s.xlsx' % (self.year, dict(self._fields['tipo'].selection).get(self.tipo)),
            'output_file': base64.encodestring(''.join(f.readlines())),
        }

        sfs_id = self.env['planilla.export.file'].create(vals)

        # mod_obj = self.env['ir.model.data']
        # act_obj = self.env['ir.actions.act_window']
        # sfs_id = self.env['export.file.save'].create(vals)

        return {
            "type": "ir.actions.act_window",
            "res_model": "planilla.export.file",
            "views": [[False, "form"]],
            "res_id": sfs_id.id,
            "target": "new",
        }

    @api.multi
    def getSheetGratificacion(self,workbook,worksheet,lines):
                # ----------------Formatos------------------
        basic = {
            'align'		: 'left',
            'valign'	: 'vcenter',
            'text_wrap'	: 1,
            'font_size'	: 9,
            'font_name'	: 'Calibri'
        }

        basic_center = basic.copy()
        basic_center['align'] = 'center'

        numeric = basic.copy()
        numeric['align'] = 'right'
        numeric['num_format'] = '0.00'

        numeric_bold_format = numeric.copy()
        numeric_bold_format['bold'] = 1

        bold = basic.copy()
        bold['bold'] = 1

        header = bold.copy()
        header['bg_color'] = '#A9D0F5'
        header['border'] = 1
        header['align'] = 'center'

        title = bold.copy()
        title['font_size'] = 15

        basic_format = workbook.add_format(basic)
        basic_center_format = workbook.add_format(basic_center)
        numeric_format = workbook.add_format(numeric)
        bold_format = workbook.add_format(bold)
        numeric_bold_format = workbook.add_format(numeric_bold_format)
        header_format = workbook.add_format(header)
        title_format = workbook.add_format(title)

        nro_columnas = 17

        tam_col = [0]*nro_columnas

        # ----------------------------------------------Título--------------------------------------------------
        rc = self.env['res.company'].search([])[0]
        cabecera = rc.name
        worksheet.merge_range('A1:B1', cabecera, title_format)
        # ---------------------------------------------Cabecera------------------------------------------------
        worksheet.merge_range('A2:D2', "CTS", bold_format)
        worksheet.write('A3', u"Año :", bold_format)

        worksheet.write('B3', self.year, bold_format)

        columnas = ["Orden",
                    "Nro Documento",
                    "Apellido\nPaterno",
                    "Apellido\nMaterno",
                    "Nombres",
                    "Fecha\nIngreso",
                    "Meses",
                    "Faltas",
                    u"Básico",
                    "A.\nFamiliar",
                    u"Comision",
                    u"Bonificación",
                    "PROM. HRS\n EXTRAS",
                    "Rem.\nCom.",
                    "M. por\nMes",
                    u"M. por\nDía",
                    "Grat. Por\nlos Meses",
                    u"Grat. Por\nlos Días",
                    "Total\nFaltas",
                    u"Total\nGratificación",
                    "Bonif.\n9%", "Total\nPagar"]
        fil = 4

        for col in range(len(columnas)):
            worksheet.write(fil, col, columnas[col], header_format)
        worksheet.set_row(fil, 22)

        # ------------------------------------------Insertando Data----------------------------------------------
        fil = 5

        totals = [0]*14

        for line in lines:
            col = 0
            worksheet.write(fil, col, line.id, basic_format)
            col += 1
            worksheet.write(fil, col, line.identification_number, basic_format)
            col += 1
            worksheet.write(fil, col, line.last_name_father, basic_format)
            col += 1
            worksheet.write(fil, col, line.last_name_mother, basic_format)
            col += 1
            worksheet.write(fil, col, line.names, basic_format)
            col += 1
            worksheet.write(fil, col, line.fecha_ingreso, basic_center_format)
            col += 1
            worksheet.write(fil, col, line.meses, basic_center_format)
            col += 1
            worksheet.write(fil, col, line.faltas, basic_center_format)
            col += 1
            worksheet.write(fil, col, line.basico, numeric_format)
            totals[col-8] += line.basico
            col += 1
            worksheet.write(fil, col, line.a_familiar, numeric_format)
            totals[col-8] += line.a_familiar
            col += 1
            worksheet.write(fil, col, line.comision, numeric_format)
            totals[col-8] += line.comision
            col += 1
            worksheet.write(fil, col, line.bonificacion, numeric_format)
            totals[col-8] += line.bonificacion
            col += 1
            worksheet.write(fil, col, line.horas_extras_mean, numeric_format)
            totals[col-8] += line.horas_extras_mean
            col += 1
            worksheet.write(
                fil, col, line.remuneracion_computable, numeric_format)
            totals[col-8] += line.remuneracion_computable
            col += 1
            worksheet.write(fil, col, line.monto_x_mes, numeric_format)
            totals[col-8] += line.monto_x_mes
            col += 1
            worksheet.write(fil, col, line.monto_x_dia, numeric_format)
            totals[col-8] += line.monto_x_dia
            col += 1
            worksheet.write(fil, col, line.monto_x_meses, numeric_format)
            totals[col-8] += line.monto_x_meses
            col += 1
            worksheet.write(fil, col, line.monto_x_dias, numeric_format)
            totals[col-8] += line.monto_x_dias
            col += 1
            worksheet.write(fil, col, line.total_faltas, numeric_format)
            totals[col-8] += line.total_faltas
            col += 1
            worksheet.write(fil, col, line.total_gratificacion, numeric_format)
            totals[col-8] += line.total_gratificacion
            col += 1
            worksheet.write(fil, col, line.plus_9, numeric_format)
            totals[col-8] += line.plus_9
            col += 1
            worksheet.write(fil, col, line.total, numeric_format)
            totals[col-8] += line.total
            fil += 1

        col = 8
        for i in range(len(totals)):
            worksheet.write(fil, col, totals[i], numeric_bold_format)
            col += 1
        col_size = [5, 12, 20]
        worksheet.set_column('A:A', col_size[0])
        worksheet.set_column('B:E', col_size[1])
        worksheet.set_column('F:F', col_size[2])
        worksheet.set_column('G:U', col_size[1])


class PlanillaGratificacionLine(models.Model):
    _name = 'planilla.gratificacion.line'

    planilla_gratificacion_id = fields.Many2one(
        'planilla.gratificacion', "Planilla Gratificacion")
    # fields.Many2one('hr.employee', "Empleado")
    employee_id = fields.Integer(index=True)
    # order = fields.Integer("Orden", compute='get_order')
    identification_number = fields.Char("Nro Documento", size=9)
    # code = fields.Char("Código", size=4)
    last_name_father = fields.Char("Apellido Paterno")
    last_name_mother = fields.Char("Apellido Materno")
    names = fields.Char("Nombres")
    fecha_ingreso = fields.Date("Fecha Ingreso")
    meses = fields.Integer("Meses")
    faltas = fields.Integer("Faltas")
    basico = fields.Float(u"Básico", digits=(10, 2))
    a_familiar = fields.Float("A. Familiar", digits=(10, 2))
    comision = fields.Float(u"Comision", digits=(10, 2))
    bonificacion = fields.Float(u"Bonificación", digits=(10, 2))
    horas_extras_mean = fields.Float("Prom. Hras extras", digits=(10, 2))
    remuneracion_computable = fields.Float("Rem. Com.", digits=(10, 2))
    monto_x_mes = fields.Float("M. por Mes", digits=(10, 2))
    monto_x_dia = fields.Float(u"M. por Día", digits=(10, 2))
    monto_x_meses = fields.Float("Grat. Por los\nMeses", digits=(10, 2))
    monto_x_dias = fields.Float(u"Grat. Por los\nDías", digits=(10, 2))
    total_faltas = fields.Float(u"Total Faltas", digits=(10, 2))
    total_gratificacion = fields.Float(u"Total\nGratificación", digits=(10, 2))
    plus_9 = fields.Float(u"Bonif. 9%", digits=(10, 2))
    # adelanto = fields.Float(u'Adelanto', digits=(10, 2))
    # total_to_pay = fields.Float(u'Gratificación a pagar', digits=(10, 2))
    total = fields.Float(u"Total Pagar", digits=(10, 2))
