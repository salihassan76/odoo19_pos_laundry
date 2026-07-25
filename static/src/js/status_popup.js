/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";


export class LaundryStatusPopup extends Component {
    static template =
        "pos_laundry.LaundryStatusPopup";

    static components = {
        Dialog,
    };

    static props = {
        close: {
            type: Function,
        },

        title: {
            type: String,
            optional: true,
        },

        scannedBarcode: {
            type: String,
        },

        order: {
            type: Object,
            optional: true,
        },

        availableStatuses: {
            type: Array,
            optional: true,
        },

        currentStatusId: {
            type: [Number, Boolean],
            optional: true,
        },

        onConfirm: {
            type: Function,
        },
    };

    static defaultProps = {
        title: _t("Laundry Order Status"),
        order: {},
        availableStatuses: [],
        currentStatusId: false,
    };

    setup() {
        this.state = useState({
            selectedStatusId:
                Number(
                    this.props.currentStatusId || 0
                ) || false,

            processing: false,

            errorMessage: "",
        });
    }

    // ---------------------------------------------------------------------
    // Data
    // ---------------------------------------------------------------------

    get order() {
        return this.props.order || {};
    }

    get statuses() {
        return (
            this.props.availableStatuses ||
            []
        );
    }

    get hasStatuses() {
        return this.statuses.length > 0;
    }

    get selectedStatusId() {
        return Number(
            this.state.selectedStatusId || 0
        );
    }

    get currentStatusId() {
        return Number(
            this.props.currentStatusId ||
            this.order.status_id ||
            0
        );
    }

    get canConfirm() {
        return Boolean(
            this.selectedStatusId &&
            !this.state.processing
        );
    }

    get selectedStatus() {
        return this.statuses.find(
            (status) =>
                Number(status.id) ===
                this.selectedStatusId
        );
    }

    get confirmButtonLabel() {
        if (this.state.processing) {
            return _t("Updating...");
        }

        if (
            this.selectedStatusId ===
            this.currentStatusId
        ) {
            return _t("Confirm Status");
        }

        return _t("Update Status");
    }

    // ---------------------------------------------------------------------
    // Status selection
    // ---------------------------------------------------------------------

    selectStatus(statusId) {
        if (this.state.processing) {
            return;
        }

        this.state.selectedStatusId =
            Number(statusId || 0);

        this.state.errorMessage = "";
    }

    isSelected(statusId) {
        return (
            Number(statusId) ===
            this.selectedStatusId
        );
    }

    isCurrent(statusId) {
        return (
            Number(statusId) ===
            this.currentStatusId
        );
    }

    // ---------------------------------------------------------------------
    // Confirm and close
    // ---------------------------------------------------------------------

    async confirm() {
        if (!this.canConfirm) {
            if (!this.selectedStatusId) {
                this.state.errorMessage =
                    _t(
                        "Please select an order status."
                    );
            }

            return;
        }

        this.state.processing = true;
        this.state.errorMessage = "";

        try {
            const result =
                await this.props.onConfirm(
                    this.selectedStatusId
                );

            /*
             * Keep the popup open when the backend explicitly
             * reports a failure.
             */
            if (!result || result.success !== true) {
                this.state.errorMessage =
                    result.message ||
                    _t(
                        "The status could not be updated."
                    );

                return;
            }

            /*
             * The service already displays the success
             * notification after status_updated.
             */
            this.props.close();
        } catch (error) {
            console.error(
                "Laundry status update failed:",
                error
            );

            this.state.errorMessage =
                this._getErrorMessage(error);
        } finally {
            this.state.processing = false;
        }
    }

    cancel() {
        if (this.state.processing) {
            return;
        }

        this.props.close();
    }

    // ---------------------------------------------------------------------
    // Keyboard handling
    // ---------------------------------------------------------------------

    async onKeydown(event) {
        if (
            event.key === "Escape" &&
            !this.state.processing
        ) {
            event.preventDefault();
            event.stopPropagation();

            this.cancel();
            return;
        }

        if (
            event.key === "Enter" &&
            this.canConfirm
        ) {
            event.preventDefault();
            event.stopPropagation();

            await this.confirm();
        }
    }

    // ---------------------------------------------------------------------
    // Display helpers
    // ---------------------------------------------------------------------

    getStatusStyle(status) {
        if (!status?.color) {
            return "";
        }

        /*
         * Supports values returned as CSS-compatible colors,
         * such as:
         *
         *     #28a745
         *     rgb(40, 167, 69)
         *
         * Numeric Odoo color indexes should be displayed
         * using CSS classes in the XML instead.
         */
        const color =
            String(status.color || "").trim();

        if (
            color.startsWith("#") ||
            color.startsWith("rgb") ||
            color.startsWith("hsl")
        ) {
            return (
                `border-color: ${color}; ` +
                `--laundry-status-color: ${color};`
            );
        }

        return "";
    }

    getStatusColorClass(status) {
        const color = Number(
            status?.color || 0
        );

        if (
            !Number.isInteger(color) ||
            color < 1 ||
            color > 11
        ) {
            return "";
        }

        return `o_tag_color_${color}`;
    }

    formatAmount(amount) {
        const value = Number(
            amount || 0
        );

        const currency =
            this.order.currency || {};

        const symbol =
            currency.symbol ||
            currency.name ||
            "";

        const decimals = Number.isInteger(
            currency.decimal_places
        )
            ? currency.decimal_places
            : 3;

        const formatted =
            value.toFixed(decimals);

        if (currency.position === "after") {
            return `${formatted} ${symbol}`.trim();
        }

        return `${symbol} ${formatted}`.trim();
    }

    // ---------------------------------------------------------------------
    // Error handling
    // ---------------------------------------------------------------------

    _getErrorMessage(error) {
        return (
            error?.data?.message ||
            error?.data?.arguments?.[0] ||
            error?.cause?.message ||
            error?.message ||
            _t(
                "An unexpected error occurred while updating the status."
            )
        );
    }
}