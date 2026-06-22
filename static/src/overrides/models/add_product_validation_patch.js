/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

patch(PosStore.prototype, {
    async addProductToCurrentOrder(product, options = {}) {
        const order = this.getOrder();
        const allowed = order?.uiState?.allowed_package_products || [];

        if (order?.uiState?.is_package_usage && allowed.length) {
            if (!allowed.includes(product.id)) {
                this.dialog.add(AlertDialog, {
                    title: _t("Product Not Allowed"),
                    body: _t("This product is not included in the selected package."),
                });
                return;
            }
        }

        return await super.addProductToCurrentOrder(product, options);
    },
});