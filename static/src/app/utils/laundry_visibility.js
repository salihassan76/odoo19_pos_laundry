/** @odoo-module **/

const DEBUG_KEY = "pos_laundry_debug";

export function isLaundryDebugEnabled() {
    try {
        const stored = globalThis?.localStorage?.getItem(DEBUG_KEY);
        if (stored === null) {
            return true;
        }
        return stored !== "0" && stored !== "false";
    } catch {
        return true;
    }
}

export function setLaundryDebugEnabled(enabled) {
    try {
        globalThis?.localStorage?.setItem(DEBUG_KEY, enabled ? "1" : "0");
    } catch {
        // Ignore storage errors in restricted browser contexts.
    }
}

export function laundryLog(scope, message, data = undefined) {
    if (!isLaundryDebugEnabled()) {
        return;
    }
    const prefix = `[Laundry:${scope}]`;
    if (data === undefined) {
        console.log(prefix, message);
    } else {
        console.log(prefix, message, data);
    }
}

export function laundryWarn(scope, message, data = undefined) {
    if (!isLaundryDebugEnabled()) {
        return;
    }
    const prefix = `[Laundry:${scope}]`;
    if (data === undefined) {
        console.warn(prefix, message);
    } else {
        console.warn(prefix, message, data);
    }
}

export function normalizeIds(values = []) {
    const list = Array.isArray(values) ? values : [values];
    return [...new Set(
        list
            .map((value) => {
                if (typeof value === "number") {
                    return value;
                }
                if (typeof value === "string") {
                    return Number(value);
                }
                if (Array.isArray(value)) {
                    return Number(value[0]);
                }
                return Number(value?.id);
            })
            .filter((value) => Number.isInteger(value) && value > 0)
    )];
}

export function getCurrentOrder(pos) {
    return pos?.getOrder?.() || pos?.get_order?.() || null;
}

export function setLaundryVisibility(order, values = {}) {
    if (!order) {
        return null;
    }
    order.uiState = order.uiState || {};

    const allowedCategoryIds = normalizeIds(
        values.allowedCategoryIds ??
        values.allowed_category_ids ??
        values.laundry_allowed_pos_category_ids ??
        order.uiState.laundry_allowed_pos_category_ids ??
        []
    );

    const allowedPackageProductIds = normalizeIds(
        values.allowedPackageProductIds ??
        values.allowed_package_product_ids ??
        values.allowed_package_products ??
        order.uiState.allowed_package_products ??
        []
    );

    order.uiState.laundry_visibility = {
        orderTypeId:
            values.orderTypeId ??
            values.laundry_order_type_id ??
            order.uiState.laundry_order_type_id ??
            false,
        allowedCategoryIds,
        isPackageUsage: Boolean(
            values.isPackageUsage ??
            values.is_package_usage ??
            order.uiState.is_package_usage ??
            false
        ),
        allowedPackageProductIds,
    };

    return order.uiState.laundry_visibility;
}

export function getLaundryVisibility(pos) {
    const order = getCurrentOrder(pos);
    const state = order?.uiState?.laundry_visibility || {};

    return {
        order,
        orderUuid: order?.uuid || false,
        laundryOrderId: order?.uiState?.laundry_order_id || false,
        orderTypeId:
            state.orderTypeId ??
            order?.uiState?.laundry_order_type_id ??
            false,
        allowedCategoryIds: normalizeIds(
            state.allowedCategoryIds ??
            order?.uiState?.laundry_allowed_pos_category_ids ??
            []
        ),
        isPackageUsage: Boolean(
            state.isPackageUsage ??
            order?.uiState?.is_package_usage ??
            false
        ),
        allowedPackageProductIds: normalizeIds(
            state.allowedPackageProductIds ??
            order?.uiState?.allowed_package_products ??
            []
        ),
    };
}

export function getProductCategoryIds(product) {
    const values = [];

    const append = (value) => {
        if (value === undefined || value === null || value === false) {
            return;
        }
        if (Array.isArray(value)) {
            values.push(...value);
        } else {
            values.push(value);
        }
    };

    append(product?.pos_categ_ids);
    append(product?.pos_category_ids);
    append(product?.pos_categ_id);
    append(product?.pos_category_id);

    const template = product?.product_tmpl_id;
    if (template && typeof template === "object" && !Array.isArray(template)) {
        append(template.pos_categ_ids);
        append(template.pos_category_ids);
        append(template.pos_categ_id);
        append(template.pos_category_id);
    }

    return normalizeIds(values);
}

export function traceLaundryState(scope, pos, extra = {}) {
    const visibility = getLaundryVisibility(pos);
    laundryLog(scope, "state", {
        orderUuid: visibility.orderUuid,
        laundryOrderId: visibility.laundryOrderId,
        orderTypeId: visibility.orderTypeId,
        allowedCategoryIds: visibility.allowedCategoryIds,
        isPackageUsage: visibility.isPackageUsage,
        allowedPackageProductIds: visibility.allowedPackageProductIds,
        ...extra,
    });
    return visibility;
}

try {
    globalThis.LaundryDebug = {
        enable: () => setLaundryDebugEnabled(true),
        disable: () => setLaundryDebugEnabled(false),
        state: (pos) => traceLaundryState("Debug", pos),
    };
} catch {
    // Browser global is optional.
}
