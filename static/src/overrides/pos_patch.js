/** @odoo-module **/

import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";

patch(PosStore.prototype, {
    onClickBackButton() {
        const order = this.getOrder?.() || this.get_order?.();

        if (order?.uiState?.return_to_laundry_home) {
            this.navigate("pos_homescreen");
            return;
        }

        return super.onClickBackButton?.(...arguments);
    },
});