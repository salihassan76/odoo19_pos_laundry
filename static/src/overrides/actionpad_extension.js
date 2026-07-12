/** @odoo-module **/

import { ActionpadWidget } from
    "@point_of_sale/app/screens/product_screen/action_pad/action_pad";
import { patch } from "@web/core/utils/patch";
import {
    AlertDialog,
    ConfirmationDialog,
} from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";


function getCurrentOrder(pos) {
    return (
        pos.getOrder?.() ||
        pos.get_order?.() ||
        null
    );
}


patch(ActionpadWidget.prototype, {
    setup() {
        super.setup(...arguments);

        this.dialog = useService("dialog");
        this.laundry = useService("laundry");
    },

    get laundryActions() {
        const order = getCurrentOrder(this.pos);

        if (!this.laundry?.isEnabled?.()) {
            return {
                canSave: false,
                canDiscard: false,
                canUpdate: false,
                canDiscardChanges: false,
                canCancel: false,
                canPayment: false,
                canRefund: false,
                canPrint: false,
            };
        }

        return this.laundry.getActionPolicy(order);
    },

    async clickSaveOrder() {
        if (!this.laundryActions.canSave) {
            return;
        }

        try {
            await this.laundry.saveAndHandleResult();
        } catch (error) {
            console.error(
                "[Laundry:ActionPad] Save failed",
                error
            );

            this.dialog.add(AlertDialog, {
                title: _t("Save Laundry Order"),
                body:
                    error?.message ||
                    _t("Could not save the laundry order."),
            });
        }
    },

    clickDiscardLaundryOrder() {
        if (!this.laundryActions.canDiscard) {
            return;
        }

        this.dialog.add(ConfirmationDialog, {
            title: _t("Discard Order"),
            body: _t(
                "This order has not been saved. "
                + "Do you want to discard it?"
            ),
            confirmLabel: _t("Discard"),
            cancelLabel: _t("Stay"),
            confirm: async () => {
                try {
                    await this.laundry.discardCurrentOrder();
                } catch (error) {
                    console.error(
                        "[Laundry:ActionPad] Discard failed",
                        error
                    );

                    this.dialog.add(AlertDialog, {
                        title: _t("Discard Order"),
                        body:
                            error?.message ||
                            _t("Could not discard the order."),
                    });
                }
            },
        });
    },

    async clickUpdateLaundryOrder() {
        if (!this.laundryActions.canUpdate) {
            return;
        }

        try {
            await this.laundry.saveAndHandleResult();

            const order = getCurrentOrder(this.pos);

            if (order?.uiState) {
                order.uiState.laundry_has_changes = false;
            }
        } catch (error) {
            console.error(
                "[Laundry:ActionPad] Update failed",
                error
            );

            this.dialog.add(AlertDialog, {
                title: _t("Update Laundry Order"),
                body:
                    error?.message ||
                    _t("Could not update the laundry order."),
            });
        }
    },

    clickDiscardLaundryChanges() {
        if (!this.laundryActions.canDiscardChanges) {
            return;
        }

        const order = getCurrentOrder(this.pos);
        const laundryOrderId =
            order?.uiState?.laundry_order_id;

        if (!laundryOrderId) {
            return;
        }

        this.dialog.add(ConfirmationDialog, {
            title: _t("Discard Changes"),
            body: _t(
                "Do you want to discard the changes "
                + "made to this order?"
            ),
            confirmLabel: _t("Discard Changes"),
            cancelLabel: _t("Keep Editing"),
            confirm: async () => {
                try {
                    await this.laundry.openLaundryOrder(
                        laundryOrderId
                    );
                } catch (error) {
                    console.error(
                        "[Laundry:ActionPad] "
                        + "Discard changes failed",
                        error
                    );

                    this.dialog.add(AlertDialog, {
                        title: _t("Discard Changes"),
                        body:
                            error?.message ||
                            _t(
                                "Could not restore "
                                + "the saved order."
                            ),
                    });
                }
            },
        });
    },

    cancelLaundryOrder() {
        if (!this.laundryActions.canCancel) {
            return;
        }

        this.dialog.add(ConfirmationDialog, {
            title: _t("Cancel Order"),
            body: _t(
                "Are you sure you want to cancel "
                + "this saved laundry order?"
            ),
            confirmLabel: _t("Cancel Order"),
            cancelLabel: _t("Keep Order"),
            confirm: async () => {
                try {
                    await this.laundry.cancelOrder();
                } catch (error) {
                    console.error(
                        "[Laundry:ActionPad] "
                        + "Cancellation failed",
                        error
                    );

                    this.dialog.add(AlertDialog, {
                        title: _t("Cancel Order"),
                        body:
                            error?.message ||
                            _t(
                                "Could not cancel "
                                + "the laundry order."
                            ),
                    });
                }
            },
        });
    },

    async clickPayLaundryOrder() {
        if (!this.laundryActions.canPayment) {
            return;
        }

        try {
            await this.laundry.payLaundryOrder();
        } catch (error) {
            console.error(
                "[Laundry:ActionPad] Payment failed",
                error
            );

            this.dialog.add(AlertDialog, {
                title: _t("Laundry Order Payment"),
                body:
                    error?.message ||
                    _t(
                        "Could not receive payment "
                        + "for the laundry order."
                    ),
            });
        }
    },

    async clickRefundLaundryOrder() {
        if (!this.laundryActions.canRefund) {
            return;
        }

        try {
            await this.laundry.refundLaundryOrder();
        } catch (error) {
            console.error(
                "[Laundry:ActionPad] Refund failed",
                error
            );

            this.dialog.add(AlertDialog, {
                title: _t("Refund Laundry Order"),
                body:
                    error?.message ||
                    _t("Could not refund the laundry order."),
            });
        }
    },

    async clickPrintLaundryOrder() {
        if (!this.laundryActions.canPrint) {
            return;
        }

        const order = getCurrentOrder(this.pos);
        const laundryOrderId =
            order?.uiState?.laundry_order_id;

        if (!laundryOrderId) {
            return;
        }

        try {
            await this.laundry.printSavedLaundryOrder(
                laundryOrderId
            );
        } catch (error) {
            console.error(
                "[Laundry:ActionPad] Print failed",
                error
            );

            this.dialog.add(AlertDialog, {
                title: _t("Print Laundry Order"),
                body:
                    error?.message ||
                    _t("Could not print the laundry order."),
            });
        }
    },
});