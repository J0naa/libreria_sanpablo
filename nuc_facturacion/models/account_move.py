# -*- coding: utf-8 -*-
from lxml import etree
from pytz import timezone
from uuid import uuid4
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import json
class AccountMove(models.Model):
    _inherit = 'account.move'
    cancellation_reason = fields.Char(
        'Motivo de Anulación', readonly=True,  copy=False)
    gt_pdf_document = fields.Binary("PDF DTE Guatemala", attachment=True)
    gt_pdf_filename = fields.Char("Nombre del PDF")
    gt_dte_numero = fields.Char("Numero")
    gt_dte_auth_number = fields.Char("Número de Autorización")
    gt_estado_dte = fields.Char("Estado SAT", default="Sin enviar")
    gt_dte_serie = fields.Char("Serie")
    gt_fecha_envio = fields.Char("Fecha")
    

from odoo.exceptions import UserError
from lxml import etree

class AccountMove(models.Model):
    _inherit = "account.move"

    def _post(self, soft=True):
        for invoice in self:
            if invoice.move_type != 'out_invoice':
                continue

            if invoice.gt_estado_dte in ('Completado', 'Cancelado'):
                raise UserError(_("La factura %s ya fue enviada y se encuentra en estado '%s'. No se puede volver a validar.") % (invoice.name, invoice.gt_estado_dte))

            partner_vat = (invoice.partner_id.vat or '').strip().upper()
            is_cf = not partner_vat or partner_vat == 'CF'

            try:
                xml_root = invoice._generate_invoice_xml(cf=is_cf)
                xml_string = etree.tostring(
                    xml_root, pretty_print=True, encoding='UTF-8', xml_declaration=True
                ).decode()
                invoice._send_to_nuc(xml_string)
            except Exception as e:
                # Lanzar excepción para que NO se valide la factura
                raise UserError(_("Error al enviar DTE de la factura %s: %s") % (invoice.name, str(e)))

        # Si todas pasan, entonces sí se postean
        return super(AccountMove, self)._post(soft=soft)

    def _generate_invoice_xml(self, cf=False):
        self.ensure_one()
        partner = self.partner_id
        company = self.company_id
        currency = self.currency_id or company.currency_id
        nuc = company.nuc_guatemala

        afiliacion_iva = company.afiliacion_iva or nuc.afiliacion_iva or "GEN"
        tipo_frase = company.tipofrase or nuc.tipofrase or "1"
        escenario = company.escenario or nuc.escenario or ("1" if cf else "2")
        codigo_establecimiento = company.codigo_establecimiento or nuc.codigo_establecimiento or "1"
        gt_time = fields.Datetime.now().astimezone(timezone("America/Guatemala"))
        fecha_emision = gt_time.strftime("%Y-%m-%dT%H:%M:%S-06:00")

        root = etree.Element("Root")
        etree.SubElement(root, "Version").text = "1.00"
        etree.SubElement(root, "CountryCode").text = "GT"

        header = etree.SubElement(root, "Header")
        etree.SubElement(header, "DocType").text = "FACT"
        etree.SubElement(header, "IssuedDateTime").text = fecha_emision
        etree.SubElement(header, "Currency").text = currency.name

        seller = etree.SubElement(root, "Seller")
        etree.SubElement(seller, "TaxID").text = company.vat or ""
        etree.SubElement(etree.SubElement(seller, "TaxIDAdditionalInfo"), "Info", Name="AfiliacionIVA", Value=afiliacion_iva)
        etree.SubElement(seller, "Name").text = company.name or ""
       
        contact = etree.SubElement(seller, "Contact")
        etree.SubElement(etree.SubElement(contact, "EmailList"), "Email").text = company.email or "correo@ejemplo.com"
        frases = etree.SubElement(seller, "AdditionlInfo")
        etree.SubElement(frases, "Info", Name="TipoFrase", Data="1", Value=tipo_frase)
        etree.SubElement(frases, "Info", Name="Escenario", Data="1", Value=escenario)

        branch = etree.SubElement(seller, "BranchInfo")
        etree.SubElement(branch, "Code").text = codigo_establecimiento
        etree.SubElement(branch, "Name").text = company.name or "ESTABLECIMIENTO"
        address_info = etree.SubElement(branch, "AddressInfo")
        etree.SubElement(address_info, "Address").text = company.street or ''
        etree.SubElement(address_info, "City").text = company.zip or "01010"
        etree.SubElement(address_info, "District").text = company.city or "Guatemala"
        etree.SubElement(address_info, "State").text = company.state_id.name or "Guatemala"
        etree.SubElement(address_info, "Country").text = "GT"

        buyer = etree.SubElement(root, "Buyer")
        etree.SubElement(buyer, "TaxID").text = "CF" if cf else partner.vat or ""
        etree.SubElement(buyer, "Name").text = "CONSUMIDOR FINAL" if cf else partner.name or "CLIENTE"
        if not cf and partner.vat and len(partner.vat.strip()) == 13:
            etree.SubElement(buyer, "TaxIDType").text = "CUI"

        buyer_address = etree.SubElement(buyer, "AddressInfo")
        etree.SubElement(buyer_address, "Address").text = partner.street or "CIUDAD"
        etree.SubElement(buyer_address, "City").text = partner.zip or "01010"
        etree.SubElement(buyer_address, "District").text = partner.city or "GUATEMALA"
        etree.SubElement(buyer_address, "State").text = partner.state_id.name or "GUATEMALA"
        etree.SubElement(buyer_address, "Country").text = "GT"

        items_node = etree.SubElement(root, "Items")
        total_impuesto = 0
        total_general = 0
        for line in self.invoice_line_ids.filtered(lambda l: l.product_id and l.quantity > 0):
            price_unit = line.price_unit
            quantity = line.quantity
            subtotal = line.price_subtotal
            tax_data = line.tax_ids.compute_all(price_unit, currency, quantity)['taxes']
            tax_amount = sum(t['amount'] for t in tax_data)
            total_impuesto += tax_amount
            total_line_total = subtotal + tax_amount
            total_general += total_line_total

            item_node = etree.SubElement(items_node, "Item")
            etree.SubElement(item_node, "Type").text = "Bien" if line.product_id.type != 'service' else "Servicio"
            etree.SubElement(item_node, "Description").text = line.name
            etree.SubElement(item_node, "Qty").text = f"{quantity:.6f}"
            etree.SubElement(item_node, "UnitOfMeasure").text = (line.product_uom_id.name[:3].upper() if line.product_uom_id else "UNI")
            etree.SubElement(item_node, "Price").text = f"{price_unit:.6f}"
            taxes_node = etree.SubElement(item_node, "Taxes")
            tax_node = etree.SubElement(taxes_node, "Tax")
            etree.SubElement(tax_node, "Code").text = "1"
            etree.SubElement(tax_node, "Description").text = "IVA"
            etree.SubElement(tax_node, "TaxableAmount").text = f"{subtotal:.6f}"
            etree.SubElement(tax_node, "Amount").text = f"{tax_amount:.6f}"
            totals_node = etree.SubElement(item_node, "Totals")
            etree.SubElement(totals_node, "TotalItem").text = f"{total_line_total:.6f}"

        totals = etree.SubElement(root, "Totals")
        total_taxes = etree.SubElement(totals, "TotalTaxes")
        total_tax = etree.SubElement(total_taxes, "TotalTax")
        etree.SubElement(total_tax, "Description").text = "IVA"
        etree.SubElement(total_tax, "Amount").text = f"{total_impuesto:.6f}"
        etree.SubElement(etree.SubElement(totals, "GrandTotal"), "InvoiceTotal").text = f"{total_general:.6f}"

        letras = self.currency_id.amount_to_text(self.amount_total).upper()

        additional_doc = etree.SubElement(root, "AdditionalDocumentInfo")
        additional_info = etree.SubElement(additional_doc, "AdditionalInfo")
        etree.SubElement(additional_info, "Code").text = f"FRONT-{uuid4().hex[:4]}-{uuid4().hex[4:8]}-XXXX-ADENDA"
        etree.SubElement(additional_info, "Type").text = "ADENDA"
        aditional_data = etree.SubElement(additional_info, "AditionalData")
        info_data = etree.SubElement(aditional_data, "Data", Name="INFORMACION_ADICIONAL")
        etree.SubElement(info_data, "Info", Name="OBSERVACIONES", Value="-")
        etree.SubElement(info_data, "Info", Name="CANTIDAD_LETRAS", Value=letras)
        aditional_info_tag = etree.SubElement(additional_info, "AditionalInfo")
        etree.SubElement(aditional_info_tag, "Info", Name="VALIDAR_REFERENCIA_INTERNA", Value="NO_VALIDAR")

        return root

    def _send_to_nuc(self, xml_bytes):
        self.ensure_one()
        company = self.company_id
        nuc = company.nuc_guatemala

        if not nuc:
            raise UserError("No se ha configurado el (nuc.guatemala) en la compañía.")
        is_prod = company.type_env
        base_url = nuc.url if is_prod else nuc.url_dev
        token = nuc.token if is_prod else nuc.token_dev
        if not base_url:
            raise UserError("No se ha configurado la URL de envío en la configuracion.")
        if not token:
            token = nuc.get_token_nuc()

        if not company.partner_id.vat:
            raise UserError("La empresa no tiene configurado el NIT (VAT).")
        vat_12 = company.partner_id.vat.zfill(12)
        username = f"GT.{vat_12}.{nuc.user}"
       
        url_envio = f"{base_url}?TAXID={company.partner_id.vat}&USERNAME={username}&FORMAT=PDF"

        headers = {
            "Content-Type": "application/xml",
            "Authorization": token
        }
       
  
        try:
            response = requests.post(url_envio, data=xml_bytes, headers=headers, verify=True)
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            # Capturar detalles si hay respuesta del PAC/SAT
            content = ""
            try:
                content = response.text  # o response.json() si esperás JSON
            except Exception:
                pass

            raise UserError(f"Error al enviar solicitud a la SAT:\n{e}\n\nRespuesta:\n{content}")
        except requests.exceptions.RequestException as e:
            raise UserError(f"Error de conexión al enviar solicitud a la SAT:\n{str(e)}")

        json_response = response.json()
        if json_response.get("code") != 1:
            mensaje = json_response.get("message") or "Error desconocido del SAT"
            detalles = json_response.get("description") or ""
            raise UserError(f"Error del SAT:\n{mensaje}\n\nDetalles:\n{detalles}")

        pdf_base64 = json_response.get("responseData3")
        serial = json_response.get("serial")
        auth_number = json_response.get("authNumber")
        batch = json_response.get("batch")
        fecha_envio = json_response.get("issuedTimeStamp")

        if not pdf_base64 or not serial or not auth_number:
            raise UserError("La respuesta del SAT está incompleta. Verifica la configuración y el XML.")

        self.gt_pdf_document = pdf_base64
        self.gt_pdf_filename = f"DTE_{self.name or 'sin_nombre'}.pdf"
        self.gt_dte_numero = serial
        self.gt_dte_auth_number = auth_number
        self.gt_dte_serie = batch
        self.gt_fecha_envio = fecha_envio
        self.gt_estado_dte = 'Completado'
    def action_show_gt_pdf(self):
        self.ensure_one()
        if not self.gt_pdf_document:
            raise UserError("No hay un PDF de DTE disponible para esta factura.")

        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content?model=account.move&id={self.id}&field=gt_pdf_document&filename_field=gt_pdf_filename&download=false",
            "target": "self",  # ✅ Mostrar en panel lateral
        }

    
    def button_cancel(self):
        for invoice in self:
            if invoice.gt_estado_dte == 'Cancelado' or invoice.gt_estado_dte == 'Sin enviar':
                raise UserError(
                    _("No puede cancelar esta factura porque ya esta Cancelada o no ha sido enviada y se encuentra en estado '%s'.") % invoice.gt_estado_dte
                )
        return super(AccountMove, self).button_cancel()
    
        
    def button_annul(self):
        for invoice in self:
            if invoice.gt_estado_dte != 'Completado':
                raise UserError("Solo se pueden anular facturas que estén en estado 'Completado'.")

            if not invoice.cancellation_reason:
                raise UserError("Debe proporcionar un motivo de anulación.")

            company = invoice.company_id
            nuc = company.nuc_guatemala

            if not nuc:
                raise UserError("No se ha configurado (nuc.guatemala) en la compañía.")
            if not invoice.gt_dte_auth_number:
                raise UserError("La factura no tiene número de autorización DTE.")
            if not invoice.gt_fecha_envio:
                raise UserError("La factura no tiene fecha de envío configurada.")
            if not company.partner_id.vat:
                raise UserError("La empresa no tiene configurado el NIT.")

            taxid = company.partner_id.vat
            username = nuc.user
            id_receptor = invoice.partner_id.vat or "CF"

            json_data = {
                "Taxid": taxid,
                "Autorizacion": invoice.gt_dte_auth_number,
                "IdReceptor": id_receptor,
                "FechaEmisionDocumentoAnular": invoice.gt_fecha_envio,
                "MotivoAnulacion": invoice.cancellation_reason,
                "Username": username
            }

            base_url = nuc.url_annul if company.type_env else nuc.url_annul_dev
            token = nuc.token if company.type_env else nuc.token_dev
            if not token:
                token = nuc.get_token_nuc()

            headers = {
                "Content-Type": "application/json",
                "Authorization": token
            }
     
            json_payload = json.dumps(json_data)
        
            try:
                response = requests.post(base_url, data=json_payload, headers=headers, verify=True)

              

                response.raise_for_status()

            except requests.exceptions.RequestException as e:
                mensaje_error = str(e)
                mensaje_pac = ""
                try:
                    error_json = response.json()
                    mensaje_pac = error_json.get("Mensaje", "") or response.text
                except Exception:
                    mensaje_pac = response.text

                invoice.message_post(
                    body=f"""
                     <b>Error al enviar solicitud de anulación</b><br/>
                    <b>Excepción HTTP:</b> {mensaje_error}<br/>
                    <b>Mensaje de la SAT:</b><br/><pre>{mensaje_pac}</pre>
                    """,
                    subtype_xmlid="mail.mt_note"
                )

                # Mostrar error al usuario
                raise UserError(f" Error al enviar solicitud de anulación:\n{mensaje_error}\n\n📩 Respuesta de la SAT:\n{mensaje_pac}")

            # Si todo sale bien: cancelar en Odoo
            invoice.button_cancel()
            invoice.gt_estado_dte = "Cancelado"
            invoice.message_post(body="✅ DTE anulado exitosamente ante la SAT.")
            
    def action_annul(self):
        action = self.env["ir.actions.actions"]._for_xml_id(
            "nuc_facturacion.action_view_account_move_annul")
        return action