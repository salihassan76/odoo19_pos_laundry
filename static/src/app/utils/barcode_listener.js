/** @odoo-module **/

import { registry } from "@web/core/registry";
import { LaundryBarcodeParser } from "../../js/barcode_parser";

export class LaundryBarcodeListener {
    constructor(env) {
        this.env = env;
        this.pos = env.services.pos;

        this.buffer = "";
        this.bufferTimer = null;

        this.enabled = false;
        this.processing = false;

        this.lastBarcode = null;
        this.lastScanTime = 0;

        /*
         * Maximum delay between barcode characters.
         *
         * This is not the same as duplicate_scan_delay.
         * Barcode scanners normally send characters very quickly.
         */
        this.characterTimeout = 150;

        this._onKeyDown = this._onKeyDown.bind(this);
    }

    // ---------------------------------------------------------------------
    // Configuration
    // ---------------------------------------------------------------------

    get config() {
        return this.pos?.config || {};
    }

    get isConfigured() {
        return Boolean(
            this.config.enable_laundry_barcode
        );
    }

    get duplicateDelayMilliseconds() {
        const seconds = Number(
            this.config.duplicate_scan_delay || 0
        );

        return Math.max(seconds, 0) * 1000;
    }

    get continuousScanning() {
        return Boolean(
            this.config.continuous_barcode_scan
        );
    }

    // ---------------------------------------------------------------------
    // Lifecycle
    // ---------------------------------------------------------------------

    start() {
        if (
            this.enabled ||
            !this.isConfigured
        ) {
            return;
        }

        this.enabled = true;

        window.addEventListener(
            "keydown",
            this._onKeyDown,
            true
        );
    }

    stop() {
        if (!this.enabled) {
            return;
        }

        this.enabled = false;

        window.removeEventListener(
            "keydown",
            this._onKeyDown,
            true
        );

        this._clearBuffer();
    }

    pause() {
        this.processing = true;
        this._clearBuffer();
    }

    resume() {
        this.processing = false;
        this._clearBuffer();
    }

    // ---------------------------------------------------------------------
    // Keyboard handling
    // ---------------------------------------------------------------------

    _onKeyDown(event) {
        if (
            !this.enabled ||
            this.processing ||
            !this.isConfigured
        ) {
            return;
        }

        /*
         * Ignore normal typing inside editable fields.
         *
         * This prevents customer search, quantity fields,
         * notes, and payment inputs from being interpreted
         * as laundry barcodes.
         */
        if (this._isEditableTarget(event.target)) {
            return;
        }

        if (event.key === "Enter") {
            const barcode = this.buffer.trim();

            this._clearBuffer();

            if (!barcode) {
                return;
            }

            event.preventDefault();
            event.stopPropagation();

            void this._processBarcode(barcode);

            return;
        }

        /*
         * Ignore modifiers and navigation keys.
         */
        if (
            event.ctrlKey ||
            event.altKey ||
            event.metaKey ||
            event.key.length !== 1
        ) {
            return;
        }

        this.buffer += event.key;

        clearTimeout(this.bufferTimer);

        this.bufferTimer = setTimeout(
            () => this._clearBuffer(),
            this.characterTimeout
        );
    }

    // ---------------------------------------------------------------------
    // Barcode processing
    // ---------------------------------------------------------------------

    async _processBarcode(scannedValue) {

        const parsed = LaundryBarcodeParser.parse(scannedValue);

        if (!parsed.valid) {
            console.debug(
                "Invalid laundry barcode:",
                parsed.errorCode
            );
            return;
        }

        // Use the normalized barcode
        const barcode = parsed.barcode;

        if (this._isDuplicateScan(barcode)) {
            return;
        }

        const barcodeService =
            this.env.services.laundry_barcode;

        if (!barcodeService) {
            console.error(
                "Laundry barcode service is not available."
            );
            return;
        }

        this.processing = true;

        try {
            await barcodeService.process(barcode);

            this.lastBarcode = barcode;
            this.lastScanTime = Date.now();
        } catch (error) {
            console.error(
                "Laundry barcode processing failed:",
                error
            );
        } finally {
            this._clearBuffer();

            if (this.continuousScanning) {
                this.processing = false;
            } else {
                this.stop();
            }
        }
    }

    _isDuplicateScan(barcode) {
        if (
            !this.lastBarcode ||
            this.lastBarcode !== barcode
        ) {
            return false;
        }

        const elapsed =
            Date.now() - this.lastScanTime;

        return (
            elapsed <
            this.duplicateDelayMilliseconds
        );
    }

    // ---------------------------------------------------------------------
    // Helpers
    // ---------------------------------------------------------------------

    _isEditableTarget(target) {
        if (!target) {
            return false;
        }

        const tagName =
            target.tagName?.toUpperCase();

        return (
            tagName === "INPUT" ||
            tagName === "TEXTAREA" ||
            tagName === "SELECT" ||
            target.isContentEditable
        );
    }

    _clearBuffer() {
        this.buffer = "";

        if (this.bufferTimer) {
            clearTimeout(this.bufferTimer);
            this.bufferTimer = null;
        }
    }
}

registry.category("services").add(
    "laundry_barcode_listener",
    {
        dependencies: [
            "pos",
            "laundry_barcode",
        ],

        start(env) {
            const listener =
                new LaundryBarcodeListener(env);

            listener.start();

            return listener;
        },
    }
);