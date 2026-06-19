/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

console.log("Laundry productToDisplayByCateg patch loaded");

patch(PosStore.prototype, {
    get productToDisplayByCateg() {
        const result = super.productToDisplayByCateg;

        const order = this.getOrder?.();
        const allowedIds =
            order?.uiState?.laundry_allowed_pos_category_ids || [];

        if (!allowedIds.length) {
            return result;
        }

        return result
            .map(([category, products]) => {
                const filteredProducts = products.filter((product) => {
                    const productCatIds =
                        product.pos_categ_ids?.map((c) => c.id || c) || [];

                    return productCatIds.some((id) =>
                        allowedIds.includes(id)
                    );
                });

                return [category, filteredProducts];
            })
            .filter(([category, products]) => products.length > 0);
    },
});