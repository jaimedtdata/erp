# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging


class ProjectExt(models.Model):
    _inherit = 'project.task'

    def _get_project_id_domain(self):
        dominio = [(self.id, '=', self.id)]
        return [(self.id, '=', self.id)]

    milestone_commercial = fields.Boolean(default=False)
    user_id = fields.Many2one('res.users', string='Assigned to', index=True, track_visibility='always', domain=lambda self: self._get_project_id_domain())