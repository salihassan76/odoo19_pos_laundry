/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

console.log("Laundry productToDisplayByCateg patch loaded");

patch(PosStore.prototype, {
    get productToDisplayByCateg() {
        const result = super.productToDisplayByCateg;

        const order = this.getOrder?.();

        const orderTypeAllowedCategories =
            order?.uiState?.laundry_allowed_pos_category_ids || [];

        const packageAllowedProducts =
            order?.uiState?.allowed_package_products || [];

        const packageAllowedCategories =
            order?.uiState?.allowed_package_categories || [];

        const isPackageUsage =
            order?.uiState?.is_package_usage || false;

        return result
            .map(([category, products]) => {
                const filteredProducts = products.filter((product) => {
                    const productCatIds =
                        product.pos_categ_ids?.map((c) => c.id || c) || [];

                    // Package usage: strict product restriction
                    if (isPackageUsage && packageAllowedProducts.length) {
                        return packageAllowedProducts.includes(product.id);
                    }

                    // Package usage fallback: category restriction
                    if (isPackageUsage && packageAllowedCategories.length) {
                        return productCatIds.some((id) =>
                            packageAllowedCategories.includes(id)
                        );
                    }

                    // Normal laundry order type restriction
                    if (orderTypeAllowedCategories.length) {
                        return productCatIds.some((id) =>
                            orderTypeAllowedCategories.includes(id)
                        );
                    }

                    return true;
                });

                return [category, filteredProducts];
            })
            .filter(([category, products]) => products.length > 0);
    },
});