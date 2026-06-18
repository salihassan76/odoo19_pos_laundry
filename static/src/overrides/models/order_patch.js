/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Order } from "@point_of_sale/app/store/models";

patch(Order.prototype, {
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);

        json.laundry_order_type_id = this.uiState?.laundry_order_type_id || false;
        json.package_rule_id = this.uiState?.package_rule_id || false;
        json.is_package_sell = this.uiState?.is_package_sell || false;
        json.is_package_usage = this.uiState?.is_package_usage || false;
        json.notes = this.uiState?.notes || "";

        return json;
    },
});