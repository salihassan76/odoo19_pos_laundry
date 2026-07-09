/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class LaundryPaymentScreen extends Component {
    static template = "pos_laundry.LaundryPaymentScreen";
    static props = ["*"];

    setup() {
        this.pos = useService("pos");
        this.orm = useService("orm");
        this.notification = useService("notification");

        this.state = useState({
            paymentData: {},
            paymentMethods: [],
            selectedPaymentMethodId: null,
            amount: "0.000",
            notes: "",
            loading: true,
        });

        onWillStart(async () => {
            await this.loadScreen();
        });
    }

    get laundryOrderId() {
        return (
            this.props?.laundryOrderId ||
            this.pos.selected_laundry_order_id ||
            false
        );
    }

    get posSessionId() {
        return (
            this.pos.pos_session?.id ||
            this.pos.session?.id ||
            this.pos.config?.current_session_id?.id ||
            this.pos.config?.current_session_id ||
            false
        );
    }

    async loadScreen() {
        if (!this.laundryOrderId) {
            this.notification.add(_t("No laundry order selected."), {
                type: "warning",
            });
            this.back();
            return;
        }

        const result = await this.orm.call(
            "laundry.order",
            "get_payment_data",
            [[this.laundryOrderId]]
        );

        this.state.paymentData = result || {};
        this.state.paymentMethods = result.payment_methods || [];
        this.state.amount = this.formatAmount(result.balance_due || 0);
        this.state.loading = false;
    }

    back() {
        this.pos.navigate?.("pos_homescreen", {
            customer: this.state.paymentData.partner || null,
        });
    }

    cancel() {
        this.back();
    }

    formatAmount(value) {
        return Number(value || 0).toFixed(3);
    }

    setAmount(amount) {
        this.state.amount = this.formatAmount(amount);
    }

    setFullBalance() {
        this.state.amount = this.formatAmount(
            this.state.paymentData.balance_due || 0
        );
    }

    addDigit(digit) {
        let value = this.state.amount || "0";

        if (value === "0.000" || value === "0") {
            value = "";
        }

        if (digit === "." && value.includes(".")) {
            return;
        }

        value += digit;

        if (value.includes(".")) {
            const parts = value.split(".");
            if (parts[1]?.length > 3) {
                return;
            }
        }

        this.state.amount = value || "0";
    }

    backspace() {
        let value = this.state.amount || "0";
        value = value.slice(0, -1);
        this.state.amount = value || "0";
    }

    selectPaymentMethod(method) {
        this.state.selectedPaymentMethodId = method.id;
    }

    async printReceipt() {
        this.notification.add(_t("Payment receipt printing will be added next."), {
            type: "info",
        });
    }

    validateAmount() {
        const amount = Number(this.state.amount || 0);
        const balance = Number(this.state.paymentData.balance_due || 0);

        if (amount <= 0) {
            this.notification.add(_t("Payment amount must be greater than zero."), {
                type: "warning",
            });
            return false;
        }

        if (balance > 0 && amount > balance) {
            this.notification.add(
                _t("Payment amount cannot be greater than the balance due."),
                { type: "warning" }
            );
            return false;
        }

        return true;
    }

    async validatePayment() {
        if (!this.state.selectedPaymentMethodId) {
            this.notification.add(_t("Please select a payment method."), {
                type: "warning",
            });
            return;
        }

        if (!this.posSessionId) {
            this.notification.add(_t("POS session was not found."), {
                type: "danger",
            });
            return;
        }

        if (!this.validateAmount()) {
            return;
        }

        const result = await this.orm.call(
            "laundry.pos.payment",
            "receive_payment_from_pos",
            [{
                laundry_order_id: this.state.paymentData.id,
                pos_session_id: this.posSessionId,
                payment_method_id: this.state.selectedPaymentMethodId,
                amount: Number(this.state.amount),
                note: this.state.notes || "",
            }]
        );

        this.notification.add(
            _t("Payment received: ") + (result.payment_name || ""),
            { type: "success" }
        );

        await this.loadScreen();

        if (Number(this.state.paymentData.balance_due || 0) <= 0) {
            this.back();
        }
    }
}

registry.category("pos_pages").add("LaundryPaymentScreen", {
    name: "LaundryPaymentScreen",
    component: LaundryPaymentScreen,
    route: `/pos/ui/${odoo.pos_config_id}/laundry-payment`,
    params: {},
});