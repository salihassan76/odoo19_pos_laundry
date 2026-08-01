/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";

import { LaundryStatusPopup } from "../../js/status_popup";
import { ManualBarcodePopup } from "../../js/manual_barcode_popup";


export class LaundryBarcodeService {
    constructor(env, services) {
        this.env = env;

        this.pos = services.pos;
        this.orm = services.orm;
        this.dialog = services.dialog;
        this.notification = services.notification;

        this.processing = false;
    }

    // ---------------------------------------------------------------------
    // Configuration
    // ---------------------------------------------------------------------

    get config() {
        return this.pos?.config || {};
    }

    get enabled() {
        return Boolean(
            this.config.enable_laundry_barcode
        );
    }

    // ---------------------------------------------------------------------
    // Public API
    // ---------------------------------------------------------------------

    /**
     * Process a barcode scanned from the active POS.
     *
     * Called from barcode_listener.js:
     *
     *     env.services.laundry_barcode.process(barcode)
     *
     * @param {string} scannedBarcode
     * @returns {Promise<Object|null>}
     */
    async process(scannedBarcode) {
        const barcode = String(
            scannedBarcode || ""
        ).trim();

        if (!barcode) {
            return null;
        }

        if (!this.enabled) {
            this.notification.add(
                _t(
                    "Laundry barcode scanning is disabled for this POS."
                ),
                {
                    type: "warning",
                }
            );

            return null;
        }

        /*
         * Prevent concurrent barcode-processing requests.
         *
         * Duplicate-scan timing is handled by barcode_listener.js.
         */
        if (this.processing) {
            return null;
        }

        this.processing = true;

        try {
            const result = await this._processOnServer(
                barcode
            );

            return await this._handleResult(
                result,
                barcode
            );
        } catch (error) {
            this._handleError(error);

            return null;
        } finally {
            this.processing = false;
        }
    }

    /**
     * Confirm the configured next order status.
     *
     * @param {string} scannedBarcode
     * @param {number} statusId
     * @returns {Promise<Object|null>}
     */
    async updateStatus(
        scannedBarcode,
        statusId
    ) {
        const barcode = String(
            scannedBarcode || ""
        ).trim();

        const requestedStatusId = Number(
            statusId || 0
        );

        if (
            !barcode ||
            !requestedStatusId
        ) {
            this.notification.add(
                _t(
                    "A barcode and a valid next status are required."
                ),
                {
                    type: "warning",
                }
            );

            return null;
        }

        if (this.processing) {
            return null;
        }

        this.processing = true;

        try {
            const result = await this._processOnServer(
                barcode,
                requestedStatusId
            );

            return await this._handleResult(
                result,
                barcode
            );
        } catch (error) {
            this._handleError(error);

            return null;
        } finally {
            this.processing = false;
        }
    }

    // ---------------------------------------------------------------------
    // Backend RPC
    // ---------------------------------------------------------------------

    async _processOnServer(
        barcode,
        requestedStatusId = false
    ) {
        const posConfigId = Number(
            this.config.id || 0
        );

        if (!posConfigId) {
            throw new Error(
                _t(
                    "The current POS configuration could not be identified."
                )
            );
        }

        return await this.orm.call(
            "laundry.order",
            "process_pos_barcode",
            [],
            {
                scanned_barcode: barcode,
                pos_config_id: posConfigId,
                requested_status_id:
                    requestedStatusId || false,
            }
        );
    }

    // ---------------------------------------------------------------------
    // Backend result handling
    // ---------------------------------------------------------------------

    async _handleResult(
        result,
        scannedBarcode
    ) {
        if (!result) {
            return null;
        }

        if (
            typeof result !== "object" ||
            Array.isArray(result)
        ) {
            console.warn(
                "Unexpected laundry barcode response:",
                result
            );

            return result;
        }

        if (result.success === false) {
            this.notification.add(
                result.message ||
                    _t(
                        "The barcode could not be processed."
                    ),
                {
                    type: "danger",
                    sticky: true,
                }
            );

            return result;
        }

        const action =
            result.action ||
            result.result ||
            false;

        switch (action) {
            case "popup":
            case "open_popup":
            case "status_popup":
                return this._openStatusPopup(
                    result,
                    scannedBarcode
                );

            case "status_updated":
                return this._handleStatusUpdated(
                    result
                );

            case "order_opened":
            case "open_order":
                return this._handleOrderOpened(
                    result
                );

            case "duplicate_ignored":
                return this._handleDuplicateIgnored(
                    result
                );

            case "status_unchanged":
                return this._handleStatusUnchanged(
                    result
                );

            case "print_requested":
                return this._handlePrintRequested(
                    result
                );

            default:
                return this._handleGenericResult(
                    result
                );
        }
    }

    // ---------------------------------------------------------------------
    // Status confirmation popup
    // ---------------------------------------------------------------------

    _openStatusPopup(
        result,
        scannedBarcode
    ) {
        const popupData =
            result.popup_data ||
            result.data ||
            result;

        const order =
            popupData.order ||
            {};

        const currentStatus =
            popupData.current_status ||
            {};

        const nextStatus =
            popupData.next_status ||
            {};

        /*
         * The backend should already reject orders that do
         * not have a valid barcode-enabled next status.
         *
         * This check protects the frontend from malformed
         * or outdated responses.
         */
        if (!Number(nextStatus.id || 0)) {
            this.notification.add(
                result.message ||
                    _t(
                        "No barcode-enabled next status is available."
                    ),
                {
                    type: "warning",
                    sticky: true,
                }
            );

            return result;
        }

        this.dialog.add(
            LaundryStatusPopup,
            {
                title:
                    popupData.title ||
                    _t(
                        "Confirm Status Update"
                    ),

                scannedBarcode,

                order,

                currentStatus,

                nextStatus,

                /*
                 * Called by status_popup.js when the user
                 * confirms the configured next status.
                 */
                onConfirm:
                    async (statusId) => {
                        return await this.updateStatus(
                            scannedBarcode,
                            statusId
                        );
                    },
            }
        );

        return result;
    }

    // ---------------------------------------------------------------------
    // Specific action handlers
    // ---------------------------------------------------------------------

    _handleStatusUpdated(result) {
        this.notification.add(
            result.message ||
                _t(
                    "The laundry order status was updated."
                ),
            {
                type: "success",
            }
        );

        this._dispatchEvent(
            "laundry-barcode-status-updated",
            result
        );

        return result;
    }

    _handleOrderOpened(result) {
        this._dispatchEvent(
            "laundry-barcode-open-order",
            result
        );

        if (result.message) {
            this.notification.add(
                result.message,
                {
                    type: "info",
                }
            );
        }

        return result;
    }

    _handleDuplicateIgnored(result) {
        /*
         * Duplicate scans are normally ignored silently.
         * Keep the message in the browser console for diagnostics.
         */
        if (result.message) {
            console.info(
                "Laundry barcode duplicate ignored:",
                result.message
            );
        }

        return result;
    }

    _handleStatusUnchanged(result) {
        this.notification.add(
            result.message ||
                _t(
                    "The order already has the selected status."
                ),
            {
                type: "info",
            }
        );

        return result;
    }

    _handlePrintRequested(result) {
        this._dispatchEvent(
            "laundry-barcode-print-requested",
            result
        );

        if (result.message) {
            this.notification.add(
                result.message,
                {
                    type: "info",
                }
            );
        }

        return result;
    }

    _handleGenericResult(result) {
        if (result.message) {
            this.notification.add(
                result.message,
                {
                    type:
                        result.notification_type ||
                        "success",
                }
            );
        }

        return result;
    }

    // ---------------------------------------------------------------------
    // Error handling
    // ---------------------------------------------------------------------

    _handleError(error) {
        console.error(
            "Laundry barcode processing failed:",
            error
        );

        this.notification.add(
            this._getErrorMessage(error),
            {
                title:
                    _t(
                        "Barcode Processing Error"
                    ),
                type: "danger",
                sticky: true,
            }
        );
    }

    _getErrorMessage(error) {
        return (
            error?.data?.message ||
            error?.data?.arguments?.[0] ||
            error?.cause?.message ||
            error?.message ||
            _t(
                "An unexpected error occurred while processing the barcode."
            )
        );
    }

    // ---------------------------------------------------------------------
    // Events
    // ---------------------------------------------------------------------

    _dispatchEvent(
        eventName,
        detail = {}
    ) {
        window.dispatchEvent(
            new CustomEvent(
                eventName,
                {
                    detail,
                }
            )
        );
    }

    // ---------------------------------------------------------------------
    // Manual barcode entry
    // ---------------------------------------------------------------------

    async openManualBarcodeEntry() {
        this.dialog.add(
            ManualBarcodePopup,
            {
                onConfirm: async (barcode) => {
                    return await this.process(
                        barcode
                    );
                },
            }
        );
    }
}


// -------------------------------------------------------------------------
// Odoo service registration
// -------------------------------------------------------------------------

export const laundryBarcodeService = {
    dependencies: [
        "pos",
        "orm",
        "dialog",
        "notification",
    ],

    start(env, services) {
        return new LaundryBarcodeService(
            env,
            services
        );
    },
};


registry.category("services").add(
    "laundry_barcode",
    laundryBarcodeService
);