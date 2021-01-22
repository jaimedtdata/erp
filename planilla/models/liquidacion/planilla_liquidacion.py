# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.addons.base.res.res_request import referenceable_models
from datetime import datetime, date, timedelta
import calendar
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
import sys
import io
from xlsxwriter.workbook import Workbook
import base64
from dateutil.relativedelta import *

from reportlab.lib.enums import TA_JUSTIFY
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.lib.colors import magenta, red , black , blue, gray, white, Color, HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Table
from reportlab.lib.units import  cm,mm
from reportlab.lib.utils import simpleSplit
import os
import decimal
class PlanillaLiquidacion(models.Model):
    _name = "planilla.liquidacion"
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
    ], string=u"Año", required="1")

    month = fields.Selection([
        (1, "Enero"),
        (2, "Febrero"),
        (3, "Marzo"),
        (4, "Abril"),
        (5, "Mayo"),
        (6, "Junio"),
        (7, "Julio"),
        (8, "Agosto"),
        (9, "Setiembre"),
        (10, "Octubre"),
        (11, "Noviembre"),
        (12, "Diciembre"),
    ], string="Mes", required="1")

    date_start = fields.Date()
    date_end = fields.Date()

    tipo_cambio = fields.Float("Tipo de Cambio", required=True, default=0)
    # tipo = fields.Selection([('07', u"Gratificación Fiestas Patrias"),
    #                          ('12', u"Gratificación Navidad")], "Mes", required=1)
    plus_9 = fields.Boolean("Considerar Bono 9%")
    # planilla_gratificacion_lines = fields.Many2one(
    #     'planilla.gratificacion.line' , "Lineas",copy=True)
    planilla_cts_lines = fields.One2many(
        'planilla.liquidacion.cts.line', 'planilla_liquidacion_id', u'Línea CTS')
    planilla_gratificacion_lines = fields.One2many(
        'planilla.liquidacion.gratificacion.line', 'planilla_liquidacion_id', u'Línea Gratificacion')
    planilla_vacaciones_lines = fields.One2many(
        'planilla.liquidacion.vacaciones.line', 'planilla_liquidacion_id', u'Línea Vacaciones')


    def is_number_tryexcept(self,s):
        """ Returns True is string is a number. """
        try:
            float(s)
            return True
        except ValueError:
            return False

    @api.multi
    def cabezera(self,c,wReal,hReal,company):
        import os
        # direccion = self.env['main.parameter'].search([])[0].dir_create_file

        c.setFont("Arimo-Bold", 6)
        c.setFillColor(black)
        endl = 12
        pos_inicial = hReal-10
        pagina = 1

        c.drawCentredString((wReal/2.00),pos_inicial, "LIQUIDACIÓN DE BENEFICIOS SOCIALES")
        pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
        c.drawCentredString((wReal/2.00),pos_inicial, "LIQUIDACIÓN DE BENEFICIOS SOCIALES QUE OTORGA")
        pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
        c.drawCentredString((wReal/2.00),pos_inicial,company.name)

        imgdata = base64.b64decode(company.logo_web)
        new_image_handle = open('company_logo_tmp.jpg', 'wb')
        new_image_handle.write(imgdata)
        new_image_handle.close()
        c.drawImage('company_logo_tmp.jpg',20, hReal-20, width=120, height=50,mask='auto')

    @api.multi
    def verify_linea(self,c,wReal,hReal,posactual,valor,pagina):
        if posactual <10:
            c.showPage()
            self.cabezera(c,wReal,hReal)

            c.setFont("Arimo-Bold", 6)
            return pagina+1,hReal-60
        else:
            return pagina,posactual-valor

    @api.multi
    def get_liquidacion_wizard(self):
        return {
            'name': 'Exportar liquidacion pdf',
            "type": "ir.actions.act_window",
            "res_model": "planilla.liquidacion.pdf.wizard",
            'view_type': 'form',
            'view_mode': 'form',
            "views": [[False, "form"]],
            "target": "new",
            'context': {'current_id': self.id,'employees':[line.employee_id for line in self.planilla_vacaciones_lines]}            
        }

    @api.multi
    def get_liquidacion_pdf(self,employee_ids):
        if not hasattr(employee_ids, '__iter__'):
            employee_ids = [employee_ids]
        self.reporteador(employee_ids)
        vals = {
            'output_name': 'Planilla_liquidacion.pdf',
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
    def reporteador(self, employee_ids):
        company = self.env['res.company'].search([], limit=1)[0]

        reload(sys)
        sys.setdefaultencoding('iso-8859-1')
        width , height = A4  # 595 , 842
        wReal = width- 30
        hReal = height - 40
        c = canvas.Canvas( "planilla_tmp.pdf", pagesize=A4)
        inicio = 0
        pos_inicial = hReal-60
        endl = 9
        font_size = 6
        pagina = 1
        textPos = 0
        ruta_modulo= os.path.join(os.path.dirname(os.path.abspath(__file__)))
        pdfmetrics.registerFont(TTFont('Arimo-Bold',ruta_modulo+ '/../../fonts/Arimo-Bold.ttf'))
        pdfmetrics.registerFont(TTFont('Arimo-BoldItalic',ruta_modulo+ '/../../fonts/Arimo-BoldItalic.ttf'))
        pdfmetrics.registerFont(TTFont('Arimo-Italic', ruta_modulo+ '/../../fonts/Arimo-Italic.ttf'))
        pdfmetrics.registerFont(TTFont('Arimo-Regular', ruta_modulo+'/../../fonts/Arimo-Regular.ttf'))


        hllv = self.planilla_vacaciones_lines.search([('employee_id','in',employee_ids),('planilla_liquidacion_id','=',self.id)])
        for i in hllv:
            self.cabezera(c,wReal,hReal,company)
            hllg = self.planilla_gratificacion_lines.search([('employee_id','=',i.employee_id),('planilla_liquidacion_id','=',self.id)])[0]
            hllc = self.planilla_cts_lines.search([('employee_id','=',i.employee_id),('planilla_liquidacion_id','=',self.id)])[0]
            # employee_id = self.env['hr.employee'].search([''])

            total_sum = 0

            c.setFont("Arimo-Bold", font_size)
            c.drawString( 30 , pos_inicial, u"DATOS PERSONALES")
            pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
            c.drawString( 40 , pos_inicial, u"Nombres y Apellidos")
            c.drawString( 140 , pos_inicial, u":")
            c.setFont("Arimo-Regular", font_size)
            c.drawString( 150 , pos_inicial, i.contract_id.employee_id.name_related if i.contract_id.employee_id.name_related else '')
            pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
            c.setFont("Arimo-Bold", font_size)
            c.drawString( 40 , pos_inicial, u"DNI Nº")
            c.drawString( 140 , pos_inicial, u":")
            c.setFont("Arimo-Regular", font_size)
            c.drawString( 150 , pos_inicial, i.contract_id.employee_id.identification_id if i.contract_id.employee_id.identification_id else '')
            pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
            c.setFont("Arimo-Bold", font_size)
            c.drawString( 40 , pos_inicial, u"Cargo")
            c.drawString( 140 , pos_inicial, u":")
            c.setFont("Arimo-Regular", font_size)
            c.drawString( 150 , pos_inicial, i.contract_id.employee_id.job_id.name if i.contract_id.employee_id.job_id.name else '')
            pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
            c.setFont("Arimo-Bold", font_size)
            c.drawString( 40 , pos_inicial, u"Fecha de Ingreso")
            c.drawString( 140 , pos_inicial, u":")
            c.setFont("Arimo-Regular", font_size)
            c.drawString( 150 , pos_inicial, i.contract_id.date_start if i.contract_id.date_start else '')
            pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
            c.setFont("Arimo-Bold", font_size)
            c.drawString( 40 , pos_inicial, u"Fecha de Cese")
            c.drawString( 140 , pos_inicial, u":")
            c.setFont("Arimo-Regular", font_size)
            c.drawString( 150 , pos_inicial, i.contract_id.date_end if i.contract_id.date_end else '')
            pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)			
            c.setFont("Arimo-Bold", font_size)
            c.drawString( 40 , pos_inicial, u"Motivo")
            c.drawString( 140 , pos_inicial, u":")
            c.setFont("Arimo-Regular", font_size)
            c.drawString( 150 , pos_inicial,  '')
            pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
            c.setFont("Arimo-Bold", font_size)
            c.drawString( 40 , pos_inicial, u"Afiliación")
            c.drawString( 140 , pos_inicial, u":")
            c.setFont("Arimo-Regular", font_size)
            c.drawString( 150 , pos_inicial, i.contract_id.afiliacion_id.entidad if i.contract_id.afiliacion_id.entidad else '')
            pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
            c.setFont("Arimo-Bold", font_size)
            c.drawString( 40 , pos_inicial, u"Último Sueldo Básico")
            c.drawString( 140 , pos_inicial, u":")
            c.setFont("Arimo-Regular", font_size)
            c.drawString( 150 , pos_inicial, ('{:,.2f}'.format(decimal.Decimal ("%0.2f" % i.contract_id.wage )) if i.basico else "0.00") + " "*4 + u"NUEVOS SOLES")
            c.setFont("Arimo-Bold", font_size)
            c.drawString( 240 , pos_inicial, u"Tipo de Cambio")
            c.drawString( 280 , pos_inicial, u":")
            c.setFont("Arimo-Regular", font_size)
            c.drawString( 290 , pos_inicial, str(self.tipo_cambio) if self.tipo_cambio else '0.00')
            pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)


            c.setFont("Arimo-Bold", font_size)
            c.drawString( 40 , pos_inicial, u"Tiempo de Servicio")
            c.drawString( 140 , pos_inicial, u":")
            if i.contract_id.date_start and i.contract_id.date_end:
                fmt = '%Y-%m-%d'
                f1 = datetime.strptime(i.contract_id.date_start,  fmt)
                f2 =datetime.strptime(i.contract_id.date_end, fmt)
                fr = relativedelta(f2,f1) + relativedelta(days=1)
                txt = ""

                res = self.env['planilla.helpers'].days360(f1,f2+relativedelta(days=1))
                meses = int(res/30)
                anios = int(meses/12)
                # meses1 = meses - int(meses/12)
                meses1 = meses - (anios*12)
                dias = res-(meses*30)
                


                if fr.years:
                    txt += str(anios) + u" AÑO(S) "
                if fr.months:
                    txt += str(meses1) + u" MES(ES)"
                if fr.days:
                    txt += str(dias) + u" DÍA(S)"
                c.setFont("Arimo-Regular", font_size)
                c.drawString( 150 , pos_inicial, txt)




            pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl*2,pagina)

            c.setFont("Arimo-Bold", font_size)
            c.drawString( 30 , pos_inicial, u"BASES DE CÁLCULO")
            pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
            basraw = i.basico
            # afraw  = self.env['hr.parameters'].search([('num_tipo','=',10001)])[0].monto if i.contract_id.employee_id.children_number else 0
            # if i.contract_id.employee_id.is_practicant:
            #     afraw /= 2
            # basraw -= afraw
            # if i.contract_id.wage:
            #     c.setFont("Arimo-Bold", font_size)
            #     c.drawString( 40 , pos_inicial, u"BÁSICO")
            #     c.drawString( 170 , pos_inicial, u":")
            #     c.setFont("Arimo-Regular", font_size)
            #     c.drawRightString( 250 , pos_inicial, '{:,.2f}'.format(decimal.Decimal ("%0.2f" % basraw )) if basraw else '')
            #     pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
            # if hllc.a_familiar:
            #     c.setFont("Arimo-Bold", font_size)
            #     c.drawString( 40 , pos_inicial, u"ASIG. FAMILIAR")
            #     c.drawString( 170 , pos_inicial, u":")
            #     c.setFont("Arimo-Regular", font_size)
            #     # hp = self.env['hr.parameters'].search([('num_tipo','=',10001)])
            #     c.drawRightString( 250 , pos_inicial, '{:,.2f}'.format(decimal.Decimal ("%0.2f" %  hllc.a_familiar )) if  hllc.a_familiar else '')
            #     pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
            # if i.nocturnal_surcharge_mean:
            #     c.setFont("Arimo-Bold", font_size)
            #     c.drawString( 40 , pos_inicial, u"PROM. SOBRETAZA NOCTURNA")
            #     c.drawString( 170 , pos_inicial, u":")
            #     c.setFont("Arimo-Regular", font_size)
            #     c.drawRightString( 250 , pos_inicial, '{:,.2f}'.format(decimal.Decimal ("%0.2f" % i.nocturnal_surcharge_mean )) if i.nocturnal_surcharge_mean else '')
            #     pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
            # if i.sixth_gratification:
            #     c.setFont("Arimo-Bold", font_size)
            #     c.drawString( 40 , pos_inicial, u"1/6 ULTIMA GRATIF.")
            #     c.drawString( 170 , pos_inicial, u":")
            #     c.setFont("Arimo-Regular", font_size)
            #     c.drawRightString( 250 , pos_inicial, '{:,.2f}'.format(decimal.Decimal ("%0.2f" % i.sixth_gratification )) if i.sixth_gratification else '')
            #     pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
            # pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)



            c.setFont("Arimo-Bold", font_size)
            c.drawString( 30 , pos_inicial, u"1. COMPENSACIÓN POR TIEMPO DE SERVICIOS")
            pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
            c.setFont("Arimo-Bold", font_size)
            fi = i.fecha_computable.split('-') if i.fecha_computable else ''
            fc = i.fecha_cese.split('-') if i.fecha_cese else ''
            str_fi = (self.env['planilla.helpers'].date_to_month(int(fi[1]))+" "+fi[0]) if i.fecha_computable else '_'*8
            str_fc = (self.env['planilla.helpers'].date_to_month(int(fc[1]))+" "+fc[0]) if i.fecha_cese else '_'*8
            c.drawString( 30 , pos_inicial, u"(Periodo "+str_fi+" A "+str_fc+")")
            pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
            if hllc.cts_a_pagar:
                c.setFont("Arimo-Bold", font_size)
                c.drawString( 40 , pos_inicial, u"CTS")
                c.drawString( 170 , pos_inicial, u":")
                c.setFont("Arimo-Regular", font_size)
                c.drawRightString( 250 , pos_inicial, '{:,.2f}'.format(decimal.Decimal ("%0.2f" % hllc.cts_a_pagar )) if hllc.cts_a_pagar else "0.00")
                pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)

                c.setFont("Arimo-Bold", font_size)
                c.drawString( 40 , pos_inicial, u"Tiempo")
                c.drawString( 170 , pos_inicial, u":")
                tiempo_cts = ""
                if hllc.meses:
                    tiempo_cts += str(int(hllc.meses)) + u" Mes(es) "
                if hllc.dias:
                    tiempo_cts += str(int(hllc.dias)) + u" Día(s) "
                c.setFont("Arimo-Regular", font_size)
                c.drawString( 200 , pos_inicial, tiempo_cts)
            pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
            if False:
                c.setFont("Arimo-Bold", font_size)
                c.drawString( 40 , pos_inicial, u"Inters. CTS")
                c.drawString( 170 , pos_inicial, u":")
                c.setFont("Arimo-Regular", font_size)
                c.drawRightString( 250 , pos_inicial, '{:,.2f}'.format(decimal.Decimal ("%0.2f" % 0 )) )
                pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
            pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)

            c.setFont("Arimo-Bold", font_size)
            c.drawString( 30 , pos_inicial, u"2. VACACIONES")
            pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
            c.setFont("Arimo-Bold", font_size)
            fi = i.fecha_computable.split('-') if i.fecha_computable else ''
            fc = i.fecha_cese.split('-') if i.fecha_cese else ''
            str_fi = (self.env['planilla.helpers'].date_to_month(int(fi[1]))+" "+fi[0]) if i.fecha_computable else '_'*8
            str_fc = (self.env['planilla.helpers'].date_to_month(int(fc[1]))+" "+fc[0]) if i.fecha_cese else '_'*8
            c.drawString( 30 , pos_inicial, u"(Periodo "+str_fi+" A "+str_fc+")")
            pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)

            if i.vacaciones_truncas:
                c.setFont("Arimo-Bold", font_size)
                c.drawString( 40 , pos_inicial, u"Vacaciones Truncas")
                c.drawString( 170 , pos_inicial, u":")
                c.setFont("Arimo-Regular", font_size)
                c.drawRightString( 250 , pos_inicial, '{:,.2f}'.format(decimal.Decimal ("%0.2f" % i.vacaciones_truncas )) if i.vacaciones_truncas else "0.00" )
                pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
            # if i.fall_due_holidays:
            #     c.setFont("Arimo-Bold", font_size)
            #     c.drawString( 40 , pos_inicial, u"Remuneración Vacacional")
            #     c.drawString( 170 , pos_inicial, u":")
            #     c.setFont("Arimo-Regular", font_size)
            #     c.drawRightString( 250 , pos_inicial, '{:,.2f}'.format(decimal.Decimal ("%0.2f" % i.fall_due_holidays )) if i.fall_due_holidays else "0.00")
            #     pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
            # if i.compensation:
            #     c.setFont("Arimo-Bold", font_size)
            #     c.drawString( 40 , pos_inicial, u"Vacaciones Indem.")
            #     c.drawString( 170 , pos_inicial, u":")
            #     c.setFont("Arimo-Regular", font_size)
            #     c.drawRightString( 250 , pos_inicial, '{:,.2f}'.format(decimal.Decimal ("%0.2f" % i.compensation )) if i.compensation else "0.00")
            #     pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
                c.setFont("Arimo-Bold", font_size)
                c.drawString( 40 , pos_inicial, u"Tiempo")
                c.drawString( 170 , pos_inicial, u":")
                tiempo_vac = ""
                if i.meses:
                    tiempo_vac += str(int(i.meses)) + u" Mes(es) "
                if i.dias:
                    tiempo_vac += str(int(i.dias)) + u" Día(s) "
                c.setFont("Arimo-Regular", font_size)
                c.drawString( 200 , pos_inicial, tiempo_vac)
                pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
            pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)

            c.setFont("Arimo-Bold", font_size)
            c.drawString( 30 , pos_inicial, u"3. GRATIFICACIONES")
            pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
            c.setFont("Arimo-Bold", font_size)
            fi = hllg.fecha_computable.split('-') if hllg.fecha_computable else ''
            fc = hllg.fecha_cese.split('-') if hllg.fecha_cese else ''
            str_fi = (self.env['planilla.helpers'].date_to_month(int(fi[1]))+" "+fi[0]) if hllg.fecha_computable else '_'*8
            str_fc = (self.env['planilla.helpers'].date_to_month(int(fc[1]))+" "+fc[0]) if hllg.fecha_cese else '_'*8
            c.drawString( 30 , pos_inicial, u"(Periodo "+str_fi+" A "+str_fc+")")
            pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
            if hllg:
                c.setFont("Arimo-Bold", font_size)
                c.drawString( 40 , pos_inicial, u"Gratificación Trunca")
                c.drawString( 170 , pos_inicial, u":")
                c.setFont("Arimo-Regular", font_size)
                c.drawRightString( 250 , pos_inicial, '{:,.2f}'.format(decimal.Decimal ("%0.2f" % hllg.total_gratificacion )) if hllg.total_gratificacion else "0.00" )
                pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)

                c.setFont("Arimo-Bold", font_size)
                c.drawString( 40 , pos_inicial, u"BONIF EX.L. 30334")
                c.drawString( 170 , pos_inicial, u":")
                c.setFont("Arimo-Regular", font_size)
                c.drawRightString( 250 , pos_inicial, '{:,.2f}'.format(decimal.Decimal ("%0.2f" % hllg.plus_9 )) if hllg.plus_9 else "0.00" )
                pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)


                c.setFont("Arimo-Bold", font_size)
                c.drawString( 40 , pos_inicial, u"Tiempo")
                c.drawString( 170 , pos_inicial, u":")
                tiempo_grat = ""
                tiempo_grat += str(int(hllg.meses)) + u" Mes(es) "
                # tiempo_grat += str(int(hllg.dias)) + u" Día(s) "
                c.setFont("Arimo-Regular", font_size)
                c.drawString( 200 , pos_inicial,tiempo_grat)
                pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)


            pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)

            c.setFont("Arimo-Bold", font_size)
            c.drawString( 30 , pos_inicial, u"4. LIQUIDACIÓN")
            pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
            if hllc:
                c.setFont("Arimo-Bold", font_size)
                c.drawString( 40 , pos_inicial, u"CTS")
                c.drawString( 170 , pos_inicial, u":")
                c.setFont("Arimo-Regular", font_size)
                c.drawRightString( 250 , pos_inicial, '{:,.2f}'.format(decimal.Decimal ("%0.2f" % hllc.cts_a_pagar )) if hllc.cts_a_pagar  else "0.00")
                pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
            if i.vacaciones_truncas:
                c.setFont("Arimo-Bold", font_size)
                c.drawString( 40 , pos_inicial, u"Vacaciones Truncas")
                c.drawString( 170 , pos_inicial, u":")
                c.setFont("Arimo-Regular", font_size)
                c.drawRightString( 250 , pos_inicial, '{:,.2f}'.format(decimal.Decimal ("%0.2f" % i.vacaciones_truncas )) if i.vacaciones_truncas else "0.00" )
                pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
            if hllg.total_gratificacion:
                c.setFont("Arimo-Bold", font_size)
                c.drawString( 40 , pos_inicial, u"Gratificación Trunca")
                c.drawString( 170 , pos_inicial, u":")
                c.setFont("Arimo-Regular", font_size)
                c.drawRightString( 250 , pos_inicial, '{:,.2f}'.format(decimal.Decimal ("%0.2f" % hllg.total_gratificacion )) if hllg.total_gratificacion else "0.00" )
                pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)

            # hfcdl = self.env['hr.five.category.devolucion.lines'].search([('devolucion_id.period_id','=',self.period_id.id),('employee_id','=',hllg.employee_id.id)])
            # if len(hfcdl):
            # 	hfcdl = hfcdl[0]
            # 	if hfcdl.monto_devolver < 0:
            # 		c.setFont("Arimo-Bold", font_size)
            # 		c.drawString( 40 , pos_inicial, u"Devolucion Imp. Renta 5ta Categ.")
            # 		c.drawString( 170 , pos_inicial, u":")
            # 		c.setFont("Arimo-Regular", font_size)
            # 		c.drawRightString( 250 , pos_inicial, '{:,.2f}'.format(decimal.Decimal ("%0.2f" % (hfcdl.monto_devolver*-1) )))
            # 		pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
            # 	else:
            # 		c.setFont("Arimo-Bold", font_size)
            # 		c.drawString( 40 , pos_inicial, u"Retención Imp. Renta 5ta Categ.")
            # 		c.drawString( 170 , pos_inicial, u":")
            # 		c.setFont("Arimo-Regular", font_size)
            # 		c.drawRightString( 250 , pos_inicial, '{:,.2f}'.format(decimal.Decimal ("%0.2f" % (hfcdl.monto_devolver) )))
            # 		pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)

            # if (i.interes+hllg.interes+hllv.interes) > 0:
            #     c.setFont("Arimo-Bold", font_size)
            #     c.drawString( 40 , pos_inicial, u"Intereses Liquidación")
            #     c.drawString( 170 , pos_inicial, u":")
            #     c.setFont("Arimo-Regular", font_size)
            #     c.drawRightString( 250 , pos_inicial, '{:,.2f}'.format(decimal.Decimal ("%0.2f" % (i.interes+hllg.interes+hllv.interes) )))
            #     pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
            if hllg.plus_9:
                c.setFont("Arimo-Bold", font_size)
                c.drawString( 40 , pos_inicial, u"BONIF EX.L. 30334")
                c.drawString( 170 , pos_inicial, u":")
                c.setFont("Arimo-Regular", font_size)
                c.drawRightString( 250 , pos_inicial, '{:,.2f}'.format(decimal.Decimal ("%0.2f" % hllg.plus_9 )) if hllg.plus_9 else "0.00" )
                pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
            # if hllv.fall_due_holidays:
            #     c.setFont("Arimo-Bold", font_size)
            #     c.drawString( 40 , pos_inicial, u"Remuneración Vacacional")
            #     c.drawString( 170 , pos_inicial, u":")
            #     c.setFont("Arimo-Regular", font_size)
            #     c.drawRightString( 250 , pos_inicial, '{:,.2f}'.format(decimal.Decimal ("%0.2f" % hllv.fall_due_holidays )) if hllv.fall_due_holidays else "0.00")
            #     pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
            # if hllv.compensation:
            #     c.setFont("Arimo-Bold", font_size)
            #     c.drawString( 40 , pos_inicial, u"Vacaciones Indem")
            #     c.drawString( 170 , pos_inicial, u":")
            #     c.setFont("Arimo-Regular", font_size)
            #     c.drawRightString( 250 , pos_inicial, '{:,.2f}'.format(decimal.Decimal ("%0.2f" % hllv.compensation )) if hllv.compensation else "0.00")
            #     pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)			
            pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)


            c.setFont("Arimo-Bold", font_size)
            c.drawString( 30 , pos_inicial, u"OTROS INGRESOS")
            pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
            tot_ingresos = i.total_vacaciones + hllc.cts_a_pagar + hllg.total_gratificacion + hllg.plus_9 
            # for item in hllv.ingresos_lines:
            #     if item.monto:
            #         c.setFont("Arimo-Bold", font_size)
            #         c.drawString( 40 , pos_inicial, item.concepto_id.name)
            #         c.drawString( 170 , pos_inicial, u":")
            #         c.setFont("Arimo-Regular", font_size)
            #         c.drawRightString( 250 , pos_inicial, '{:,.2f}'.format(decimal.Decimal ("%0.2f" % item.monto )) )
            #         tot_ingresos += item.monto
            #         pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)

            pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
            c.setFont("Arimo-Bold", font_size)
            c.drawString( 40 , pos_inicial, u"Total Ingresos")
            c.setFont("Arimo-Bold", font_size)
            c.drawRightString( 330 , pos_inicial, '{:,.2f}'.format(decimal.Decimal ("%0.2f" % tot_ingresos )) if tot_ingresos else "0.00" )
            pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl*2,pagina)
            c.setFont("Arimo-Bold", font_size)
            c.drawString( 40 , pos_inicial, u"Aportes Trabajador")
            pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)

            if i.onp:
                c.setFont("Arimo-Bold", font_size)
                c.drawString( 40 , pos_inicial, u"ONP")
                c.drawString( 170 , pos_inicial, u":")
                c.setFont("Arimo-Regular", font_size)
                c.drawRightString( 250 , pos_inicial, '{:,.2f}'.format(decimal.Decimal ("%0.2f" % i.onp )) if i.onp else "0.00" )
                pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)

            if i.afp_jub or i.afp_si or i.afp_com:
                c.setFont("Arimo-Bold", font_size)
                c.drawString( 40 , pos_inicial, u"AFP. PENSIONES")
                c.drawString( 170 , pos_inicial, u":")
                c.setFont("Arimo-Regular", font_size)
                c.drawRightString( 250 , pos_inicial, '{:,.2f}'.format(decimal.Decimal ("%0.2f" % i.afp_jub )) if i.afp_jub else "0.00" )
                pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
                c.setFont("Arimo-Bold", font_size)
                c.drawString( 40 , pos_inicial, u"AFP. COM. PORC.")
                c.drawString( 170 , pos_inicial, u":")
                c.setFont("Arimo-Regular", font_size)
                c.drawRightString( 250 , pos_inicial, '{:,.2f}'.format(decimal.Decimal ("%0.2f" % i.afp_com )) if i.afp_com else "0.00" )
                pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
                c.setFont("Arimo-Bold", font_size)
                c.drawString( 40 , pos_inicial, u"AFP. SEGUROS")
                c.drawString( 170 , pos_inicial, u":")
                c.setFont("Arimo-Regular", font_size)
                c.drawRightString( 250 , pos_inicial, '{:,.2f}'.format(decimal.Decimal ("%0.2f" % i.afp_si )) if i.afp_si else "0.00" )
                pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
            # if i.afp_2p:
            #     c.setFont("Arimo-Bold", font_size)
            #     c.drawString( 40 , pos_inicial, u"AFP. 2%")
            #     c.drawString( 170 , pos_inicial, u":")
            #     c.setFont("Arimo-Regular", font_size)
            #     c.drawRightString( 250 , pos_inicial, '{:,.2f}'.format(decimal.Decimal ("%0.2f" % i.afp_2p )) if i.afp_2p else "0.00" )
            #     pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
            if i.afp_jub:
                c.setFont("Arimo-Bold", font_size)
                c.drawString( 40 , pos_inicial, u"FONDO DE JUBILACION")
                c.drawString( 170 , pos_inicial, u":")
                c.setFont("Arimo-Regular", font_size)
                c.drawRightString( 250 , pos_inicial, '{:,.2f}'.format(decimal.Decimal ("%0.2f" % i.afp_jub )) if i.afp_jub else "0.00" )
                pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
            tot_descuentos = i.onp + i.afp_jub + i.afp_si + i.afp_com + i.afp_jub
            pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
            c.setFont("Arimo-Bold", font_size)
            c.drawString( 30 , pos_inicial, u"OTROS DESCUENTOS")
            pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)

            # for item in i.descuentos_lines:
            #     if item.concepto_id.payroll_group != '4':
            #         if item.monto:
            #             c.setFont("Arimo-Bold", font_size)
            #             c.drawString( 40 , pos_inicial, item.concepto_id.name)
            #             c.drawString( 170 , pos_inicial, u":")
            #             c.setFont("Arimo-Regular", font_size)
            #             c.drawRightString( 250 , pos_inicial, '{:,.2f}'.format(decimal.Decimal ("%0.2f" % item.monto )) )
            #             tot_descuentos += item.monto
            #             pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
            pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)			
            c.setFont("Arimo-Bold", font_size)
            c.drawString( 40 , pos_inicial, u"Total Descuentos")
            c.setFont("Arimo-Bold", font_size)
            c.drawRightString( 330 , pos_inicial, '{:,.2f}'.format(decimal.Decimal ("%0.2f" % tot_descuentos )) if tot_descuentos else "0.00")
            pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)

            c.setFont("Arimo-Bold", font_size)
            c.drawString( 40 , pos_inicial, u"Total a Pagar")
            c.setFont("Arimo-Bold", font_size)
            c.drawRightString( 330 , pos_inicial, '{:,.2f}'.format(decimal.Decimal ("%0.2f" % (tot_ingresos - tot_descuentos) )) if (tot_ingresos - tot_descuentos) else "0.00")
            pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl*2,pagina)

            c.setFont("Arimo-Bold", font_size)
            c.drawString( 30 , pos_inicial, u"Neto a Pagar al Trabajador")
            pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
            c.setFont("Arimo-Regular", font_size)
            c.drawString( 40 , pos_inicial, u"SON")
            c.setFont("Arimo-Bold", font_size)
            tot_tot = '{:,.2f}'.format(decimal.Decimal ("%0.2f" % (tot_ingresos - tot_descuentos) ))
            c.drawString( 55 , pos_inicial, str(float(tot_tot.replace(',',''))).capitalize() + " soles")
            pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl*3,pagina)

            c.setFont("Arimo-Regular", font_size)
            # isd = i.issue_date.split('-' ) if i.issue_date else ''
            isd = i.contract_id.date_end.split('-') if i.contract_id.date_end else ''
            c.drawString( 300 , pos_inicial, ("Arequipa " + isd[2] + " de "+self.env['planilla.helpers'].date_to_month(int(isd[1]))+" del "+isd[0]) if i.contract_id.date_end else '_'*28)
            pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)			
            txt = u"Dpto. de personal"
            c.drawCentredString( 100 , pos_inicial, u"_"*len(txt)*2)
            pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
            c.drawCentredString( 100 , pos_inicial, txt)
            pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
            c.drawCentredString( 100 , pos_inicial, company.name)
            pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl*2,pagina)

            c.setFont("Arimo-Bold", font_size)
            c.drawString( 30 , pos_inicial, u"CONSTANCIA DE RECEPCIÓN")
            pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl*4,pagina)

            style = getSampleStyleSheet()["Normal"]
            style.leading = 12
            style.alignment = 4

            paragraph1 = Paragraph(
                "<font size=6>" + u"Declaro estar conforme con la presente liquidación, haber recibido el importe de la misma así como el importe correspondiente a todas y cada una de  mis remuneraciones y beneficios no teniendo que reclamar en el futuro, quedando asi concluida la relación laboral. </font>",
                style
            )

            data= [[ paragraph1 ]]
            t=Table(data,colWidths=(515), rowHeights=(40))
            t.setStyle(TableStyle([
            ('TEXTFONT', (0, 0), (-1, -1), 'Arimo-Regular'),
            ('FONTSIZE',(0,0),(-1,-1),font_size)
            ]))
            t.wrapOn(c,40,pos_inicial)
            t.drawOn(c,40,pos_inicial)
            pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl*3,pagina)

            c.setFont("Arimo-Regular", font_size)		
            txt = i.contract_id.employee_id.name_related
            c.drawCentredString( 250 , pos_inicial, u"_"*len(txt)*2)
            pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
            c.drawCentredString( 250 , pos_inicial, txt)
            pagina, pos_inicial = self.verify_linea(c,wReal,hReal,pos_inicial,endl,pagina)
            c.drawCentredString( 250 , pos_inicial, i.contract_id.employee_id.identification_id if i.contract_id.employee_id.identification_id else '')

            pagina += 1
            c.showPage()
            inicio = 0
            pos_inicial = hReal-100
            pagina = 1
            textPos = 0
        c.save()

    @api.multi
    @api.depends('year', 'month')
    @api.onchange('year', 'month')
    def change_dates(self):
		if(self.year is not False and self.month is not False):
			self.ensure_one()
			self.date_start = date(int(self.year), self.month, 1)
			self.date_end = date(int(self.year), self.month,
								 calendar.monthrange(int(self.year), self.month)[1])

    @api.multi
    def write(self, vals):
        if vals and ("year" in vals or "month" in vals):
            vals['date_start'] = date(int(self.year), self.month, 1)
            vals['date_end'] = date(int(self.year), self.month, calendar.monthrange(
                int(self.year), self.month)[1])

        return super(PlanillaLiquidacion, self).write(vals)

    @api.model
    def create(self, vals):
        if len(self.search([('year', '=', vals['year']), ('month', '=', vals['month'])])) >= 1:
            raise UserError(
                "Ya existe un registros %s" % (vals['year']))
        else:
            vals['date_start'] = date(int(vals['year']), int(vals['month']) , 1)
            vals['date_end'] = date(int(vals['year']), int(vals['month']) , calendar.monthrange(
                int(vals['year']), int(vals['month']) )[1])
            return super(PlanillaLiquidacion, self).create(vals)


    def get_excel(self):
        # -------------------------------------------Datos---------------------------------------------------
        reload(sys)
        sys.setdefaultencoding('iso-8859-1')
        output = io.BytesIO()

        # direccion = self.env['main.parameter'].search([])[0].dir_create_file
        workbook = Workbook('Liquidacion%s-%s.xlsx' % (self.year, self.month))
        worksheet = workbook.add_worksheet(
            'gratificacion%s-%s.xlsx' % (self.year, self.month))
        worksheet.set_tab_color('red')

        lines = self.planilla_gratificacion_lines
        self.env['planilla.gratificacion'].getSheetGratificacion(workbook,worksheet,lines)
        
        lines = self.planilla_cts_lines
        worksheet = workbook.add_worksheet(
            'CTS%s-%s.xlsx' % (self.year, self.month))
        worksheet.set_tab_color('green')
        self.env['planilla.cts'].getCTSSheet(workbook,worksheet,lines)
            
        lines = self.planilla_vacaciones_lines
        worksheet = workbook.add_worksheet(
            'Vacaciones%s-%s.xlsx' % (self.year, self.month))
        worksheet.set_tab_color('blue')
        self.getLiquidacionSheet(workbook,worksheet,lines)


            
        workbook.close()

        f = open('Liquidacion%s-%s.xlsx' % (self.year, self.month), 'rb')

        vals = {
            'output_name': 'Liquidacion%s-%s.xlsx' % (self.year, self.month),
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
    def getLiquidacionSheet(self,workbook,worksheet,lines):

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
            {'num_format': '#,##0.00', 'font_name': 'Arial', 'align': 'right'})
        formatLeft = workbook.add_format(
            {'num_format': '#,##0.00', 'font_name': 'Arial', 'align': 'left', 'font_size': fontSize})
        formatLeftColor = workbook.add_format(
            {'bold': True, 'num_format': '#,##0.00', 'font_name': 'Arial', 'align': 'left', 'bg_color': '#99CCFF', 'font_size': fontSize})
        styleFooterSum = workbook.add_format(
            {'bold': True, 'num_format': '#,##0.00', 'font_name': 'Arial', 'align': 'right', 'font_size': fontSize, 'top': 1, 'bottom': 2})
        styleFooterSum.set_bottom(6)
        numberdos.set_font_size(fontSize)
        bord = workbook.add_format()
        bord.set_border(style=1)
        bord.set_text_wrap()
        # numberdos.set_border(style=1)
        formatMoneyWithBorder = workbook.add_format(
            {'valign': 'vcenter', 'align': 'right', 'border': 1, 'num_format': '#,##0.00'})

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
            x, 1,dict(self._fields['month'].selection).get(self.month))

        x = x+3

        columnas = ["Orden",
                    "Nro Documento",
                    "Apellido\nPaterno",
                    "Apellido\nMaterno",
                    "Nombres",
                    "Fecha\nComputo",
                    "Fecha\nCese",
                    "Faltas",
                    "Basico",
                    u"Prom Bonificación",
                    u"Prom Comision",
                    "PROM. HRS\n EXTRAS",
                    "Rem\nCom",
                    'Meses',
                    'Dias',
                    'Monto\npor mes',
                    'Monto\npor dia',
                    "Vacaciones\nDevengadas",
                    "Vacaciones\nTruncas",
                    "Total\nVacaciones",
                    "ONP",
                    "AFP\nJUB",
                    "AFP\nSI",
                    "AFP\nCOM",
                    u"Neto\nTotal"]
        # fil = 4
        worksheet.write(
            x, 0,columnas[0], formatLeftColor)
        for i in range(1, len(columnas)):
            worksheet.write(x, i, columnas[i], boldbord)

        worksheet.set_row(x, 50)

        x = x+1

        filtro = []

        # query = 'select %s from planilla_tabular' % (','.join(fields))
        query = """
        select  id,
        identification_number,
        last_name_father ,
        last_name_mother ,
        names ,
        fecha_computable ,
        fecha_cese   ,        
        faltas        ,    
        basico         ,    
        comision        ,     
        bonificacion     ,       
        horas_extras_mean ,            
        remuneracion_computable,        
        meses           ,
        dias           ,
        monto_x_mes     ,    
        monto_x_dia      ,    
        vacaciones_devengadas        ,     
        vacaciones_truncas            ,
        total_vacaciones            ,
        onp   ,
        afp_jub,       
        afp_si  ,    
        afp_com  ,     
        neto_total              
        from planilla_liquidacion_vacaciones_line where planilla_liquidacion_id =%d
        
        """%(self.id)
        print query
        self.env.cr.execute(query)
        datos_planilla = self.env.cr.fetchall()
        range_row = len(datos_planilla[0] if len(datos_planilla) > 0 else 0)
        print datos_planilla
        x_ini=x
        for i in range(len(datos_planilla)):
            for j in range(range_row):
                if j == 0 or j == 1:
                    if self.is_number_tryexcept(datos_planilla[i][j]):
                        worksheet.write_number(
                            x, j, float(datos_planilla[i][j]) if datos_planilla[i][j] else 0.00, formatLeft)
                    else:
                        worksheet.write(
                            x, j, datos_planilla[i][j] if datos_planilla[i][j] else '0.00', formatLeft)
                else:
                    if self.is_number_tryexcept(datos_planilla[i][j]):
                        worksheet.write_number(
                            x, j, float(datos_planilla[i][j]) if datos_planilla[i][j] else 0.00, numberdos)
                    else:
                        worksheet.write(
                            x, j, datos_planilla[i][j] if datos_planilla[i][j] else '5.00', numberdos)
            x = x+1
        x = x + 1

        j=7
        tmp_i=0
        for i in range(7,len(datos_planilla[0])):
            worksheet.write(x, j, '=SUM(%s%d:%s%d)' %(chr(ord('H')+tmp_i), x_ini+1, chr(ord('H')+tmp_i) , x), styleFooterSum)
            j+=1
            tmp_i+=1

        helper_liquidacion = self.env['planilla.helpers']
        # seteando tamaño de columnas
        col_widths =helper_liquidacion.get_col_widths(datos_planilla)
        worksheet.set_column(0, 0, col_widths[0]-10)
        worksheet.set_column(1, 1, col_widths[1]-7)
        for i in range(2, len(col_widths)):
            worksheet.set_column(i, i, col_widths[i])


    @api.multi
    def calcular_liquidacion(self):
        self.planilla_gratificacion_lines.unlink()
        self.planilla_cts_lines.unlink()
        self.planilla_vacaciones_lines.unlink()

        mes_periodo = self.month
        days = calendar.monthrange(int(self.year), mes_periodo)[1]
        date_start_liquidacion = date(int(self.year), mes_periodo, 1)
        date_end_liquidacion = date(int(self.year), mes_periodo, days)

        date_start_liquidacion_cts = date(int(self.year), mes_periodo, 1)
        date_end_liquidacion_cts = date(int(self.year), mes_periodo, days)

        date_start_liquidacion_vacaciones = date(
            int(self.year), mes_periodo, 1)
        date_end_liquidacion_vacaciones = date(
            int(self.year), mes_periodo, days)

        if mes_periodo >= 1 and mes_periodo <= 6:
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
            rango_inicio_contrato = date(int(self.year), 12, 1)
            # rango_fin_contrato = date(int(self.year), 12, 31) #30 nov
            rango_fin_contrato = date(int(self.year), 11, 30)  # 30 nov
            rango_inicio_planilla = date(int(self.year), 7, 1)
            # rango_fin_planilla = date(int(self.year), 12, 31)
            rango_fin_planilla = date(int(self.year), 11, 30)

        if mes_periodo >= 5 and mes_periodo <= 10:  # mayo a octubre
            # el rango fin deberia ser 31 del mes 10
            # pero para asegurarme que al menos haya
            # un mes para que se le pague la cts
            # le aumentare la fecha final(para control resumen_periodo) que sea mayor a 31 del mes 10
            # ya que si es menor a esa fecha o bien seso y bien sesara el mes 7
            # por lo que le corresponderia no cts sino liquidacion
            #
            # para el rango de inicio para asegurarme de que tenga al menos un mes
            # el rango de inicio de resumen_periodo deberia ser como minimo menor o igual a el 1 del mes 10

            rango_inicio_planilla_cts = date(int(self.year), 5, 1)
            rango_fin_planilla_cts = date(int(self.year), 10, 31)
            # se usa para sacar los dia del periodo anterior
            anho_periodo_anterior_cts = int(self.year)-1
            tipo_cts = '12'

        elif mes_periodo >= 1 and mes_periodo <= 4:  # enero a abril

            rango_inicio_planilla_cts = date(int(self.year)-1, 11, 1)
            rango_fin_planilla_cts = date(int(self.year), 4, 30)
            # se usa para sacar los dia del periodo anterior
            anho_periodo_anterior_cts = int(self.year)-1
            tipo_cts = '12'
        else:  # solo queda noviembre y diciembre
            rango_inicio_planilla_cts = date(int(self.year), 11, 1)
            rango_fin_planilla_cts = date(int(self.year)+1, 4, 30)
            # se usa para sacar los dia del periodo anterior
            anho_periodo_anterior_cts = int(self.year)
            tipo_cts = '07'

        parametros_eps = self.env['planilla.parametros.essalud.eps'].get_parametros_essalud_eps(
        )

        contratos_empleado = self.env['hr.contract'].search(
            [('date_end', '>=', date_start_liquidacion_vacaciones), ('date_end', '<=', date_end_liquidacion_vacaciones), ('state', '!=', 'close')])

        for contrato in contratos_empleado:
            # 1 busco los contratos de ese empleado
            contratos_empleado = self.env['hr.contract'].search(
                [('employee_id', '=', contrato.employee_id.id), ('date_end', '<=', contrato.date_end)], order='date_end desc')
            # datetime
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

            self.calcular_gratificacion(contrato, rango_inicio_planilla, rango_fin_planilla,
                                        fecha_ini, fecha_fin_contrato, parametros_eps, date_start_liquidacion, date_end_liquidacion)
            self.calcular_cts(contrato, rango_inicio_planilla_cts, rango_fin_planilla_cts,
                              fecha_ini, fecha_fin_contrato, date_start_liquidacion, date_end_liquidacion, anho_periodo_anterior_cts, tipo_cts)
            self.calcular_vacaciones(
                contrato, date_start_liquidacion_vacaciones, date_end_liquidacion_vacaciones, fecha_ini, fecha_fin_contrato)

    @api.multi
    def calcular_gratificacion(self, contrato, rango_inicio_planilla, rango_fin_planilla, fecha_ini, fecha_fin, parametros_eps, date_start_liquidacion, date_end_liquidacion):
        self.ensure_one()
        ultimo_mes_no_cuenta = False
        helper_liquidacion = self.env['planilla.helpers']
        parametros_gratificacion = self.env['planilla.gratificacion'].get_parametros_gratificacion()    
        if fecha_ini < rango_inicio_planilla:
            fecha_computable = rango_inicio_planilla
        else:
            fecha_computable = fecha_ini

        dias_mes_cese = calendar.monthrange(
            int(self.year), fecha_fin.month)[1]

        meses = helper_liquidacion.diferencia_meses_gratificacion(
            fecha_computable, fecha_fin)


        # 4 sacando basico afam y faltas
        if fecha_fin.month-fecha_computable.month == 0:
            # solo esta un mes o menos, no hay nomina anterior
            basico = contrato.wage
            faltas = 0.0
            afam = 0.0
            comisiones_periodo = 0.0
            promedio_bonificaciones = 0.0
            promedio_horas_trabajo_extra = 0.0
            # fecha_computable = date(fecha_fin.year, fecha_ini.month, fecha_ini.day)
        else:
            fecha_inicio_nominas = date(
                fecha_computable.year, fecha_computable.month, 1)
            fecha_fin_nominas = date(fecha_fin.year, fecha_fin.month, calendar.monthrange(
                fecha_fin.year, fecha_fin.month)[1])
            fecha_fin_nominas = fecha_fin - relativedelta(months=+1)
            fecha_fin_nominas = date(fecha_fin_nominas.year, fecha_fin_nominas.month, calendar.monthrange(
                fecha_fin_nominas.year, fecha_fin_nominas.month)[1])

            conceptos = self.env['hr.payslip'].search([('date_from', '>=', fecha_inicio_nominas), (
                'date_to', '<=', fecha_fin_nominas), ('employee_id', '=', contrato.employee_id.id)], order='date_to desc')

            verificar_meses, _ = helper_liquidacion.diferencia_meses_dias(
                fecha_inicio_nominas, fecha_fin_nominas)

            if len(conceptos) != verificar_meses:
                fecha_encontradas = ' '.join(
                    ['\t-'+x.name+'\n' for x in conceptos])
                if not fecha_encontradas:
                    fecha_encontradas = '"No tiene nominas"'
                raise UserError(
                    'Error en GRATIFICACION: El empleado %s debe tener nominas desde:\n %s hasta %s pero solo tiene nominas en las siguientes fechas:\n %s \nfaltan %d nominas, subsanelas por favor ' % (
                        contrato.employee_id.name_related, fecha_inicio_nominas, fecha_fin_nominas, fecha_encontradas, abs(len(
                            conceptos) - (verificar_meses))
                    ))

            basico = helper_liquidacion.getBasicoByDate(date(fecha_fin_nominas.year,fecha_fin_nominas.month,1),fecha_fin_nominas,contrato.employee_id.id,parametros_gratificacion.cod_basico.code )  # conceptos[0].basico if conceptos else 0.0
            faltas = helper_liquidacion.getSumFaltas(date(fecha_fin_nominas.year,fecha_fin_nominas.month,1),fecha_fin_nominas,contrato.employee_id.id,parametros_gratificacion.cod_dias_faltas.codigo ) #sum([x.dias_faltas for x in conceptos])
            afam = helper_liquidacion.getAsignacionFamiliarByDate(fecha_inicio_nominas,fecha_fin_nominas,contrato.employee_id.id,parametros_gratificacion.cod_asignacion_familiar.code )  #conceptos[0].asignacion_familiar if conceptos else 0.0

            comisiones_periodo, promedio_bonificaciones, promedio_horas_trabajo_extra = helper_liquidacion.calcula_comision_gratificacion_hrs_extras(
                contrato, fecha_computable, fecha_fin_nominas, meses, fecha_fin)

        bonificacion_9 = 0
        bonificacion = promedio_bonificaciones
        comision = comisiones_periodo
        dias = 0

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
        if  contrato.employee_id.tipo_empresa=='microempresa':
            total_gratificacion=0
        elif contrato.employee_id.tipo_empresa=='pequenhaempresa':
            total_gratificacion/=2.0

        if self.plus_9:
            if contrato.tipo_seguro == 'essalud':
                bonificacion_9 = parametros_eps.ratio_essalud / \
                    100.0*float(total_gratificacion)
            else:
                bonificacion_9 = parametros_eps.ratio_eps / \
                    100.0*float(total_gratificacion)

        vals = {
            'planilla_liquidacion_id': self.id,
            'employee_id': contrato.employee_id,
            'identification_number': contrato.employee_id.identification_id,
            'last_name_father': contrato.employee_id.a_paterno,
            'last_name_mother': contrato.employee_id.a_materno,
            'names': contrato.employee_id.name_related,
            'fecha_ingreso': fecha_ini,
            'fecha_computable': fecha_computable,
            'fecha_cese': fecha_fin,
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
        print "liquidacion final para ", contrato.employee_id.name_related
        print vals

        self.planilla_gratificacion_lines.create(vals)
        return True

    @api.multi
    def calcular_cts(self, contrato, rango_inicio_planilla, rango_fin_planilla, fecha_ini, fecha_fin, date_start_liquidacion, date_end_liquidacion, anho_periodo_anterior_cts, tipo_cts):
        self.ensure_one()
        ultimo_mes_no_cuenta = False
        helper_liquidacion = self.env['planilla.helpers']
        parametros_gratificacion = self.env['planilla.gratificacion'].get_parametros_gratificacion()

        # el resto se queda
        dias = 0
        dias_mes_cese = calendar.monthrange(
            int(fecha_fin.month), fecha_fin.month)[1]
        meses = 0
        if rango_inicio_planilla <= fecha_ini and rango_fin_planilla >= fecha_ini:
            fecha_computable = fecha_ini
        else:
            fecha_computable = rango_inicio_planilla

        meses, dias = helper_liquidacion.diferencia_meses_dias(
            fecha_computable, fecha_fin)

        meses, dias = helper_liquidacion.diferencia_meses_dias(
            fecha_computable, fecha_fin)

        # 4 sacando basico afam y faltas
        if fecha_fin.month-fecha_computable.month == 0:
            # solo esta un mes o menos, no hay nomina anterior
            basico = contrato.wage
            faltas = 0.0
            afam = 0.0
            comisiones_periodo = 0.0
            promedio_bonificaciones = 0.0
            promedio_horas_trabajo_extra = 0.0
            # fecha_computable = date(fecha_fin.year, fecha_ini.month, fecha_ini.day)
            gratificacion = 0.0
        else:

            fecha_inicio_nominas = date(
                fecha_computable.year, fecha_computable.month, 1)
            fecha_fin_nominas = fecha_fin - relativedelta(months=+1)
            fecha_fin_nominas = date(fecha_fin_nominas.year, fecha_fin_nominas.month, calendar.monthrange(
                fecha_fin_nominas.year, fecha_fin_nominas.month)[1])

            conceptos = self.env['hr.payslip'].search([('date_from', '>=', fecha_inicio_nominas), (
                'date_to', '<=', fecha_fin_nominas), ('employee_id', '=', contrato.employee_id.id)], order='date_to desc')

            fecha_encontradas = ' '.join(
                ['\t-'+x.name+'\n' for x in conceptos])
            # meses-1#meses-1 if ultimo_mes_no_cuenta else meses
            verificar_meses, _ = helper_liquidacion.diferencia_meses_dias(
                fecha_inicio_nominas, fecha_fin_nominas)

            if len(conceptos) != verificar_meses:
                fecha_encontradas = ' '.join(
                    ['\t-'+x.name+'\n' for x in conceptos])
                if not fecha_encontradas:
                    fecha_encontradas = '"No tiene nominas"'
                raise UserError(
                    'Error en CTS: El empleado %s debe tener nominas desde:\n %s hasta %s pero solo tiene nominas en las siguientes fechas:\n %s \nfaltan %d nominas, subsanelas por favor ' % (
                        contrato.employee_id.name_related, fecha_inicio_nominas, fecha_fin_nominas, fecha_encontradas, abs(len(
                            conceptos) - (verificar_meses))
                    ))

            basico = helper_liquidacion.getBasicoByDate(date(fecha_fin_nominas.year,fecha_fin_nominas.month,1),fecha_fin_nominas,contrato.employee_id.id,parametros_gratificacion.cod_basico.code )  # conceptos[0].basico if conceptos else 0.0
            faltas = helper_liquidacion.getSumFaltas(date(fecha_fin_nominas.year,fecha_fin_nominas.month,1),fecha_fin_nominas,contrato.employee_id.id,parametros_gratificacion.cod_dias_faltas.codigo ) #sum([x.dias_faltas for x in conceptos])
            afam = helper_liquidacion.getAsignacionFamiliarByDate(fecha_inicio_nominas,fecha_fin_nominas,contrato.employee_id.id,parametros_gratificacion.cod_asignacion_familiar.code )  #conceptos[0].asignacion_familiar if conceptos else 0.0


            query_gratificacion = """
            select total_gratificacion/6.0 as gratificacion from planilla_gratificacion pg 
            inner join planilla_gratificacion_line pgl 
            on pgl.planilla_gratificacion_id= pg.id 
            where employee_id =%d and year='%s' and tipo='%s' 
            """ % (contrato.employee_id, anho_periodo_anterior_cts, tipo_cts)

            self.env.cr.execute(query_gratificacion)
            gratificacion = self.env.cr.dictfetchone()
            gratificacion = gratificacion['gratificacion'] if gratificacion else 0.0

            query_dias_pasados = """
            select dias_proxima_fecha as dias_cts_periodo_anterior from planilla_cts pc 
            inner join planilla_cts_line pcl 
            on pc.id= pcl.planilla_cts_id
            where employee_id=%d    and year='%s' and tipo='%s'
            """ % (contrato.employee_id, anho_periodo_anterior_cts, tipo_cts)

            self.env.cr.execute(query_dias_pasados)
            dias_cts_periodo_anterior = self.env.cr.dictfetchone()
            dias_cts_periodo_anterior = dias_cts_periodo_anterior[
                'dias_cts_periodo_anterior'] if dias_cts_periodo_anterior else 0
            dias = dias+dias_cts_periodo_anterior

            helper_liquidacion = self.env['planilla.helpers']
            comisiones_periodo, promedio_bonificaciones, promedio_horas_trabajo_extra = helper_liquidacion.calcula_comision_gratificacion_hrs_extras(
                contrato, fecha_computable, fecha_fin_nominas, meses, fecha_fin)

        bonificacion = promedio_bonificaciones
        comision = comisiones_periodo

        rem_computable = basico+afam + \
            gratificacion + bonificacion + \
            comision + promedio_horas_trabajo_extra

        monto_x_mes = round(rem_computable/12.0, 2)
        monto_x_dia = round(monto_x_mes/30.0, 2)
        monto_x_meses = round(monto_x_mes*meses, 2)
        monto_x_dias = round(monto_x_dia*dias, 2)
        total_faltas = round(monto_x_dia*faltas, 2)

        cts_soles = monto_x_dias+monto_x_meses-total_faltas
        cts_interes = 0.0
        otros_dtos = 0.0
        cts_a_pagar = (cts_soles+cts_interes)-otros_dtos

        if  contrato.employee_id.tipo_empresa=='microempresa':
            cts_a_pagar=0
        elif contrato.employee_id.tipo_empresa=='pequenhaempresa':
            cts_a_pagar/=2.0

        tipo_cambio_venta = self.tipo_cambio
        cts_dolares = round(cts_a_pagar*tipo_cambio_venta, 2)
        cuenta_cts = 0.0
        banco = 0.0

        vals = {
            'planilla_liquidacion_id': self.id,
            'employee_id': contrato.employee_id,
            'contract_id': contrato.id,
            'identification_number': contrato.employee_id.identification_id,
            'last_name_father': contrato.employee_id.a_paterno,
            'last_name_mother': contrato.employee_id.a_materno,
            'names': contrato.employee_id.name_related,
            'fecha_ingreso': fecha_ini,
            'fecha_computable': fecha_computable,
            'fecha_cese': fecha_fin,
            'basico': basico,
            'a_familiar': afam,
            'gratificacion': gratificacion,
            'horas_extras_mean': promedio_horas_trabajo_extra,
            'bonificacion': bonificacion,
            'comision': comisiones_periodo,
            'base': rem_computable,
            'monto_x_mes': monto_x_mes,
            'monto_x_dia': monto_x_dia,
            'faltas': faltas,
            'meses': meses,
            'dias': dias,
            'monto_x_meses': monto_x_meses,
            'monto_x_dias':  monto_x_dias,
            'total_faltas':  total_faltas,
            'cts_soles': cts_soles,
            'intereses_cts': cts_interes,
            'otros_dtos': otros_dtos,
            'cts_a_pagar': cts_a_pagar,
            'tipo_cambio_venta': tipo_cambio_venta,
            'cts_dolares': cts_dolares,
            'cta_cts': cuenta_cts,
            'banco': banco
        }

        self.planilla_cts_lines.create(vals)
        return True

    @api.multi
    def calcular_vacaciones(self, contrato, date_start_liquidacion, date_end_liquidacion, fecha_ini, fecha_fin):
        self.ensure_one()
        helper_liquidacion = self.env['planilla.helpers']
        parametros_gratificacion = self.env['planilla.gratificacion'].get_parametros_gratificacion()
        fecha_ini = date(int(self.year), fecha_ini.month, fecha_ini.day)
        fecha_computable = fecha_fin - relativedelta(months=+6)

        dias = 0
        dias_mes_cese = calendar.monthrange(
            int(fecha_fin.month), fecha_fin.month)[1]
        if fecha_computable < fecha_ini:
            fecha_computable = fecha_ini
        dias_del_mes_fin = calendar.monthrange(
            int(self.year), fecha_fin.month)[1]


        meses, _ = helper_liquidacion.diferencia_meses_dias(
            fecha_ini, fecha_fin)

        mes_tmp = date(fecha_fin.year, fecha_fin.month, fecha_ini.day)
        if mes_tmp > fecha_fin:
            dias = abs(mes_tmp-fecha_fin)+timedelta(days=1)
            dias = 31-dias.days
        else:
            if fecha_fin.day == dias_mes_cese and fecha_ini.day == 1:
                dias = 0
                meses += 1
            else:
                dias = abs(fecha_ini.day-fecha_fin.day)+1

        meses, dias = helper_liquidacion.diferencia_meses_dias(
            fecha_ini, fecha_fin)

        # 4 sacando basico afam y faltas
        if fecha_fin.month-fecha_ini.month == 0:
            # solo esta un mes o menos, no hay nomina anterior
            basico = contrato.wage
            faltas = 0.0
            afam = 0.0
            comisiones_periodo = 0.0
            promedio_bonificaciones = 0.0
            promedio_horas_trabajo_extra = 0.0
            fecha_computable = date(
                fecha_fin.year, fecha_ini.month, fecha_ini.day)
        else:
            fecha_inicio_nominas = date(fecha_ini.year, fecha_ini.month, 1)
            fecha_fin_nominas = fecha_fin - relativedelta(months=+1)
            fecha_fin_nominas = date(fecha_fin_nominas.year, fecha_fin_nominas.month, calendar.monthrange(
                fecha_fin_nominas.year, fecha_fin_nominas.month)[1])

            conceptos = self.env['hr.payslip'].search([('date_from', '>=', fecha_inicio_nominas), (
                'date_to', '<=', fecha_fin_nominas), ('employee_id', '=', contrato.employee_id.id)], order='date_to desc')

            verificar_meses, _ = helper_liquidacion.diferencia_meses_dias(
                fecha_inicio_nominas, fecha_fin_nominas)

            if len(conceptos) != verificar_meses:
                fecha_encontradas = ' '.join(
                    ['\t-'+x.name+'\n' for x in conceptos])
                if not fecha_encontradas:
                    fecha_encontradas = '"No tiene nominas"'
                raise UserError(
                    'Error en VACACIONES: El empleado %s debe tener nominas desde:\n %s hasta %s pero solo tiene nominas en las siguientes fechas:\n %s \nfaltan %d nominas, subsanelas por favor ' % (
                        contrato.employee_id.name_related, fecha_inicio_nominas, fecha_fin_nominas, fecha_encontradas, abs(len(
                            conceptos) - (verificar_meses))
                    ))

            basico = helper_liquidacion.getBasicoByDate(date(fecha_fin_nominas.year,fecha_fin_nominas.month,1),fecha_fin_nominas, contrato.employee_id.id,parametros_gratificacion.cod_basico.code )  # conceptos[0].basico if conceptos else 0.0
            faltas = helper_liquidacion.getSumFaltas(fecha_inicio_nominas,fecha_fin_nominas, contrato.employee_id.id,parametros_gratificacion.cod_dias_faltas.codigo ) #sum([x.dias_faltas for x in conceptos])



            helper_liquidacion = self.env['planilla.helpers']
            meses_comisiones = fecha_fin.month-fecha_computable.month
            comisiones_periodo, promedio_bonificaciones, promedio_horas_trabajo_extra = helper_liquidacion.calcula_comision_gratificacion_hrs_extras(
                contrato, fecha_computable, fecha_fin_nominas, meses_comisiones, fecha_fin)

        bonificacion = promedio_bonificaciones
        comision = comisiones_periodo

        rem_computable = basico + \
            bonificacion + comision + promedio_horas_trabajo_extra

        monto_x_mes = round(rem_computable/12.0, 2)
        monto_x_dia = round(monto_x_mes/30.0, 2)
        monto_x_meses = round(monto_x_mes*meses, 2)
        monto_x_dias = round(monto_x_dia*dias, 2)
        total_faltas = round(monto_x_dia*faltas, 2)

        vacaciones_truncas = monto_x_meses+monto_x_dias
        vacaciones_devengadas = 0
        total_vacaciones = vacaciones_truncas+vacaciones_devengadas

        afiliacion_lines = self.env['planilla.afiliacion.line'].search(
            [('fecha_ini', '=', date_start_liquidacion), ('fecha_fin', '=', date_end_liquidacion)])

        query_afiliacion = """
        select lower(pa.entidad) as entidad,fondo,segi,comf,comm from planilla_afiliacion_line pal
        inner join planilla_afiliacion pa
        on pa.id = pal.planilla_afiliacion_id
        where fecha_ini= '%s' and fecha_fin ='%s' and planilla_afiliacion_id=%d
        """ % (date_start_liquidacion, date_end_liquidacion, contrato.afiliacion_id)

        self.env.cr.execute(query_afiliacion)

        afiliacion = self.env.cr.dictfetchone()
        onp = 0
        afp_jub = 0
        afp_si = 0
        afp_com = 0
        if afiliacion:
            if afiliacion['entidad'] == 'onp':
                onp = afiliacion['fondo']/100*total_vacaciones
            else:
                afp_jub = afiliacion['fondo']/100*total_vacaciones
                afp_si = afiliacion['segi']/100*total_vacaciones
                afp_com = afiliacion['comm']/100*total_vacaciones

        neto_total = total_vacaciones + onp+afp_jub+afp_si+afp_com

        vals = {
            'planilla_liquidacion_id': self.id,
            'employee_id': contrato.employee_id,
            'contract_id': contrato.id,
            'identification_number': contrato.employee_id.identification_id,
            'last_name_father': contrato.employee_id.a_paterno,
            'last_name_mother': contrato.employee_id.a_materno,
            'names': contrato.employee_id.nombres,
            'fecha_ingreso': fecha_ini,
            'fecha_computable': fecha_computable,
            'fecha_cese': fecha_fin,
            'faltas': faltas,
            'basico': basico,
            'comision': comision,
            'bonificacion': bonificacion,
            'horas_extras_mean': promedio_horas_trabajo_extra,
            'remuneracion_computable': rem_computable,
            'meses': meses,
            'dias': dias,
            'monto_x_mes': monto_x_meses,
            'monto_x_dia': monto_x_dias,
            'vacaciones_devengadas': '',
            'vacaciones_truncas': vacaciones_truncas,
            'total_vacaciones': total_vacaciones,
            'onp': onp,
            'afp_jub': afp_jub,
            'afp_si': afp_si,
            'afp_com': afp_com,
            'neto_total': neto_total
        }

        self.planilla_vacaciones_lines.create(vals)
        return True
