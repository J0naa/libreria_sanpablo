/** @odoo-module */

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/store/pos_hook";

patch(PaymentScreen.prototype, {
      setup() {
        super.setup();
        this.orm = useService("orm");
        this.pos = usePos();
      },
    async validateOrder(isForceValidate) {
//    extending  the validate order to add the below fields
        let receipt_order = await super.validateOrder(arguments);
        var receipt_number = this.pos.selectedOrder.name;
        var orders = this.env.services.pos.selectedOrder;

        const data = this.env.services.pos.session_orders;
        var length = data.length-1;
        var order = data[length];
 
    

       
        
       
      
        return receipt_order;
    },
});


/** @odoo-module **/

import { useState } from "@odoo/owl";
import { ReceiptHeader } from "@point_of_sale/app/screens/receipt_screen/receipt/receipt_header/receipt_header";



patch(ReceiptHeader.prototype, {
    async setup() {
        super.setup();
        this.state = useState({
            invoiceData: {}, // guardamos los 4 campos aquí
        });
        this.pos = usePos();
        this.orm = useService("orm");

        if (this.pos.orders.length && this.pos.orders[0].to_invoice && this.pos.orders[0].server_id) {
            const data = await this.orm.call("pos.order", "generate_invoice_data", [this.pos.orders[0].server_id]);
            this.state.invoiceData = data;
        }
    },
});