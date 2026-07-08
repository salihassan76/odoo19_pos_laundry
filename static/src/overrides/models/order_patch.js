/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Order } from "@point_of_sale/app/store/models";

patch(Order.prototype, {
    setup() {
        super.setup(...arguments);
        this.uiState.laundry_order_id = this.uiState.laundry_order_id || false;
        this.uiState.laundry_order_name = this.uiState.laundry_order_name || "";
        this.uiState.laundry_order_type_id = this.uiState.laundry_order_type_id || false;
        this.uiState.laundry_order_type_name = this.uiState.laundry_order_type_name || "";
        this.uiState.laundry_order_type_prefix = this.uiState.laundry_order_type_prefix || "";
        this.uiState.laundry_allowed_pos_category_ids = this.uiState.laundry_allowed_pos_category_ids || [];
    },
});
