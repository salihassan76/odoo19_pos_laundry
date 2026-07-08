 /** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { CategorySelector } from "@point_of_sale/app/components/category_selector/category_selector";

patch(CategorySelector.prototype, {
    getLaundryCategoriesAndSub() {
        const categories = this.getCategoriesAndSub(...arguments);
        const order = this.pos.getOrder?.();

        if (!this.pos.config.enable_laundry_workflow) {
            return categories;
        }

        const allowedIds = order?.uiState?.laundry_allowed_pos_category_ids || [];

        if (!allowedIds.length) {
            return [];
        }

        return categories.filter((category) => allowedIds.includes(category.id));
    },
});