/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

import {
    getPackageDetailForProduct,
    canUsePackageProduct,
} from "./package_engine";

console.log("Laundry package validation patch loaded");

patch(PosStore.prototype, {
    async addProductToCurrentOrder(product, options = {}) {
        const order = this.getOrder?.() || this.get_order?.();

        if (!order?.uiState?.is_package_usage) {
            return await super.addProductToCurrentOrder(product, options);
        }

        const productId = product?.id;
        const detail = getPackageDetailForProduct(order, productId);

        if (!detail) {
            this.dialog.add(AlertDialog, {
                title: _t("Product Not Allowed"),
                body: _t("This product is not included in the selected package."),
            });
            return;
        }

        const qty = options?.quantity || 1;

        if (!canUsePackageProduct(order, productId, qty)) {
            this.dialog.add(AlertDialog, {
                title: _t("Package Balance Exceeded"),
                body: _t(
                    "No remaining quantity is available for this package category."
                ),
            });
            return;
        }

        return await super.addProductToCurrentOrder(product, options);
    },
});