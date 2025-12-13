/** @odoo-module */
import { OrderReceipt } from "@point_of_sale/app/screens/receipt_screen/receipt/order_receipt";
import { patch } from "@web/core/utils/patch";
import { useState, Component, xml } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

patch(OrderReceipt.prototype, {
    setup(){
        super.setup();
        this.state = useState({
            template: true,
        })
        this.pos = useState(useService("pos"));
    },
   get templateProps() {
    const currentOrder = this.pos.orders?.[0];
    return {
        data: this.props.data,
        order: this.pos.orders,
        receipt: currentOrder?.export_for_printing() || {},
        orderlines: currentOrder?.get_orderlines() || [],
        paymentlines: currentOrder?.get_paymentlines() || []
    };
},
    get templateComponent() {
        var mainRef = this;
        return class extends Component {
            setup() {}
            static template = xml`${mainRef.pos.config.design_receipt}`
        };
    },
    get isTrue() {
        if (this.env.services.pos.config.is_custom_receipt == false) {
            return true;
        }
        return false;
    }
});
