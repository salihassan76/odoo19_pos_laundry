

/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { Order } from "@point_of_sale/app/store/models";

patch(Order.prototype, {
    setup() {
        super.setup(...arguments);

        this.uiState.is_package_usage = this.uiState.is_package_usage || false;
        this.uiState.partner_package_id = this.uiState.partner_package_id || false;
        this.uiState.package_rule_id = this.uiState.package_rule_id || false;
        this.uiState.package_rule_name = this.uiState.package_rule_name || "";

        this.uiState.allowed_package_products = this.uiState.allowed_package_products || [];
        this.uiState.allowed_package_categories = this.uiState.allowed_package_categories || [];
    },
});