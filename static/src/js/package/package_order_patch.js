/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

console.log("Laundry package order patch loaded");

function touchPackageState(order) {
    if (!order?.uiState?.is_package_usage) {
        return;
    }

    order.uiState.package_refresh_key =
        (order.uiState.package_refresh_key || 0) + 1;
}

patch(PosStore.prototype, {
    refreshPackageState() {
        const order = this.getOrder?.() || this.get_order?.();
        touchPackageState(order);
    },

    async addProductToCurrentOrder(product, options = {}) {
        const result = await super.addProductToCurrentOrder(product, options);

        const order = this.getOrder?.() || this.get_order?.();
        touchPackageState(order);

        return result;
    },

    async removeOrderline(line) {
        const result = await super.removeOrderline?.(...arguments);

        const order = this.getOrder?.() || this.get_order?.();
        touchPackageState(order);

        return result;
    },

    async deleteLine(line) {
        const result = await super.deleteLine?.(...arguments);

        const order = this.getOrder?.() || this.get_order?.();
        touchPackageState(order);

        return result;
    },
});