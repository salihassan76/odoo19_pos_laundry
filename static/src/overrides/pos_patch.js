/** @odoo-module **/

import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

patch(PosStore.prototype, {
    /**
     * Handles the custom Laundry POS Back button.
     *
     * New unsaved order with items:
     *     Show confirmation before discarding.
     *
     * Empty order or saved laundry order:
     *     Return directly to the Laundry Home screen.
     */
    onClickBackButton() {
        const order =
            this.getOrder?.() ||
            this.get_order?.() ||
            null;

        /*
         * Use the standard POS Back behavior when the current order
         * is not part of the Laundry workflow.
         */
        if (!this.config?.enable_laundry_workflow) {
            return super.onClickBackButton?.(...arguments);
        }

        const orderLines =
            order.getOrderlines?.() ||
            order.get_orderlines?.() ||
            order.lines ||
            [];

        const hasItems = orderLines.length > 0;

        const isSavedLaundryOrder = Boolean(
            order.uiState?.laundry_order_id
        );

        const mustConfirmDiscard =
            hasItems &&
            !isSavedLaundryOrder;

        console.log("[Laundry:Navigation] Back clicked", {
            orderUuid: order.uuid || false,
            laundryOrderId:
                order.uiState?.laundry_order_id ||
                false,
            hasItems,
            isSavedLaundryOrder,
            mustConfirmDiscard,
        });

        /*
         * Warn only when a new, unsaved order contains items.
         */
        if (mustConfirmDiscard) {
            this.dialog.add(ConfirmationDialog, {
                title: _t("Order Not Saved"),
                body: _t(
                    "This order has not been saved. Do you want to go back and discard it?"
                ),
                confirmLabel: _t("Yes, Go Back"),
                cancelLabel: _t("No, Stay"),
                confirmClass: "btn-danger",

                confirm: () => {
                    this._returnToLaundryHome(order);
                },

                /*
                 * No action is required.
                 * The dialog closes and the user stays on ProductScreen.
                 */
                cancel: () => {},
            });

            return;
        }

        /*
         * Empty order or an already-saved laundry order.
         */
        this._returnToLaundryHome(order);
    },

    /**
     * Discards the current frontend POS order and returns to
     * the Laundry Home screen while preserving the customer.
     */
    _returnToLaundryHome(order) {
        const customer =
            order?.getPartner?.() ||
            order?.get_partner?.() ||
            order?.partner_id ||
            this.selected_customer ||
            null;

        console.log(
            "[Laundry:Navigation] Returning to Laundry Home",
            {
                orderUuid:
                    order?.uuid ||
                    false,
                laundryOrderId:
                    order?.uiState
                        ?.laundry_order_id ||
                    false,
                customerId:
                    customer?.id ||
                    false,
            }
        );

        /*
         * Remove the current temporary frontend POS order.
         */
        if (order) {
            if (this.removeOrder) {
                this.removeOrder(order);
            } else if (this.remove_order) {
                this.remove_order(order);
            }
        }

        /*
         * Create a clean frontend order.
         */
        const newOrder =
            this.addNewOrder?.() ||
            this.add_new_order?.() ||
            this.getOrder?.() ||
            this.get_order?.() ||
            null;

        if (newOrder) {
            if (this.setOrder) {
                this.setOrder(newOrder);
            } else if (this.set_order) {
                this.set_order(newOrder);
            }

            /*
             * Keep the selected customer on the new clean order.
             */
            if (customer) {
                if (newOrder.setPartner) {
                    newOrder.setPartner(customer);
                } else if (newOrder.set_partner) {
                    newOrder.set_partner(customer);
                }
            }
        }

        /*
         * Clear the previous Laundry order state.
         */
        this.selected_laundry_order_id = false;
        this.selected_laundry_order_type = null;
        this.selected_customer = customer;

        /*
         * Reset product/category filtering state.
         */
        this.selectedCategory = undefined;
        this.selectedCategoryId = undefined;

        /*
         * Return to Laundry Home.
         */
        this.navigate("pos_homescreen", {
            customer,
        });
    },
});