/** @odoo-module **/
import { ActionpadWidget } from "@point_of_sale/app/screens/product_screen/action_pad/action_pad";
import { patch } from "@web/core/utils/patch";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

patch(ActionpadWidget.prototype, {
    setup() {
        super.setup(...arguments);
        this.dialog = useService("dialog");
    },

    async clickSaveOrder() {
        this.dialog.add(AlertDialog, {
            title: _t("Save Order"),
            body: _t("This action was triggered by your custom button!"),
        });
    },
    async cancelLaundryOrder() {
        this.dialog.add(AlertDialog, {
            title: _t("Cancel Order"),
            body: _t("Are you sure you want to cancel this order?"),
            confirmLabel: _t("Yes, Cancel"),
            confirm: () => {
                const order = this.pos.get_order
                    ? this.pos.get_order()
                    : this.pos.getOrder();

                if (order) {
                    if (this.pos.removeOrder) {
                        this.pos.removeOrder(order);
                    } else if (this.pos.remove_order) {
                        this.pos.remove_order(order);
                    }
                }

                if (this.pos.addNewOrder) {
                    this.pos.addNewOrder();
                } else if (this.pos.add_new_order) {
                    this.pos.add_new_order();
                }

                this.pos.navigate("pos_customerscreen");
            },
        });
    },
});