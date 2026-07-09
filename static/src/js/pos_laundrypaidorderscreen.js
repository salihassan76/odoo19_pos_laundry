/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class PosLaundryPaidOrderScreen extends Component {
    static template = "pos_laundry.PosLaundryPaidOrderScreen";
    static props = ["*"];

    setup() {
        this.pos = useService("pos");
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.notification = useService("notification");

        this.state = useState({
            loading: true,
            order: {},
            lines: [],
        });

        onWillStart(async () => {
            await this.loadOrder();
        });
    }

    get laundryOrderId() {
        return (
            this.props?.laundryOrderId ||
            this.pos.selected_laundry_order_id ||
            false
        );
    }

    async loadOrder() {
        if (!this.laundryOrderId) {
            this.notification.add(_t("Laundry order not found."), {
                type: "danger",
            });
            return;
        }

        try {
            const result = await this.orm.call(
                "laundry.order",
                "get_paid_order_details_for_pos",
                [this.laundryOrderId]
            );

            this.state.order = result.order || {};
            this.state.lines = result.lines || [];
        } catch (error) {
            console.error(error);

            this.notification.add(
                _t("Unable to load order."),
                { type: "danger" }
            );
        } finally {
            this.state.loading = false;
        }
    }

    back() {
        this.pos.showScreen("LaundryHomeScreen");
    }

    async printReceipt() {
        try {
            await this.pos.printSavedLaundryOrder(this.laundryOrderId);
        } catch (error) {
            console.error(error);
        }
    }

    async refundOrder() {
        const confirmed = window.confirm(
            _t(
                "Refund this order?\n\nA refund payment and cancellation will be created."
            )
        );

        if (!confirmed) {
            return;
        }

        try {
            await this.orm.call(
                "laundry.order",
                "action_refund_from_pos",
                [this.laundryOrderId]
            );

            this.notification.add(
                _t("Order refunded successfully."),
                {
                    type: "success",
                }
            );

            this.back();
        } catch (error) {
            console.error(error);

            this.notification.add(
                error.message || _t("Unable to refund order."),
                {
                    type: "danger",
                }
            );
        }
    }
}



registry.category("pos_pages").add("PosLaundryPaidOrderScreen", {
    name: "laundry_paid_order",
    component: PosLaundryPaidOrderScreen,
    route: `/pos/ui/${odoo.pos_config_id}/pos_laundrypaidorderscreen`,
    params: {},
});