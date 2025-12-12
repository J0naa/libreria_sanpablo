# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError

class pa_dgi_server(models.Model):
    _inherit = 'res.company'
    _description = 'Guatemala Server'

    type_env = fields.Boolean("Tipo de Ambiente")
    url = fields.Char("Url Producción")
    url_dev = fields.Char("Url Desarrollo")
    user = fields.Char("User")
    password = fields.Char("Password")
    nuc_guatemala = fields.Many2one('nuc.guatemala', string='Nuc Guatemala',required=True)
    afiliacion_iva = fields.Char("Afiliacion IVA")
    tipofrase = fields.Char("Tipo Frase")
    escenario = fields.Char("Escenario")
    codigo_establecimiento = fields.Char("Codigo Establecimiento")
            

    @api.onchange('nuc_guatemala')
    def _onchange_pac_panama_id(self):
        if self.nuc_guatemala:
            self.url = self.nuc_guatemala.url 
            self.url_dev = self.nuc_guatemala.url_dev 
            self.password = self.nuc_guatemala.password 
            self.user = self.nuc_guatemala.user 

            self.afiliacion_iva = self.nuc_guatemala.afiliacion_iva
            self.tipofrase = self.nuc_guatemala.tipofrase
            self.escenario = self.nuc_guatemala.escenario
            self.codigo_establecimiento = self.nuc_guatemala.codigo_establecimiento
            