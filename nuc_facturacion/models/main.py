# -*- coding: utf-8 -*-
from odoo import models, fields, api,_
from odoo.exceptions import UserError
import requests
from datetime import datetime
from dateutil import parser

class FacturacionGuatemala(models.Model):
    _name = 'nuc.guatemala'
    _description = 'nuc Guatemala'
    
    name = fields.Char('Razón Social')
    afiliacion_iva = fields.Char("Afiliacion IVA")
    tipofrase = fields.Char("Tipo Frase")
    escenario = fields.Char("Escenario")
    codigo_establecimiento = fields.Char("Codigo Establecimiento")
    url = fields.Char("Url Api Nuc Producción")
    url_dev = fields.Char("Url Api Nuc (Test)")
    url_token = fields.Char("Url Token")
    url_token_dev = fields.Char("Url Token (Test)")
    token = fields.Text("Token")
    token_dev = fields.Text("Token (Test)")
    url_annul = fields.Char("Url Api Annul")
    url_annul_dev = fields.Char("Url Api Annul (Test)")
    url_get_info_nit_dev = fields.Char("Url Get Info Nit (Test)")
    url_get_document_dev = fields.Char("Url Get Document (Test)")
    url_get_info_nit = fields.Char("Url Get Info Nit")
    url_get_document = fields.Char("Url Get Document")
    user = fields.Char("User")
    password = fields.Char("Password")
    expiration_date = fields.Datetime('Token expira en')
    expiration_date_dev = fields.Datetime('Token expira en (Test)')
    
    def get_token_nuc(self):
        company_id = self.env.company
        nuc_guatemal_id = company_id.nuc_guatemala
        is_production = company_id.type_env
        if is_production:
            if nuc_guatemal_id.url_token:
                url_token = nuc_guatemal_id.url_token
            else:
              
                raise UserError(_("No se ingresó URL token de produccion"))
        else:
            if nuc_guatemal_id.url_token_dev:
                url_token = nuc_guatemal_id.url_token_dev
            else:
              
                raise UserError(_("No se ingresó URL token de Test"))
     
        if not url_token:
            raise UserError(_("No se configuró el url token "))
        if url_token == "":
            raise UserError(_("No se configuró el url token "))
        vat_12 = (company_id.partner_id.vat or '').zfill(12)
        username = f"GT.{vat_12}.{nuc_guatemal_id.user}"
        json_data = {
            "Username": username,
            "Password": nuc_guatemal_id.password,
        }
        headers = {"content-type": "application/json"}
        response = requests.post(
            url=url_token, json=json_data, headers=headers, verify=False)
        json = response.json()
        if json:
            if "Token" in json:
                token = json["Token"]
                date = False

                if json.get("expira_en"):
                    expira_en = json.get("expira_en", "").strip()
                    date = parser.parse(expira_en)

                if is_production:
                    nuc_guatemal_id.token = token
                    nuc_guatemal_id.expiration_date = date
                else:
                    nuc_guatemal_id.token_dev = token
                    nuc_guatemal_id.expiration_date_dev = date

                return token
            else:
                if json.get("response"):
                    raise UserError(
                        "No se encontró el token.\n"
                        "Respuesta: {}\n"
                        "Usuario enviado: {}\n"
                        "Password enviada: {}".format(
                            json.get("response"),
                            username,
                            nuc_guatemal_id.password
                        )
                    )
                else:
                    raise UserError(
                        "No se pudo obtener el token.\n"
                        "Usuario enviado: {}\n"
                        "Password enviada: {}\n"
                        "Verifique URL, USER y PASSWORD.".format(
                            username,
                            password
                        )
                    )
        else:
            raise UserError(
                "Respuesta vacía del servicio de token.\n"
                "Usuario enviado: {}\n"
                "Password enviada: {}\n"
                "Verifique URL, USER y PASSWORD.".format(
                    username,
                    password
                )
            )