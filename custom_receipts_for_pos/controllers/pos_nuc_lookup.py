# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from odoo.exceptions import UserError
import requests

class PosNucLookupController(http.Controller):

    @http.route('/pos/nuc_lookup', type='json', auth='user')  # POS ya va autenticado
    def pos_nuc_lookup(self, vat=None):
        if not vat:
            return {"ok": False, "error": _("Debes ingresar el NIT.")}

        vat_clean = (vat or "").replace(" ", "").upper()

        Partner = request.env['res.partner'].sudo()
        company = request.env.company

        try:
            base_url = Partner._nuc__get_info_nit_url(company)
            username = Partner._nuc__get_username(company)
            token = Partner._nuc__get_authorization(company)

            taxid_company = (company.partner_id.vat or "").strip().zfill(12)
            if not taxid_company:
                return {"ok": False, "error": _("La empresa no tiene configurado el NIT (VAT).")}

            params = {
                "TAXID": taxid_company,
                "DATA1": "SHARED_GETINFONITcom",
                "DATA2": f"NIT|{vat_clean}",
                "COUNTRY": "GT",
                "USERNAME": username,
            }
            headers = {"Authorization": token}

            resp = requests.get(base_url, params=params, headers=headers, timeout=30, verify=True)
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            return {"ok": False, "error": _("Error de conexión al consultar NUC: %s") % str(e)}
        except UserError as ue:
            return {"ok": False, "error": str(ue)}

        try:
            payload = resp.json()
        except Exception:
            return {"ok": False, "error": _("Respuesta no es JSON válido.")}

        data = Partner._first_in(payload, ("RESPONSE", 0)) \
            or payload.get("responseData") \
            or payload.get("responseData1") \
            or payload.get("data")
        if not data or not isinstance(data, dict):
            return {"ok": False, "error": _("NUC no devolvió datos útiles.")}

        # mapeo flexible
        nombre_raw    = data.get("NOMBRE") or data.get("Nombre") or data.get("name")
        direccion_raw = data.get("Direccion") or data.get("DIRECCION") or data.get("Address")
        depto_raw     = data.get("DEPARTAMENTO") or data.get("Departamento")
        muni_raw      = data.get("MUNICIPIO") or data.get("Municipio") or data.get("City")
        cp_raw        = data.get("CodigoPostal") or data.get("ZIP") or data.get("CP")
        pais_code     = (data.get("PAIS") or data.get("Pais") or "GT").upper()

        # mismo limpiador que usas
        nombre_limpio = Partner._cleanup_nombre(nombre_raw)
        if not nombre_limpio:
            return {"ok": False, "error": _("NIT inválido o no encontrado en NUC.")}
        pais_code = (data.get("PAIS") or data.get("Pais") or "GT").upper()
        depto_raw = data.get("DEPARTAMENTO") or data.get("Departamento")

        # Usa tu helper para encontrar GT y state
        gt, state = Partner._find_gt_and_state(depto_raw)

        return {
            "ok": True,
            "data": {
                "vat": vat_clean,
                "name": nombre_limpio,
                "street": direccion_raw or "CIUDAD",
                "city": muni_raw or "",
                "zip": cp_raw or "",
                "country_code": pais_code,
                "state_hint": depto_raw or "",
                # 👇 añade IDs para que el POS pueda setearlos directamente
                "country_id": gt.id if gt else False,
                "state_id": state.id if state else False,
            }

        }
