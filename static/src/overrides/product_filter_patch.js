/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import {
    getLaundryVisibility,
    getProductCategoryIds,
    laundryLog,
    laundryWarn,
} from "@pos_laundry/app/utils/laundry_visibility";

function filterProductArray(products, visibility) {
    const categoryIds = new Set(visibility.allowedCategoryIds);
    const packageProductIds = new Set(visibility.allowedPackageProductIds);

    return products.filter((product) => {
        const productCategoryIds = getProductCategoryIds(product);
        const categoryAllowed = productCategoryIds.some((id) => categoryIds.has(id));

        if (!categoryAllowed) {
            return false;
        }

        if (visibility.isPackageUsage) {
            return packageProductIds.has(Number(product.id));
        }

        return true;
    });
}

patch(PosStore.prototype, {
    get productToDisplayByCateg() {
        const nativeResult = super.productToDisplayByCateg;

        if (!this.config?.enable_laundry_workflow) {
            return nativeResult;
        }

        const visibility = getLaundryVisibility(this);

        if (!visibility.order || !visibility.allowedCategoryIds.length) {
            laundryWarn("Products", "Missing active order or allowed categories; returning no products.", visibility);
            return [];
        }

        if (visibility.isPackageUsage && !visibility.allowedPackageProductIds.length) {
            laundryWarn("Products", "Package usage has no allowed package products; returning no products.", visibility);
            return [];
        }

        if (!Array.isArray(nativeResult)) {
            laundryWarn("Products", "Unexpected native product result type; returning it unchanged.", {
                type: typeof nativeResult,
                nativeResult,
            });
            return nativeResult;
        }

        let result;

        // Odoo variants may return either products[] or [category, products][] groups.
        const isGrouped = nativeResult.every(
            (entry) => Array.isArray(entry) && entry.length >= 2 && Array.isArray(entry[1])
        );

        if (isGrouped) {
            result = nativeResult
                .map(([category, products, ...rest]) => [
                    category,
                    filterProductArray(products, visibility),
                    ...rest,
                ])
                .filter(([, products]) => products.length > 0);
        } else {
            result = filterProductArray(nativeResult, visibility);
        }

        const sampleProduct = isGrouped ? nativeResult?.[0]?.[1]?.[0] : nativeResult?.[0];

        laundryLog("Products", "filter result", {
            orderUuid: visibility.orderUuid,
            laundryOrderId: visibility.laundryOrderId,
            allowedCategoryIds: visibility.allowedCategoryIds,
            isPackageUsage: visibility.isPackageUsage,
            allowedPackageProductIds: visibility.allowedPackageProductIds,
            nativeShape: isGrouped ? "grouped" : "flat",
            inputCount: isGrouped
                ? nativeResult.reduce((total, [, products]) => total + products.length, 0)
                : nativeResult.length,
            outputCount: isGrouped
                ? result.reduce((total, [, products]) => total + products.length, 0)
                : result.length,
            sampleProductCategoryIds: sampleProduct ? getProductCategoryIds(sampleProduct) : [],
            sampleProduct,
        });

        return result;
    },
});
