/** @odoo-module **/

import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { patch } from "@web/core/utils/patch";

patch(PaymentScreen.prototype, {
    async validateOrder(isForceValidate) {
        const order = this.currentOrder;
        const returnHome = order?.uiState?.return_to_laundry_home;

        await super.validateOrder(...arguments);

        if (returnHome) {
            this.pos.navigate("pos_homescreen");
        }
    },

    async back() {
        const order = this.currentOrder;

        if (order?.uiState?.return_to_laundry_home) {
            this.pos.navigate("pos_homescreen");
            return;
        }

        return super.back?.(...arguments);
    },
});