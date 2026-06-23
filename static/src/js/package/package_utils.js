/** @odoo-module **/

export function toArray(value) {
    return Array.isArray(value) ? value : [];
}

export function toId(value) {
    if (!value) {
        return false;
    }

    if (typeof value === "object") {
        return value.id || value[0] || false;
    }

    return value;
}

export function uniqueIds(ids) {
    return [...new Set((ids || []).filter(Boolean))];
}

export function productBelongsToDetail(detail, productId) {
    return toArray(detail.product_ids).includes(productId);
}

export function categoryBelongsToDetail(detail, categoryId) {
    return detail.category_id === categoryId;
}

export function findDetailByProduct(details, productId) {
    return toArray(details).find((detail) =>
        productBelongsToDetail(detail, productId)
    );
}

export function findDetailByCategory(details, categoryId) {
    return toArray(details).find((detail) =>
        categoryBelongsToDetail(detail, categoryId)
    );
}

export function getProductCategoryIds(product) {
    return toArray(product?.pos_categ_ids).map((cat) => toId(cat)).filter(Boolean);
}

export function sumLineQty(lines, productIds) {
    const allowedProducts = toArray(productIds);
    let total = 0;

    for (const line of toArray(lines)) {
        const product = line.product_id || line.product;
        const productId = toId(product);

        if (!allowedProducts.includes(productId)) {
            continue;
        }

        if (typeof line.get_quantity === "function") {
            total += line.get_quantity();
        } else {
            total += line.qty || line.quantity || 0;
        }
    }

    return total;
}

export function normalizePackageDetail(detail) {
    return {
        detail_id: detail.detail_id || detail.id || false,
        category_id: detail.category_id || false,
        category_name: detail.category_name || "",
        product_ids: uniqueIds(detail.product_ids || []),
        allowed_qty: detail.allowed_qty || 0,
        used_qty: detail.used_qty || 0,
        remaining_qty: detail.remaining_qty ?? detail.allowed_qty ?? 0,
    };
}

export function normalizePackageDetails(details) {
    return toArray(details).map((detail) => normalizePackageDetail(detail));
}