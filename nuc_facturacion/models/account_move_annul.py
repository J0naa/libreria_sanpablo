# -*- coding: utf-8 -*-
from odoo import models, fields
from odoo.tools.translate import _


class AccountMoveAnnul(models.TransientModel):
    """
    Account move Annul wizard.
    """
    _name = 'account.move.annul'
    _description = 'Account Move Annul'
    _check_company_auto = True

    
    name = fields.Char(string='Reason')

    def annul_moves(self):
        self.ensure_one()
        moves_id = self._context.get('active_ids')
        invoices_id = self.env['account.move'].browse(moves_id)
        invoices_id
        invoices_id.update({
            'cancellation_reason': self.name or "Anulacion de factura Electronica"
        })
        invoices_id.button_annul()
        return {'type': 'ir.actions.act_window_close'}

