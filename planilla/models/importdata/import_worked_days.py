
# -*- coding: utf-8 -*-
from odoo.exceptions import ValidationError, UserError
from odoo import api, fields, models, _, exceptions
from datetime import datetime
import re
import time
import collections
import base64


class PlanillaImportWorkedDays(models.Model):

    _name = "planilla.import.worked.days"
    fecha_ini = fields.Date("Fecha inicio", required="1")
    fecha_fin = fields.Date("Fecha fin", required="1")
    file_imp = fields.Binary(
        u'Archivo importación Dias de trabajo')
    file_input_lines = fields.Binary(
        u'Archivo importación Entradas')
    file_sal_error  = fields.Binary('Archivo Errores dias trabajo',readonly=1)
    file_error_entradas  = fields.Binary('Archivo Errores entradas',readonly=1)

    file_imp_text = fields.Char('dias trabajo',default=u'importacion_dias_trabajo.csv')
    file_input_lines_text = fields.Char('dias entradas',default=u'importacion_worked_days.csv')
    sal_name2 = fields.Char('errores dias trabajo',default='errores_importacion_dias_trabajo.csv')
    sal_name3 = fields.Char('errores entradas',default='errores_importacion_entradas.csv')


    def valida_informacion(self, file_input_lines, type_expr=1):
        informacion_csv = base64.b64decode(file_input_lines)
        informacion_array = informacion_csv.strip().split("\n")
        # header_csv = ''.join(
        #     ['\''+x+'\',' for x in informacion_array[0].split(',')])
        # header_csv = header_csv[:-1]
        # informacion_array = informacion_array[1:]

        # if type_expr == 1:
        #     expr_reg = r'([\d]{8}),(([0-9]*\.?[0-9]+),){%d}' % (
        #         len(informacion_array[0].split(','))-2)+r'([0-9]*\.?[0-9]+)'
        # else:
        #     expr_reg = r'([\d]{8}),(([0-9]*\.?[0-9]+):([0-9]*\.?[0-9]+),){%d}' % (
        #         len(informacion_array[0].split(','))-2)+r'([0-9]*\.?[0-9]+):([0-9]*\.?[0-9]+)'

        # verify = re.compile(expr_reg)
        # for i in range(len(informacion_array)):
        #     match = verify.match(informacion_array[i])
        #     if not match:
        #         raise UserError('Error de sintaxis en linea: %d, ' % (
        #             i+2) + informacion_array[i][:8]+'\n'+'Por favor corriga y vuelva a subir el archivo')

        informacion_array.sort(key=lambda x: x[:8])
        return informacion_array

        # dni_array = ['\''+x[:8]+'\',' for x in informacion_array]
        # informacion_dnis = ''.join(dni_array)
        # informacion_dnis = informacion_dnis[:-1]

        # duplicates = [item for item, count in collections.Counter(
        #     dni_array).items() if count > 1]

        # print duplicates
        # if len(duplicates) > 0:
        #     raise UserError('Registro duplicado: '+''.join(duplicates)+'\n' +
        #                     'DNI no debe repetirse mas de una vez. Por favor corriga y vuelva a subir el archivo')

        # return informacion_dnis, informacion_array

    @api.multi
    def procesa_worked_days(self):

        start_time = time.time()
        informacion_array = self.valida_informacion(
            self.file_imp, 2)

        # obtengo los contratos
        # query_payslip_employee = """
        #     select hp.id,hp.contract_id,e.id as employee_id,e.identification_id from hr_payslip hp
        #     inner join hr_employee e
        #     on hp.employee_id = e.id
        #     where date_from >='%s' and (date_to is null or date_to <= '%s') and e.identification_id in (%s)
        #     order by identification_id
        # """ % (self.fecha_ini, self.fecha_fin, informacion_dnis)

        # self.env.cr.execute(query_payslip_employee)
        # #payslips = self.env['hr.payslip'].search(['&','|',('date_to', '&lt;=', self.fecha_fin),('date_to','=',False) ,('date_from', '&gt;=', self.fecha_ini)])
        # payslips = self.env.cr.dictfetchall()

        # payslip_ids = [  payslips['id'] for payslips['id'] in payslips ]

        # payslip_ids= ','.join(payslip_ids)
        # informacion_dnis = informacion_dnis+informacion_array

        # #eliminando registros
        # query_del_worked_days_anteriores = """

        # delete from hr_payslip_worked_days
        #     where payslip_id in(
        #      %s
        # )
        # """ % (payslip_ids)

        # self.env.cr.execute(query)

        # ingresando registros

        # informacion_dnis = informacion_dnis+informacion_array
        list_horrores=[]
        for line in informacion_array:
            line = line.split(',')
            print line
            query_payslip_employee = """
            select hp.id,hp.contract_id,e.id as employee_id,e.identification_id from hr_payslip hp
            inner join hr_employee e
            on hp.employee_id = e.id
            where date_from >='%s' and (date_to is null or date_to <= '%s') and e.identification_id = '%s'
            """ % (self.fecha_ini, self.fecha_fin, line[0])

            print query_payslip_employee

            self.env.cr.execute(query_payslip_employee)
            payslip_dni = self.env.cr.dictfetchall()
            print payslip_dni

            if len(payslip_dni) > 0 and line[1] and line[2] and line[3] and line[4]:
                for worked_day in payslip_dni:
                    wd = self.env['hr.payslip.worked_days'].search([('payslip_id', '=', worked_day['id']),
                                                                    ('contract_id', '=',
                                                                     worked_day['contract_id']),
                                                                    ('code', '=',
                                                                     line[1])
                                                                    ])
                    wd.number_of_days = line[2]
                    wd.number_of_hours = line[3]
                    wd.minutos = line[4]
            else:
                print "horror ",line
                list_horrores.append(line)



            horrores = open(str( 'horroresimportacion.csv' ),'w+' )
            for item in list_horrores:
                horrores.write("%s\n" % item)
            horrores.close()
            horrores_read = open(str( 'horroresimportacion.csv' ),'r' ).read()


            self.file_sal_error = base64.encodestring(horrores_read)
                # data = {
                #     'name': '',
                #     'payslip_id': payslip_dni['id'],
                #     'code': line[1].strip(),
                #     'number_of_days': line[2],
                #     'number_of_hours': line[3],
                #     'tasa': line[4],
                #     'contract_id': payslip_dni['contract_id'],
                # }
                # self.env['hr.payslip.worked_days'].create(data)

        # obtengo los contratos
        # query_payslip_employee = """
        #     select hp.id,hp.contract_id,e.id as employee_id,e.identification_id from hr_payslip hp
        #     inner join hr_employee e
        #     on hp.employee_id = e.id
        #     where date_from >='%s' and (date_to is null or date_to <= '%s') and e.identification_id in (%s)
        #     order by identification_id
        # """ % (self.fecha_ini, self.fecha_fin, informacion_dnis)

        # self.env.cr.execute(query_payslip_employee)
        # #payslips = self.env['hr.payslip'].search(['&','|',('date_to', '&lt;=', self.fecha_fin),('date_to','=',False) ,('date_from', '&gt;=', self.fecha_ini)])
        # payslips = self.env.cr.dictfetchall()

        # worked_days_codes = self.env['planilla.worked.days'].search([])

        # body ="INSERT into hr_payslip_worked_days(name,payslip_id,sequence,code,number_of_days,number_of_hours,contract_id,write_uid,write_date,create_date) values"

        # if len(payslips) != len(informacion_array):
        #     raise UserError(
        #         'El numero de nominas(%d) no coincide con el numero de registros(%d)' % (len(payslips), len(informacion_array)))

        # i = 0
        # for payslip in payslips:
        #     current_employee_line = informacion_array[i].split(',')[1:]
        #     current_payslip = self.env['hr.payslip'].browse(payslip['id'])
        #     if current_payslip:
        #         current_payslip.worked_days_line_ids.unlink()

        #     j = 0
        #     for worked_day in worked_days_codes:
        #         current_amount = current_employee_line[j].split(':')
        #         data = {
        #             'name': worked_day.descripcion,
        #             'payslip_id': payslip['id'],
        #             'code': worked_day.codigo,
        #             'number_of_days': current_amount[0],
        #             'number_of_hours': current_amount[1],
        #             'contract_id': payslip['contract_id'],
        #         }
        #         self.env['hr.payslip.worked_days'].create(data)
        #         j = j+1
        #     i = i+1
        print("--- %s TIEMPO FINAL EJECUCION ---" % (time.time() - start_time))
        print "TERMINEE!!!"
        if len(list_horrores)>0:
            return self.env['planilla.warning'].info(title='Resultado de importacion', message="Hubo errores,verifique la fecha de inicio y fecha de fin sea correcto y revise el archivo de errorers de dias de trabajo y verifique las fechas!!!")
        else:
            return self.env['planilla.warning'].info(title='Resultado de importacion', message="Dias de trabajo importados con exito!!!")

    @api.multi
    def procesa_entradas(self):

        start_time = time.time()

        informacion_array = self.valida_informacion(
            self.file_input_lines, 2)
        list_horrores=[]
        for line in informacion_array:
            line = line.split(',')
            print line
            query_payslip_employee = """
            select hp.id,hp.contract_id,e.id as employee_id,e.identification_id from hr_payslip hp
            inner join hr_employee e
            on hp.employee_id = e.id
            where date_from >='%s' and (date_to is null or date_to <= '%s') and e.identification_id = '%s'
            """ % (self.fecha_ini, self.fecha_fin, line[0])

            print query_payslip_employee

            self.env.cr.execute(query_payslip_employee)
            payslip_dni = self.env.cr.dictfetchall()
            print payslip_dni
            
            if len(payslip_dni) > 0 and line[1] and line[2]:
                for worked_day in payslip_dni:
                    wd = self.env['hr.payslip.input'].search([('payslip_id', '=', worked_day['id']),
                                                              ('contract_id', '=',
                                                               worked_day['contract_id']),
                                                              ('code', '=', line[1])])

                    wd.amount = line[2]
            else:
                print "horror ",line
                list_horrores.append(line)
                
                # data = {'name': '',
                #         'payslip_id':  payslip_dni['id'],
                #         'code': line[1].strip(),
                #         'amount': line[2],
                #         'contract_id':  payslip_dni['contract_id'],
                #         }
                # self.env['hr.payslip.input'].create(data)


            horrores = open(str( 'horroresimportacion.csv' ),'w+' )
            for item in list_horrores:
                print "escribiendo horror",item
                horrores.write("%s\n" % item)
            horrores.close()
            horrores_read = open(str( 'horroresimportacion.csv' ),'r' ).read()


            self.file_error_entradas = base64.encodestring(horrores_read)



        # informacion_dnis, informacion_array = self.valida_informacion(
        #     self.file_input_lines)

        # query_payslip_employee = """
        #     select hp.id,hp.contract_id,e.id as employee_id,e.identification_id from hr_payslip hp
        #     inner join hr_employee e
        #     on hp.employee_id = e.id
        #     where date_from >='%s' and (date_to is null or date_to <= '%s') and e.identification_id in (%s)
        #     order by identification_id
        # """ % (self.fecha_ini, self.fecha_fin, informacion_dnis)

        # self.env.cr.execute(query_payslip_employee)
        # payslips = self.env.cr.dictfetchall()
        # inputs = self.env['planilla.inputs.nomina'].search([])

        # if len(payslips) != len(informacion_array):
        #     raise UserError(
        #         'El numero de nominas(%d) no coincide con el numero de registros(%d)' % (len(payslips), len(informacion_array)))

        # i = 0
        # for payslip in payslips:
        #     current_employee_line = informacion_array[i].split(',')[1:]
        #     current_payslip = self.env['hr.payslip'].browse(payslip['id'])
        #     if current_payslip:
        #         current_payslip.input_line_ids.unlink()
        #     j = 0
        #     for my_input in inputs:
        #         data = {'name': my_input.descripcion,
        #                 'payslip_id': payslip['id'],
        #                 'code': my_input.codigo,
        #                 'amount': current_employee_line[j],
        #                 'contract_id': payslip['contract_id'],
        #                 }
        #         self.env['hr.payslip.input'].create(data)
        #         j = j+1
        #     i = i+1
        print("--- %s TIEMPO FINAL EJECUCION ---" % (time.time() - start_time))
        print "TERMINEE!!!"
        if len(list_horrores)>0:
            return self.env['planilla.warning'].info(title='Resultado de importacion', message="Hubo errores,verifique la fecha de inicio y fecha de fin sea correcto y revise el archivo de errorers de entradas!!!")
        else:
            return self.env['planilla.warning'].info(title='Resultado de importacion', message="Entradas importados con exito!!!")
