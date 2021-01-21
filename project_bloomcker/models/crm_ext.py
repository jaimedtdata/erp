# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging


class ProjectExt(models.Model):
    _inherit = 'crm.lead'

    def create_project_ext(self):
        registro = {
            'name':self.name,
        }
        project = self.env['project.project'].create(registro)
        print(project)
        print(self.planned_revenue)
        print("Lo Cree")
        return 0