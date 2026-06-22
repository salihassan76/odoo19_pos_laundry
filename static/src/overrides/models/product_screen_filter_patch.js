/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

patch(ProductScreen.prototype, {
    get productsToDisplay() {
        let products = super.productsToDisplay;

        const order = this.pos.getOrder();
        const allowed = order?.uiState?.allowed_package_products || [];

        if (!order?.uiState?.is_package_usage || !allowed.length) {
            return products;
        }

        return products.filter((product) => allowed.includes(product.id));
    },
});