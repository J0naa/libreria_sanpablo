/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Order } from "@point_of_sale/app/store/models";

patch(Order.prototype, {
    setup() {
        super.setup(...arguments);
        this.invoice_data = this.invoice_data || {};
    },

    set_invoice_data(data) {
        this.invoice_data = data || {};
    },

    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.invoice_data = this.invoice_data || {};
        return json;
    },

    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.invoice_data = json.invoice_data || {};
    },

    export_for_printing() {
        const result = super.export_for_printing(...arguments);
        result.invoice_data = this.invoice_data || {};
        return result;
    },
});
