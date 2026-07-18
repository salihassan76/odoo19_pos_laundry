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
        * Use the standard POS Back behavior when Laundry workflow
        * is disabled.
        */
        if (!this.config?.enable_laundry_workflow) {
            return super.onClickBackButton?.(...arguments);
        }

        /*
        * No active order: return directly to Laundry Home.
        */
        if (!order) {
            this.navigate("pos_homescreen");
            return;
        }

        const orderLines =
            order.getOrderlines?.() ||
            order.get_orderlines?.() ||
            order.lines ||
            [];

        const hasItems =
            orderLines.length > 0;

        const isSavedLaundryOrder =
            Boolean(
                order.uiState?.laundry_order_id
            );

        /*
        * Use the existing Laundry action policy so the Back button
        * follows the same change-detection logic as Update and
        * Discard Changes.
        */
        const laundryService =
            this.laundryService ||
            this.env?.services?.laundryService ||
            this.env?.services?.laundry ||
            null;

        const policy =
            laundryService?.getActionPolicy?.(
                order
            ) || {};

        /*
        * New unsaved order:
        * warn when it contains products.
        */
        const hasUnsavedNewOrder =
            !isSavedLaundryOrder &&
            hasItems;

        /*
        * Saved order:
        * warn when local changes have not been saved.
        *
        * canDiscardChanges is the best value to use because it is
        * true whenever a saved order has changes, even when the
        * current status does not allow Update.
        */
        const hasSavedOrderChanges =
            isSavedLaundryOrder &&
            Boolean(
                policy.canDiscardChanges
            );

        const mustConfirmDiscard =
            hasUnsavedNewOrder ||
            hasSavedOrderChanges;

        console.log(
            "[Laundry:Navigation] Back clicked",
            {
                orderUuid:
                    order.uuid || false,
                laundryOrderId:
                    order.uiState
                        ?.laundry_order_id ||
                    false,
                hasItems,
                isSavedLaundryOrder,
                hasUnsavedNewOrder,
                hasSavedOrderChanges,
                mustConfirmDiscard,
            }
        );

        /*
        * Warn before discarding either:
        * 1. a new unsaved order with products, or
        * 2. unsaved modifications to a saved order.
        */
        if (mustConfirmDiscard) {
            this.dialog.add(
                ConfirmationDialog,
                {
                    title:
                        _t("Discard Changes?"),

                    body:
                        _t(
                            "This order has unsaved changes. Do you want to discard them and go back?"
                        ),

                    confirmLabel:
                        _t(
                            "Discard and Go Back"
                        ),

                    cancelLabel:
                        _t("Stay"),

                    confirmClass:
                        "btn-danger",

                    confirm: () => {
                        this._returnToLaundryHome(
                            order
                        );
                    },

                    /*
                    * The dialog closes and the user remains on
                    * ProductScreen.
                    */
                    cancel: () => {},
                }
            );

            return;
        }

        /*
        * Empty new order or saved order without changes.
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