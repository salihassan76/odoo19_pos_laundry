/** @odoo-module **/

import { _t } from
    "@web/core/l10n/translation";

import { AlertDialog } from
    "@web/core/confirmation_dialog/confirmation_dialog";

import { LaundryReceipt } from
    "../printing/laundry_receipt";


export async function printLaundryReceipt(
    printer,
    receipt,
    dialog
) {
    if (!receipt) {
        dialog?.add(AlertDialog, {
            title: _t("Printer"),
            body: _t(
                "No receipt data was available for printing."
            ),
        });

        return false;
    }

    try {
        console.log(
            "[Laundry] Starting receipt print",
            receipt
        );

        await printer.print(
            LaundryReceipt,
            {
                receipt,
            }
        );

        console.log(
            "[Laundry] Receipt passed to printer service"
        );

        return true;
    } catch (error) {
        console.error(
            "[Laundry] Receipt printing failed:",
            error
        );

        dialog?.add(AlertDialog, {
            title: _t("Printer"),
            body: _t(
                "Unable to print the receipt. " +
                "You can reprint it later from " +
                "the Laundry Order."
            ),
        });

        return false;
    }
}