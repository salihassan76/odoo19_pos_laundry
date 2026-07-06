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

function goToScreen(pos, screenName) {
    if (pos.showScreen) {
        pos.showScreen(screenName);
    } else if (pos.navigate) {
        pos.navigate(screenName);
    }
}

patch(ActionpadWidget.prototype, {
    setup() {
        super.setup(...arguments);
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        this.printer = useService("printer");
        this.laundry = useService("laundry");
    },
    async clickSaveOrder() {
        if (!this.laundry.isEnabled()) {
            return;
        }

        try {
            await this.laundry.saveAndHandleResult();
        } catch (error) {
            this.dialog.add(AlertDialog, {
                title: _t("Save Laundry Order"),
                body: error.message || _t("Could not save laundry order."),
            });
        }
    },

    async cancelLaundryOrder() {
        this.dialog.add(AlertDialog, {
            title: _t("Cancel Order"),
            body: _t("Are you sure you want to cancel this order?"),
            confirmLabel: _t("Yes, Cancel"),
            confirm: () => {
                this.laundry.cancelOrder();
            },
        });
    },
    async clickPayLaundryOrder() {
        try {
            await this.laundry.payLaundryOrder();
        } catch (error) {
            this.dialog.add(AlertDialog, {
                title: _t("Laundry Order Payment"),
                body: error.message || _t("Could not pay laundry order."),
            });
        }
    },
    async clickPrintLaundryOrder() {
        const order = this.pos.getOrder();

        const laundryOrderId = order?.uiState?.laundry_order_id;
        if (!laundryOrderId) {
            return;
        }

        const result = await this.orm.call(
            "laundry.order",
            "action_create_invoice",
            [[laundryOrderId]]
        );

        console.log(result);
    },
});
