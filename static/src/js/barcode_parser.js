/** @odoo-module **/

export class LaundryBarcodeParser {
    static parse(value) {
        const barcode = (value || "")
            .trim()
            .toUpperCase();

        if (!barcode) {
            return {
                valid: false,
                errorCode: "EMPTY_BARCODE",
            };
        }

        if (!barcode.startsWith("LND")) {
            return {
                valid: false,
                errorCode: "INVALID_BARCODE",
            };
        }

        return {
            valid: true,
            barcode,
        };
    }
}