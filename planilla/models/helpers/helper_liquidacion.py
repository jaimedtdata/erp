# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.addons.base.res.res_request import referenceable_models
from datetime import datetime, date
from calendar import monthrange
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError

class HelperLiquidacion(models.Model):
    _name = "planilla.helpers"

    def date_to_month(self,m):
        meses = {
            1:	"Enero",
            2:	"Febrero",
            3:	"Marzo",
            4: "Abril",
            5: "Mayo",
            6: "Junio",
            7: "Julio",
            8: "Agosto",
            9: "Setiembre",
            10: "Octubre",
            11: "Noviembre",
            12: "Diciembre",
        }
        return meses[m]

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




    @api.model
    def getAsignacionFamiliarByDate(self, fecha_ini, fecha_fin, employee_id, code):
        query = """
        select total from hr_payslip hp
        inner join hr_payslip_line hpl
        on hpl.slip_id = hp.id
        where hp.date_from >= '%s' and hp.date_to<= '%s' and hp.employee_id =%d
        and code ='%s'
        """ % (fecha_ini, fecha_fin, employee_id, code)

        self.env.cr.execute(query)
        res = self.env.cr.dictfetchone()
        return res['total'] if len(res) > 0 else 0.0

    @api.model
    def getBasicoByDate(self, fecha_ini, fecha_fin, employee_id, code):

        query = """
        select total from hr_payslip hp
        inner join hr_payslip_line hpl
        on hpl.slip_id = hp.id
        where hp.date_from >= '%s' and hp.date_to<= '%s' and hp.employee_id =%d
        and code ='%s'
        """ % (fecha_ini, fecha_fin, employee_id, code)

        self.env.cr.execute(query)
        res = self.env.cr.dictfetchone()
        return res['total'] if len(res) > 0 else 0.0

    @api.model
    def getSumFaltas(self, fecha_ini, fecha_fin, employee_id, code):

        query = """
        select sum(total) as total from hr_payslip hp
        inner join hr_payslip_line hpl
        on hpl.slip_id = hp.id
        where hp.date_from >= '%s' and hp.date_to<= '%s' and hp.employee_id =%d
        and code ='%s'
        group by hp.employee_id
        """ % (fecha_ini, fecha_fin, employee_id, code)

        self.env.cr.execute(query)
        res = self.env.cr.dictfetchone()
        return res['total'] if len(res) > 0 else 0.0


    @api.model
    def queryBeneficiosSociales(self, fecha_ini, fecha_fin, employee_id, code):
        query = """
        select sum(total) as total,count(total) as count from hr_payslip hp
        inner join hr_payslip_line hpl
        on hpl.slip_id = hp.id
        where hp.date_from >= '%s' and hp.date_to<= '%s' and hp.employee_id =%d
        and code ='%s'
        group by hp.employee_id
        """ % (fecha_ini, fecha_fin, employee_id, code)
        print "query beneficios sociales"
        print query
        self.env.cr.execute(query)
        res = self.env.cr.dictfetchone()
        return res['total'],res['count'] if len(res) > 0 else 0.0

    @api.model
    def calcula_comision_gratificacion_hrs_extras(self, contrato, fecha_computable, fecha_fin_nominas, meses, fecha_cese):
        print "CALCULANDO COMISIONES EN FECHAS ", fecha_computable, fecha_fin_nominas, meses
        parametros_gratificacion = self.env['planilla.gratificacion'].get_parametros_gratificacion()    
        fecha_inicio_nominas = date(
            fecha_computable.year, fecha_computable.month, 1)

        # query_nro_comisiones_periodo = """
        # select count(comisiones) count_comisiones,sum(comisiones) sum_comisiones
        # from  hr_payslip hp
        # where ( date_from>='%s' and date_to<='%s'  ) and
        # comisiones>0 and
        # hp.employee_id = %d
        # """ % (fecha_inicio_nominas, fecha_fin_nominas, contrato.employee_id)
        # print "query comisiones periodo ", query_nro_comisiones_periodo

        # self.env.cr.execute(query_nro_comisiones_periodo)

        # nro_comisiones_periodo = self.env.cr.dictfetchone()
        # count_comisiones = int(
        #     nro_comisiones_periodo['count_comisiones']) if nro_comisiones_periodo['count_comisiones'] else 0.0
        # sum_comisiones = float(
        #     nro_comisiones_periodo['sum_comisiones']) if nro_comisiones_periodo['sum_comisiones'] else 0.0

        sum_comisiones,count_comisiones = self.queryBeneficiosSociales(fecha_inicio_nominas,fecha_fin_nominas,contrato.employee_id,parametros_gratificacion.cod_comisiones.code)


        # si tiene mas de 3 comisiones recibidas en el rango entonces tiene grati de comision
        if count_comisiones >= 3:
            if meses == 6:
                print "sum comisiones ", sum_comisiones
                comisiones_periodo = round(sum_comisiones/6.0, 2)
            else:
                print "restare ", fecha_computable, ' - ', fecha_cese
                dias = abs(fecha_computable - fecha_cese)
                dias = dias.days+1
                comisiones_periodo = round(sum_comisiones/dias, 2)*30
                print "dias  calculo comisiones ", dias
                print "suma  calculo comisiones ", sum_comisiones
        else:
            comisiones_periodo = 0

        # query_nro_bonificaciones = """
        # select count(bonificaciones) count_bonificaciones,sum(bonificaciones) sum_bonificaciones
        # from  hr_payslip hp
        # where ( date_from>='%s' and date_to<='%s'  ) and
        # bonificaciones>0 and
        # hp.employee_id = %d
        # """ % (fecha_inicio_nominas, fecha_fin_nominas, contrato.employee_id)

        # print "promedio de bonificaciones ", query_nro_bonificaciones

        # self.env.cr.execute(query_nro_bonificaciones)

        # nro_bonificaciones_periodo = self.env.cr.dictfetchone()
        # count_bonificaciones = int(
        #     nro_bonificaciones_periodo['count_bonificaciones']) if nro_bonificaciones_periodo['count_bonificaciones'] else 0.0
        # sum_bonificaciones = float(
        #     nro_bonificaciones_periodo['sum_bonificaciones']) if nro_bonificaciones_periodo['sum_bonificaciones'] else 0.0

        sum_bonificaciones,count_bonificaciones = self.queryBeneficiosSociales(fecha_inicio_nominas,fecha_fin_nominas,contrato.employee_id,parametros_gratificacion.cod_bonificaciones.code)


        # si tiene mas de 3 bonificaciones recibidas en el rango entonces tiene grati de comision
        if count_bonificaciones >= 3:
            if meses == 6:
                promedio_bonificaciones = round(sum_bonificaciones/6.0, 2)
            else:
                # dias = abs(fecha_fin_nominas.day-fecha_computable.day) + 1
                dias = abs(fecha_computable - fecha_cese)
                dias = dias.days+1
                promedio_bonificaciones = round(
                    sum_bonificaciones/dias, 2)*30
        else:
            promedio_bonificaciones = 0.0

        # query_nro_horas_sobretiempo = """
        # select count(sobretiempos) count_sobretiempos,sum(sobretiempos) sum_sobretiempos
        # from  hr_payslip hp
        # where ( date_from>='%s' and date_to<='%s'  ) and
        # sobretiempos>0 and
        # hp.employee_id = %d
        # """ % (fecha_inicio_nominas, fecha_fin_nominas, contrato.employee_id)

        # self.env.cr.execute(query_nro_horas_sobretiempo)

        # nro_horas_sobretiempo_periodo = self.env.cr.dictfetchone()
        # count_sobretiempos = int(
        #     nro_horas_sobretiempo_periodo['count_sobretiempos']) if nro_horas_sobretiempo_periodo['count_sobretiempos'] else 0.0
        # sum_sobretiempos = float(
        #     nro_horas_sobretiempo_periodo['sum_sobretiempos']) if nro_horas_sobretiempo_periodo['sum_sobretiempos'] else 0.0

        sum_sobretiempos,count_sobretiempos = self.queryBeneficiosSociales(fecha_inicio_nominas,fecha_fin_nominas,contrato.employee_id,parametros_gratificacion.cod_sobretiempos.code)


        # si tiene mas de 3 pagos de sobretiempo recibidas en el rango entonces tiene grati de comision
        if count_sobretiempos >= 3:
            if meses == 6:
                promedio_horas_trabajo_extra = round(
                    sum_sobretiempos/6.0, 2)
            else:
                dias = abs(fecha_computable - fecha_cese)
                dias = dias.days+1
                promedio_horas_trabajo_extra = round(
                    sum_sobretiempos/dias, 2)*30
        else:
            promedio_horas_trabajo_extra = 0.0
        return comisiones_periodo, promedio_bonificaciones, promedio_horas_trabajo_extra

    def _diferencia_meses(self, d1, d2):
        if d1 > d2:
            raise UserError("Fecha %s no puede se rmayor a %s" % (d1, d2))
        res = relativedelta(d1, d2)
        return abs(res.months), abs(res.days)

    def diferencia_meses_gratificacion(self, d1, d2):
        meses, dias = self._diferencia_meses(d1, d2)
        if meses == 0 and dias == 0:
            return meses

        if d1.day > 1:
            meses -= 1
        if meses == 0 and dias == 0:
            return meses

        dias_mes_cese = monthrange(d2.year, d2.month)[1]

        if d2.day == dias_mes_cese:
            meses += 1
        else:
            meses -= 1
        return meses

    def diferencia_meses_dias(self, d1, d2):
        res = self.days360(d1, d2)
        dias_mes_cese = monthrange(d2.year, d2.month)[1]
        meses = int(res/30)
        dias = res-(meses*30)
        if dias_mes_cese == 30:
            dias += 1
        if dias == 30:
            meses += 1
            dias = 0

        return meses, dias

    def days360(self, start_date, end_date, method_eu=False):
        start_day = start_date.day
        start_month = start_date.month
        start_year = start_date.year
        end_day = end_date.day
        end_month = end_date.month
        end_year = end_date.year

        if (
            start_day == 31 or
            (
                method_eu is False and
                start_month == 2 and (
                    start_day == 29 or (
                        start_day == 28 and
                        calendar.isleap(start_year) is False
                    )
                )
            )
        ):
            start_day = 30

        if end_day == 31:
            if method_eu is False and start_day != 30:
                end_day = 1

                if end_month == 12:
                    end_year += 1
                    end_month = 1
                else:
                    end_month += 1
            else:
                end_day = 30
        return (
            end_day + (end_month * 30) + (end_year * 360) -
            start_day - (start_month * 30) - (start_year * 360)
        )
