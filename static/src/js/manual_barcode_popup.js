/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";

import { LaundryBarcodeParser } from "./barcode_parser";

export class ManualBarcodePopup extends Component {
    static template = "pos_laundry.ManualBarcodePopup";

    static components = {
        Dialog,
    };

    static props = {
        close: Function,
        onConfirm: Function,
        title: {
            type: String,
            optional: true,
        },
    };

    setup() {
        this.state = useState({
            barcode: "",
            errorMessage: "",
            processing: false,
        });
    }

    mounted() {
        this.el
            ?.querySelector("#manual_laundry_barcode")
            ?.focus();
    }

    get title() {
        return this.props.title || _t("Enter Laundry Barcode");
    }

    onBarcodeInput(event) {
        this.state.barcode = event.target.value || "";
        this.state.errorMessage = "";
    }

    async confirm() {
        if (this.state.processing) {
            return;
        }

        const parsed = LaundryBarcodeParser.parse(this.state.barcode);

        if (!parsed.valid) {
            this.state.errorMessage = this._getParserError(parsed.errorCode);
            return;
        }

        this.state.processing = true;
        this.state.errorMessage = "";

        try {
            const result = await this.props.onConfirm(parsed.barcode);

            if (!result || result.success !== true) {
                this.state.errorMessage =
                    result?.message ||
                    _t("The barcode could not be processed.");
                return;
            }

            this.props.close();
        } catch (error) {
            this.state.errorMessage =
                error?.message ||
                _t("The barcode could not be processed.");
        } finally {
            this.state.processing = false;
        }
    }

    cancel() {
        if (!this.state.processing) {
            this.props.close();
        }
    }

    onKeydown(event) {
        if (event.key === "Enter") {
            event.preventDefault();
            this.confirm();
        }
    }

    _getParserError(errorCode) {
        switch (errorCode) {
            case "EMPTY_BARCODE":
                return _t("Please enter a barcode.");

            case "INVALID_BARCODE":
                return _t("Enter a valid laundry order barcode.");

            default:
                return _t("The barcode is invalid.");
        }
    }
}