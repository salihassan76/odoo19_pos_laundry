/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { CategorySelector } from "@point_of_sale/app/components/category_selector/category_selector";

console.log("Laundry native CategorySelector patch loaded");

patch(CategorySelector.prototype, {
    getLaundryCategoriesAndSub() {
        const categories = this.getCategoriesAndSub();

        const order = this.pos.get_order
            ? this.pos.get_order()
            : this.pos.getOrder?.();

        const allowedIds = order?.uiState?.laundry_allowed_pos_category_ids || [];

        if (!allowedIds.length) {
            return categories;
        }

        return categories.filter((category) => allowedIds.includes(category.id));
    },
});