# -*- coding: utf-8 -*-
import logging
import requests

from odoo import api, fields, models, _
from odoo.exceptions import UserError




class ResPartner(models.Model):
    _inherit = 'res.partner'

    # =========================
    # Helpers de configuración
    # =========================
    def _nuc__get_info_nit_url(self, company):
        """Devuelve la URL del endpoint Get Info NIT según el ambiente."""
        nuc = company.nuc_guatemala
        if not nuc:
            raise UserError(_("No se ha configurado (nuc.guatemala) en la compañía."))

        if company.type_env:
            if not nuc.url_get_info_nit:
                raise UserError(_("Falta configurar 'Url Get Info Nit' en nuc.guatemala (Producción)."))
            return nuc.url_get_info_nit
        else:
            if not nuc.url_get_info_nit_dev:
                raise UserError(_("Falta configurar 'Url Get Info Nit (Test)' en nuc.guatemala."))
            return nuc.url_get_info_nit_dev

    def _nuc__get_username(self, company):
        """USERNAME = GT.{VAT_12}.{nuc.user} (mismo formato que usas para el token)."""
        nuc = company.nuc_guatemala
        if not nuc or not nuc.user:
            raise UserError(_("No se ha configurado el usuario de NUC en (nuc.guatemala)."))

        vat_company = (company.partner_id.vat or "").strip()
        if not vat_company:
            raise UserError(_("La empresa no tiene configurado el NIT (VAT)."))

        vat_12 = vat_company.zfill(12)
        return f"GT.{vat_12}.{nuc.user}"

    def _nuc__get_authorization(self, company):
        """Obtiene el token del ambiente; si no hay, lo renueva con get_token_nuc()."""
        nuc = company.nuc_guatemala
        token = nuc.token if company.type_env else nuc.token_dev
        if not token:
            token = nuc.get_token_nuc()
        if not token:
            raise UserError(_("No se pudo obtener el token de NUC. Verifica credenciales/URLs."))
        return token

    # ======================
    # Helpers de normalización
    # ======================
    @api.model
    def _first_in(self, payload, *paths):
        """
        Devuelve el primer dict hallado en los 'paths':
          - ('RESPONSE', 0) -> payload['RESPONSE'][0] si existe
          - ('responseData',) -> payload['responseData'] si existe
        """
        for path in paths:
            node = payload
            try:
                for key in path:
                    node = node[key]
                if isinstance(node, dict):
                    return node
            except Exception:
                continue
        return None

    @api.model
    def _pick_any(self, data, *keys, default=None):
        """Primer valor no vacío para cualquiera de las llaves dadas (case-insensitive)."""
        if not isinstance(data, dict):
            return default
        lowered = {str(k).lower(): v for k, v in data.items()}
        for k in keys:
            v = lowered.get(str(k).lower())
            if v not in (None, "", []):
                return v
        return default

    @api.model
    def _cleanup_nombre(self, raw):
        """Limpia 'GARCIA,ROSALES,,RUPTILIO,' -> 'Garcia Rosales Rupilito' (title-case)."""
        if not raw:
            return raw
        txt = " ".join([p for p in raw.replace(",", " ").split() if p.strip()])
        return txt.title()

    @api.model
    def _find_gt_and_state(self, depto_name):
        """Busca Guatemala (country) y un state que 'se parezca' al departamento."""
        Country = self.env["res.country"]
        State = self.env["res.country.state"]
        gt = Country.search([("code", "=", "GT")], limit=1)
        st = False
        if gt and depto_name:
            st = State.search([
                ("country_id", "=", gt.id),
                ("name", "ilike", (depto_name or "").strip())
            ], limit=1)
        return gt, st

    # ======================
    # Acción principal
    # ======================
    def action_buscar_nit(self):
        """Consulta NUC (Get Info NIT) y actualiza el partner con los datos recibidos."""
        for partner in self:
            vat = (partner.name or "").strip().upper()
            if not vat:
                raise UserError(_("Debes ingresar el NIT para hacer la consulta."))

            company = partner.company_id or self.env.company
            nuc = company.nuc_guatemala
            if not nuc:
                raise UserError(_("No se ha configurado (nuc.guatemala) en la compañía."))

            base_url = self._nuc__get_info_nit_url(company)
            username = self._nuc__get_username(company)
            token = self._nuc__get_authorization(company)

            taxid_company = (company.partner_id.vat or "").strip().zfill(12)
            if not taxid_company:
                raise UserError(_("La empresa no tiene configurado el NIT (VAT)."))

            params = {
                "TAXID": taxid_company,
                "DATA1": "SHARED_GETINFONITcom",
                "DATA2": f"NIT|{vat}",
                "COUNTRY": "GT",
                "USERNAME": username,
            }
            headers = {"Authorization": token}

            
            try:
                resp = requests.get(base_url, params=params, headers=headers, timeout=30, verify=True)
                resp.raise_for_status()
            except requests.exceptions.RequestException as e:
                raise UserError(_("Error de conexión al consultar NUC:\n%s") % str(e))

            # Intentar parsear JSON
            try:
                payload = resp.json()
            except Exception:
                raise UserError(_("Respuesta no es JSON válido:\n%s") % resp.text[:1000])

            # 1) Formato que mostraste: RESPONSE[0]
            data = self._first_in(payload, ("RESPONSE", 0))
            # 2) Fallbacks
            if not data:
                data = (payload.get("responseData")
                        or payload.get("responseData1")
                        or payload.get("data"))

            if not data or not isinstance(data, dict):
                raise UserError(_("NUC no devolvió datos útiles. Respuesta: %s") % str(payload)[:1000])

            # --- Mapeo flexible con prioridad a tu formato ---
            nombre_raw     = data.get("NOMBRE") or data.get("Nombre") or data.get("name") or partner.name
            direccion_raw  = data.get("Direccion") or data.get("DIRECCION") or data.get("Address") or partner.street
            depto_raw      = data.get("DEPARTAMENTO") or data.get("Departamento")
            muni_raw       = data.get("MUNICIPIO") or data.get("Municipio") or data.get("City") or partner.city
            cp_raw         = data.get("CodigoPostal") or data.get("ZIP") or data.get("CP") or partner.zip
            pais_code      = data.get("PAIS") or data.get("Pais") or "GT"

            nombre_limpio = self._cleanup_nombre(nombre_raw)

            vals = {
                "vat": partner.name,
                "name":   nombre_limpio or partner.name,
                "street": (direccion_raw or partner.street) or "CIUDAD",
                "city":   muni_raw or partner.city,
                "zip":    cp_raw or partner.zip,
            }

            # (Opcional) Asignar país/estado si existen
            if (pais_code or "").upper() == "GT":
                gt, state = self._find_gt_and_state(depto_raw)
                if gt and not partner.country_id:
                    vals["country_id"] = gt.id
                if state:
                    vals["state_id"] = state.id

            partner.write(vals)
            partner.message_post(
                body=_("Datos actualizados desde NUC para el NIT %s.") % vat,
                subtype_xmlid="mail.mt_note",
            )

        return True

    _sql_constraints = [
        ('unique_vat', 'unique(vat)', 'El NIT (VAT) debe ser único.'),
    ]
    company_type = fields.Selection(string='Company Type', default='person',
        selection=[('person', 'Individual'), ('company', 'Company')],
        compute='_compute_company_type', inverse='_write_company_type')
    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        """ Permitir buscar por nombre, número de móvil y NIT (VAT),
            eliminando los espacios del número móvil antes de buscar. """
        args = args or []
        if name:
         
            clean_vat = name.replace(" ", "")

            domain = [
                '|', '|',
                ('name', operator, name),        # Búsqueda por nombre # Búsqueda por móvil sin espacios
                ('vat', operator, clean_vat)     # Búsqueda por NIT (VAT)
            ] + args

            partners = self.search(domain, limit=limit)

            if not partners:
                # Búsqueda avanzada quitando espacios de 'mobile' y 'vat' en la base de datos
                query = """
                    SELECT id FROM res_partner
                    WHERE (
                        REPLACE(vat, ' ', '') ILIKE %s
                    )
                    LIMIT %s
                """
                self.env.cr.execute(query, (
                  
                    f"%{clean_vat}%",
                    limit
                ))
                partner_ids = [row[0] for row in self.env.cr.fetchall()]
                if partner_ids:
                    partners = self.browse(partner_ids)

            return partners.name_get()
        return super().name_search(name, args, operator, limit)