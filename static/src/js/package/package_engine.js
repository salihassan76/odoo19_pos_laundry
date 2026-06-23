/** @odoo-module **/

export function getOrderLines(order) {
    return order?.lines || order?.orderlines || [];
}

export function getLineProductId(line) {
    const product = line.product_id || line.product;
    return product?.id || false;
}

export function getLineQty(line) {
    if (typeof line.get_quantity === "function") {
        return line.get_quantity();
    }

    return line.qty || line.quantity || 0;
}

export function getLivePackageDetails(order) {
    const details = order?.uiState?.package_details || [];
    const lines = getOrderLines(order);

    return details.map((detail) => {
        let currentOrderQty = 0;

        for (const line of lines) {
            const productId = getLineProductId(line);

            if (!productId) {
                continue;
            }

            if ((detail.product_ids || []).includes(productId)) {
                currentOrderQty += getLineQty(line);
            }
        }

        const dbRemaining = detail.remaining_qty ?? detail.allowed_qty ?? 0;
        const liveRemaining = dbRemaining - currentOrderQty;

        return {
            ...detail,
            current_order_qty: currentOrderQty,
            live_remaining_qty: liveRemaining > 0 ? liveRemaining : 0,
            is_exhausted: liveRemaining <= 0,
        };
    });
}

export function getLiveAllowedProductIds(order) {
    return getLivePackageDetails(order)
        .filter((detail) => detail.live_remaining_qty > 0)
        .flatMap((detail) => detail.product_ids || []);
}

export function getLiveAllowedCategoryIds(order) {
    return getLivePackageDetails(order)
        .filter((detail) => detail.live_remaining_qty > 0)
        .map((detail) => detail.category_id)
        .filter(Boolean);
}

export function getLiveRemainingByCategory(order) {
    const result = {};

    for (const detail of getLivePackageDetails(order)) {
        if (!detail.category_id) {
            continue;
        }

        result[detail.category_id] = detail.live_remaining_qty;
    }

    return result;
}

export function getPackageDetailForProduct(order, productId) {
    return getLivePackageDetails(order).find((detail) =>
        (detail.product_ids || []).includes(productId)
    );
}

export function getPackageDetailForCategory(order, categoryId) {
    return getLivePackageDetails(order).find(
        (detail) => detail.category_id === categoryId
    );
}

export function canUsePackageProduct(order, productId, qty = 1) {
    const detail = getPackageDetailForProduct(order, productId);

    if (!detail) {
        return false;
    }

    return detail.live_remaining_qty >= qty;
}

export function getPackageCategoryBadge(order, categoryId) {
    const detail = getPackageDetailForCategory(order, categoryId);

    if (!detail) {
        return "";
    }

    return String(detail.live_remaining_qty);
}

export function isPackageCategoryExhausted(order, categoryId) {
    const detail = getPackageDetailForCategory(order, categoryId);

    if (!detail) {
        return false;
    }

    return detail.live_remaining_qty <= 0;
}