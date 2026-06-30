/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { CategorySelector } from "@point_of_sale/app/components/category_selector/category_selector";

console.log("Laundry native CategorySelector patch loaded");

patch(CategorySelector.prototype, {
    getCategoriesAndSub() {
        const categories = super.getCategoriesAndSub(...arguments);
        return this._filterCategoriesWithVisibleProducts(categories);
    },

    getLaundryCategoriesAndSub() {
        const categories = super.getCategoriesAndSub(...arguments);
        return this._filterCategoriesWithVisibleProducts(categories);
    },

    _filterCategoriesWithVisibleProducts(categories) {
        const order = this.pos.getOrder?.() || this.pos.get_order?.();

        const orderTypeAllowedCategories =
            order?.uiState?.laundry_allowed_pos_category_ids || [];

        const packageAllowedProducts =
            order?.uiState?.allowed_package_products || [];

        const packageAllowedCategories =
            order?.uiState?.allowed_package_categories || [];

        const isPackageUsage =
            order?.uiState?.is_package_usage || false;

        if (
            !isPackageUsage &&
            !orderTypeAllowedCategories.length
        ) {
            return categories;
        }

        const realCategories = this.pos.models["pos.category"];

        return categories.filter((category) => {
            const categoryId = category?.id;

            if (!categoryId) {
                return false;
            }

            const realCategory = realCategories.get(categoryId);

            if (!realCategory) {
                return false;
            }

            const products = realCategory.associatedProducts || [];

            const visibleProducts = products.filter((product) => {
                const productCatIds =
                    product.pos_categ_ids?.map((c) => c.id || c) || [];

                if (isPackageUsage && packageAllowedProducts.length) {
                    return packageAllowedProducts.includes(product.id);
                }

                if (isPackageUsage && packageAllowedCategories.length) {
                    return productCatIds.some((id) =>
                        packageAllowedCategories.includes(id)
                    );
                }

                if (orderTypeAllowedCategories.length) {
                    return productCatIds.some((id) =>
                        orderTypeAllowedCategories.includes(id)
                    );
                }

                return true;
            });

            return visibleProducts.length > 0;
        });
    },
});