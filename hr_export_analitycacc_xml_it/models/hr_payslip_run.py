# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _
from datetime import date, datetime
from odoo.exceptions import ValidationError, UserError
from reportlab.pdfgen import canvas
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
import copy
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, inch, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import StringIO
import time
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

import calendar
from datetime import date, datetime
from openerp.osv import osv
from math import modf
from decimal import *

class HrPayslipRun(models.Model):
	_inherit = ['hr.payslip.run']
	
	@api.multi
	def exportar_planilla_tabular_xlsx(self):
		if len(self.ids) > 1:
			raise UserError(
				'Solo se puede mostrar una planilla a la vez, seleccione solo una nómina')

		self.env['planilla.planilla.tabular.wizard'].reconstruye_tabla(self.date_start,self.date_end)
		try:
			direccion = self.env['main.parameter.hr'].search([])[0].dir_create_file
		except: 
			raise UserError('Falta configurar un directorio de descargas en el menu Configuracion/Parametros/Directorio de Descarga')
		workbook = Workbook(direccion+'planilla_tabular.xls')
		worksheet = workbook.add_worksheet(
			str(self.id)+'-'+self.date_start+'-'+self.date_end)
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
		worksheet.write(x, 0, header_planilla_tabular[0].field_description, formatLeftColor)
		for i in range(1, len(header_planilla_tabular)):
			if i==3:
				worksheet.write(x, i, u'Cta. Analítica', boldbord)
				continue
			if i not in (4,5):
				worksheet.write(x, i, header_planilla_tabular[i].field_description, boldbord)
		worksheet.write(x,i+1,'Aportes ESSALUD',boldbord)
		worksheet.set_row(x, 50)

		fields = ['\"'+column.name+'\"' for column in header_planilla_tabular]
		x = x+1

		filtro = []

		query = 'select %s from planilla_tabular' % (','.join(fields))
		
		self.env.cr.execute(query)
		datos_planilla = self.env.cr.fetchall()
		range_row = len(datos_planilla[0] if len(datos_planilla) > 0 else 0)
		total_essalud = 0
		
		for i in range(len(datos_planilla)):
			d_ana=self.env['hr.payslip'].browse(datos_planilla[i][4]).contract_id.distribucion_analitica_id.descripcion
			for j in range(range_row):
				if j==3:
					worksheet.write(x, j, d_ana, formatLeft)
					continue
				if j not in (4,5):
					if j == 0 or j == 1:
						worksheet.write(x, j, datos_planilla[i][j] if datos_planilla[i][j] else '0.00', formatLeft)
					else:
						worksheet.write(x, j, datos_planilla[i][j] if datos_planilla[i][j] else '0.00', numberdos)
			essalud = self.env['hr.payslip'].browse(datos_planilla[i][4]).essalud
			worksheet.write(x,j+1,essalud,formatLeft)
			total_essalud += essalud


			x = x+1
		x = x + 1
		datos_planilla_transpuesta = zip(*datos_planilla)
		for j in range(5, len(datos_planilla_transpuesta)):
			if j==3:
				worksheet.write(x, j, '', formatLeft)
				continue
			worksheet.write(x, j, sum([float(d) for d in datos_planilla_transpuesta[j]]), styleFooterSum)

		worksheet.write(x,j+1,total_essalud,styleFooterSum)

		# seteando tamaño de columnas
		col_widths = self.get_col_widths(datos_planilla)
		worksheet.set_column(0,0, col_widths[0]-10)
		worksheet.set_column(1,1, col_widths[1]-7)
		worksheet.set_column(2,2, col_widths[0]-10)
		worksheet.set_column(3,3, col_widths[0])

		for i in range(4, len(col_widths)):

			worksheet.set_column(i, i, col_widths[i])

		worksheet.set_column('E:E',None,None,{'hidden':True})
		worksheet.set_column('F:F',None,None,{'hidden':True})

		workbook.close()

		f = open(direccion+'planilla_tabular.xls', 'rb')

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