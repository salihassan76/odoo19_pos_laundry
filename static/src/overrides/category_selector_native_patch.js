/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { CategorySelector } from "@point_of_sale/app/components/category_selector/category_selector";
import {
    getLaundryVisibility,
    laundryLog,
    laundryWarn,
    normalizeIds,
} from "@pos_laundry/app/utils/laundry_visibility";

function getCategoryModel(pos) {
    return pos.models?.["pos.category"] || pos.data?.models?.["pos.category"] || null;
}

function getCategoryRecord(pos, categoryId) {
    const model = getCategoryModel(pos);
    return (
        model?.get?.(categoryId) ||
        model?.getAll?.()?.find((category) => Number(category.id) === Number(categoryId)) ||
        null
    );
}

patch(CategorySelector.prototype, {
    getLaundryCategoriesAndSub() {
        const categories = this.getCategoriesAndSub(...arguments);

        if (!this.pos.config?.enable_laundry_workflow) {
            return categories;
        }

        const visibility = getLaundryVisibility(this.pos);

        if (!visibility.order) {
            laundryWarn("Categories", "No active order; returning an empty category list.");
            return [];
        }

        if (!visibility.allowedCategoryIds.length) {
            laundryWarn("Categories", "No allowed categories on the active laundry order.", {
                orderUuid: visibility.orderUuid,
                laundryOrderId: visibility.laundryOrderId,
                orderTypeId: visibility.orderTypeId,
                uiState: visibility.order.uiState,
            });
            return [];
        }

        const visibleIds = new Set(visibility.allowedCategoryIds);

        for (const categoryId of visibility.allowedCategoryIds) {
            const category = getCategoryRecord(this.pos, categoryId);
            for (const parent of category?.allParents || []) {
                visibleIds.add(Number(parent.id));
            }
        }

        const result = categories.filter((category) => visibleIds.has(Number(category.id)));

        laundryLog("Categories", "filter result", {
            orderUuid: visibility.orderUuid,
            laundryOrderId: visibility.laundryOrderId,
            allowedCategoryIds: visibility.allowedCategoryIds,
            visibleCategoryIds: normalizeIds([...visibleIds]),
            incoming: categories.map((category) => ({ id: category.id, name: category.name })),
            outgoing: result.map((category) => ({ id: category.id, name: category.name })),
        });

        return result;
    },
});
