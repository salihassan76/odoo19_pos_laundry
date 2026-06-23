/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

import {
    getLivePackageDetails,
    getLiveAllowedProductIds,
    getLiveAllowedCategoryIds,
    getLiveRemainingByCategory,
    getPackageDetailForProduct,
    getPackageDetailForCategory,
    canUsePackageProduct,
    getPackageCategoryBadge,
    isPackageCategoryExhausted,
} from "./package_engine";

console.log("Laundry package store patch loaded");

patch(PosStore.prototype, {
    getPackageOrder() {
        return this.getOrder?.() || this.get_order?.();
    },

    get isPackageUsageOrder() {
        const order = this.getPackageOrder();
        return Boolean(order?.uiState?.is_package_usage);
    },

    get packageLiveDetails() {
        const order = this.getPackageOrder();

        if (!order?.uiState?.is_package_usage) {
            return [];
        }

        return getLivePackageDetails(order);
    },

    get packageAllowedProductIds() {
        const order = this.getPackageOrder();

        if (!order?.uiState?.is_package_usage) {
            return [];
        }

        return getLiveAllowedProductIds(order);
    },

    get packageAllowedCategoryIds() {
        const order = this.getPackageOrder();

        if (!order?.uiState?.is_package_usage) {
            return [];
        }

        return getLiveAllowedCategoryIds(order);
    },

    get packageRemainingByCategory() {
        const order = this.getPackageOrder();

        if (!order?.uiState?.is_package_usage) {
            return {};
        }

        return getLiveRemainingByCategory(order);
    },

    getPackageDetailForProduct(productId) {
        const order = this.getPackageOrder();

        if (!order?.uiState?.is_package_usage) {
            return false;
        }

        return getPackageDetailForProduct(order, productId);
    },

    getPackageDetailForCategory(categoryId) {
        const order = this.getPackageOrder();

        if (!order?.uiState?.is_package_usage) {
            return false;
        }

        return getPackageDetailForCategory(order, categoryId);
    },

    canUsePackageProduct(productId, qty = 1) {
        const order = this.getPackageOrder();

        if (!order?.uiState?.is_package_usage) {
            return true;
        }

        return canUsePackageProduct(order, productId, qty);
    },

    getPackageCategoryBadge(categoryId) {
        const order = this.getPackageOrder();

        if (!order?.uiState?.is_package_usage) {
            return "";
        }

        return getPackageCategoryBadge(order, categoryId);
    },

    isPackageCategoryExhausted(categoryId) {
        const order = this.getPackageOrder();

        if (!order?.uiState?.is_package_usage) {
            return false;
        }

        return isPackageCategoryExhausted(order, categoryId);
    },
});