/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { OrderSummary } from "@point_of_sale/app/screens/product_screen/order_summary/order_summary";
import { _t } from "@web/core/l10n/translation";

patch(OrderSummary.prototype, {

    setup() {
        super.setup(...arguments);

        this.laundryBarcode = useService("laundry_barcode");
        this.notification = useService("notification");
    },

    async openLaundryStatusPopup() {
        const order =
            this.pos.getOrder?.() ||
            this.pos.selectedOrder;

        const barcode =
            order?.uiState?.laundry_order_barcode ||
            "";

        if (!barcode) {
            this.notification.add(
                _t(
                    "No barcode is available for this laundry order."
                ),
                {
                    type: "warning",
                }
            );

            return;
        }

        await this.laundryBarcode.process(barcode);
    },

});
