/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

console.log("Laundry ProductScreen category patch loaded");

patch(ProductScreen.prototype, {
    get laundryAllowedCategories() {
        const order = this.pos.get_order
            ? this.pos.get_order()
            : this.pos.getOrder?.();

        const allowedIds = order?.uiState?.laundry_allowed_pos_category_ids || [];

        let categories = [];

        try {
            categories = this.pos.models["pos.category"].getAll();
        } catch (e) {
            categories = [];
        }

        if (!allowedIds.length) {
            return categories;
        }

        return categories.filter((cat) => allowedIds.includes(cat.id));
    },

    selectLaundryCategory(category) {
        if (this.pos.setSelectedCategoryId) {
            this.pos.setSelectedCategoryId(category.id);
        } else {
            this.pos.selectedCategoryId = category.id;
        }
    },
});