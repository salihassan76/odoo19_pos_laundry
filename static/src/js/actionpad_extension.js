/** @odoo-module **/
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

function getCurrentOrder(pos) {
    return pos.getOrder?.() || pos.get_order?.() || null;
}

function addNewOrder(pos) {
    return pos.addNewOrder?.() || pos.add_new_order?.() || null;
}

function removeOrder(pos, order) {
    if (!order) return;
    if (pos.removeOrder) {
        pos.removeOrder(order);
    } else if (pos.remove_order) {
        pos.remove_order(order);
    }
}

function getOrderLines(order) {
    const lines = order?.lines || order?.orderlines || order?.get_orderlines?.() || [];
    return Array.from(lines);
}

function getLineProduct(line) {
    return line.product_id || line.product || line.get_product?.() || null;
}

function getLineQty(line) {
    return line.qty ?? line.quantity ?? line.get_quantity?.() ?? 1;
}

function getLinePrice(line) {
    return line.price_unit ?? line.price ?? line.get_unit_price?.() ?? 0;
}

function getOrderPartner(order) {
    return order.partner_id || order.get_partner?.() || order.getPartner?.() || null;
}

patch(ActionpadWidget.prototype, {
    setup() {
        super.setup(...arguments);
        this.dialog = useService("dialog");
        this.orm = useService("orm");
    },

    async clickSaveOrder() {
        const order = getCurrentOrder(this.pos);
        if (!order) return;

        const partner = getOrderPartner(order);
        const lines = getOrderLines(order);

        const data = {
            partner_id: partner?.id || false,
            laundry_order_type_id: order.uiState?.laundry_order_type_id || false,
            package_rule_id: order.uiState?.package_rule_id || false,
            partner_package_id: order.uiState?.partner_package_id || false,
            is_package_sale: Boolean(order.uiState?.is_package_sale),
            is_package_usage: Boolean(order.uiState?.is_package_usage),
            notes: order.uiState?.notes || "",
            lines: lines.map((line) => {
                const product = getLineProduct(line);
                return {
                    product_id: product?.id || false,
                    qty: getLineQty(line),
                    price_unit: getLinePrice(line),
                };
            }).filter((line) => line.product_id),
        };

        const result = await this.orm.call(
            "laundry.order",
            "process_pos_laundry_order",
            [data]
        );

        if (result) {
            removeOrder(this.pos, order);
            addNewOrder(this.pos);
            this.pos.navigate("pos_homescreen");
        }
    },

    async cancelLaundryOrder() {
        this.dialog.add(AlertDialog, {
            title: _t("Cancel Order"),
            body: _t("Are you sure you want to cancel this order?"),
            confirmLabel: _t("Yes, Cancel"),
            confirm: () => {
                const order = getCurrentOrder(this.pos);
                removeOrder(this.pos, order);
                addNewOrder(this.pos);
                this.pos.navigate("pos_customerscreen");
            },
        });
    },
});
