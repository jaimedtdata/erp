# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging


class ProjectExt(models.Model):
    _inherit = 'project.task'

    milestone_commercial = fields.Boolean(default=False)