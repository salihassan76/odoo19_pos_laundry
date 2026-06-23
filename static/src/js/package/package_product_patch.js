/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { getLiveAllowedProductIds } from "./package_engine";

console.log("Laundry package product patch loaded");

patch(PosStore.prototype, {
    get productToDisplayByCateg() {
        const result = super.productToDisplayByCateg;
        const order = this.getOrder?.() || this.get_order?.();

        const isPackageUsage =
            order?.uiState?.is_package_usage || order?.is_package_usage || false;

        const orderTypeAllowedCategories =
            order?.uiState?.laundry_allowed_pos_category_ids || [];

        const selectedCategory = this.selectedCategory;
        const selectedCategoryIds = selectedCategory
            ? selectedCategory.getAllChildren().map((cat) => cat.id)
            : [];

        return result
            .map(([category, products]) => {
                const filteredProducts = products.filter((product) => {
                    const productCatIds =
                        product.pos_categ_ids?.map((c) => c.id || c) || [];

                    const allowedBySelectedCategory =
                        !selectedCategoryIds.length ||
                        productCatIds.some((id) =>
                            selectedCategoryIds.includes(id)
                        );

                    if (!allowedBySelectedCategory) {
                        return false;
                    }

                    if (isPackageUsage) {
                        const liveAllowedProductIds =
                            getLiveAllowedProductIds(order) || [];

                        const fallbackAllowedProductIds =
                            order?.uiState?.allowed_package_products ||
                            order?.allowed_package_products ||
                            [];

                        const allowedProductIds = liveAllowedProductIds.length
                            ? liveAllowedProductIds
                            : fallbackAllowedProductIds;

                        return allowedProductIds.includes(product.id);
                    }

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