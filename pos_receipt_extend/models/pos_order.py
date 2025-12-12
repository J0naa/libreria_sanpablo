from odoo import models,api

class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _export_for_ui(self, order):
        result = super()._export_for_ui(order)

        # Asegúrate de que `account_move` esté vinculado y tenga los campos personalizados
        if order.account_move:
            result.update({
                'gt_dte_auth_number': order.account_move.gt_dte_auth_number or '',
                'gt_dte_numero': order.account_move.gt_dte_numero or '',
                'gt_dte_serie': order.account_move.gt_dte_serie or '',
                'gt_fecha_envio': order.account_move.gt_fecha_envio if order.account_move.gt_fecha_envio else '',
            })
        else:
            result.update({
                'gt_dte_auth_number': '',
                'gt_dte_numero': '',
                'gt_dte_serie': '',
                'gt_fecha_envio': '',
            })

        return result


    @api.model
    def generate_invoice_data(self, order_id):
        order = self.env["pos.order"].browse(int(order_id))
        invoice = order.account_move
        return {
            'auth_number': invoice.gt_dte_auth_number or '',
            'dte_number': invoice.gt_dte_numero or '',
            'dte_serie': invoice.gt_dte_serie or '',
            'fecha_envio': invoice.gt_fecha_envio if invoice.gt_fecha_envio else '',
        }