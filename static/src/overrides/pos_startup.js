/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    get defaultPage() {
        if (this.config?.enable_laundry_workflow) {
            return {
                page: "pos_customerscreen",
                params: {},
            };
        }

        return super.defaultPage;
    },
});
