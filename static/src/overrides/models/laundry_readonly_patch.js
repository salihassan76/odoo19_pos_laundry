/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { Order, Orderline } from "@point_of_sale/app/store/models";

function isLockedLaundryOrder(order) {
    const state = order?.uiState;
    return Boolean(
        state?.laundry_order_id &&
        !state?.laundry_restoring_lines &&
        state?.laundry_status?.can_edit !== true
    );
}

function lineOrder(line) {
    return line?.order_id || line?.order || line?.pos_order_id || null;
}

patch(PosStore.prototype, {
    async addLineToCurrentOrder(...args) {
        if (this.config?.enable_laundry_workflow && isLockedLaundryOrder(this.getOrder?.())) {
            console.warn("[Laundry:ReadOnly] Cannot add products to this saved order.");
            return;
        }
        return super.addLineToCurrentOrder(...args);
    },
    async addLineToOrder(...args) {
        // Odoo 19 normally receives the target order as its second argument.
        const target = args.find((arg) => arg?.uiState?.laundry_order_id);
        if (this.config?.enable_laundry_workflow && isLockedLaundryOrder(target)) {
            console.warn("[Laundry:ReadOnly] Cannot add products to this saved order.");
            return;
        }
        return super.addLineToOrder(...args);
    },
});

patch(Orderline.prototype, {
    setQuantity(...args) {
        if (isLockedLaundryOrder(lineOrder(this))) return;
        return super.setQuantity(...args);
    },
    setUnitPrice(...args) {
        if (isLockedLaundryOrder(lineOrder(this))) return;
        return super.setUnitPrice(...args);
    },
    setDiscount(...args) {
        if (isLockedLaundryOrder(lineOrder(this))) return;
        return super.setDiscount(...args);
    },
});

patch(Order.prototype, {
    removeOrderline(...args) {
        if (isLockedLaundryOrder(this)) return;
        return super.removeOrderline(...args);
    },
});
