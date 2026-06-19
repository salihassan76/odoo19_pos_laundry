/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { CategorySelector } from "@point_of_sale/app/screens/product_screen/category_selector/category_selector";

console.log("Laundry CategorySelector patch loaded");

patch(CategorySelector.prototype, {
    setup() {
        super.setup?.(...arguments);
        this.pos = usePos();
    },

    get laundryCategories() {
        const categories = this.props.categories || [];

        const order = this.pos.get_order
            ? this.pos.get_order()
            : this.pos.getOrder?.();

        const allowedIds = order?.laundry_allowed_pos_category_ids || [];

        console.log("CategorySelector allowedIds:", allowedIds);
        console.log("Original categories:", categories);

        if (!allowedIds.length) {
            return categories;
        }

        return categories.filter((cat) => allowedIds.includes(cat.id));
    },
});