from odoo import models, api
import logging

_logger = logging.getLogger(__name__)

class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def invoice_data(self, order):
        """
        Devuelve los datos FEL Guatemala para el POS.
        MISMA estructura que tu invoice_data original.
        """
        data = {}
        try:
            pos_order = self.env['pos.order'].search(
                [('pos_reference', '=', order)], limit=1
            )
            invoice = pos_order.account_move

            # Si la factura existe, devolver datos FEL
            if invoice:
                data['auth_number'] = invoice.gt_dte_auth_number or ''
                data['dte_number'] = invoice.gt_dte_numero or ''
                data['dte_serie'] = invoice.gt_dte_serie or ''
                data['fecha_envio'] = invoice.gt_fecha_envio or ''

                # Datos del cliente
                data['client_name'] = pos_order.partner_id.name or ''
                data['client_vat'] = pos_order.partner_id.vat or ''

            else:
                # Si no hay factura todavía
                data = {
                    'auth_number': '',
                    'dte_number': '',
                    'dte_serie': '',
                    'fecha_envio': '',
                    'client_name': pos_order.partner_id.name or '',
                    'client_vat': pos_order.partner_id.vat or '',
                }

        except Exception as e:
            _logger.error("Error generando invoice_data FEL: %s", e)
            data = False

        return data
