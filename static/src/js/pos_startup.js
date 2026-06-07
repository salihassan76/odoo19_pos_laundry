/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);

        console.log("Opening laundry home screen");

        setTimeout(() => {
            this.navigate("pos_customerscreen");
        }, 1000);
    },
});