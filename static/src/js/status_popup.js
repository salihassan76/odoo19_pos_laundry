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

        currentStatus: {
            type: Object,
            optional: true,
        },

        nextStatus: {
            type: Object,
            optional: true,
        },

        onConfirm: {
            type: Function,
        },
    };

    static defaultProps = {
        title: _t("Confirm Status Update"),
        order: {},
        currentStatus: {},
        nextStatus: {},
    };

    setup() {
        this.state = useState({
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

    get currentStatus() {
        return this.props.currentStatus || {};
    }

    get nextStatus() {
        return this.props.nextStatus || {};
    }

    get hasNextStatus() {
        return Boolean(
            Number(this.nextStatus.id || 0)
        );
    }

    get canConfirm() {
        return (
            this.hasNextStatus &&
            !this.state.processing
        );
    }

    get confirmButtonLabel() {
        if (this.state.processing) {
            return _t("Updating...");
        }

        return _t("Confirm");
    }

    // ---------------------------------------------------------------------
    // Confirm and close
    // ---------------------------------------------------------------------

    async confirm() {
        if (!this.canConfirm) {
            if (!this.hasNextStatus) {
                this.state.errorMessage =
                    _t(
                        "No barcode-enabled next status is available."
                    );
            }

            return;
        }

        this.state.processing = true;
        this.state.errorMessage = "";

        try {
            const result =
                await this.props.onConfirm(
                    Number(this.nextStatus.id)
                );

            if (!result || result.success !== true) {
                this.state.errorMessage =
                    result?.message ||
                    _t(
                        "The status could not be updated."
                    );

                return;
            }

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