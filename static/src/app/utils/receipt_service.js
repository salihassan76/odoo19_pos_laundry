/** @odoo-module **/

export async function printLaundryReceipt(printer, receipt, dialog) {
    try {
        await printer.print(
            "pos_laundry.LaundryReceipt",
            {
                receipt,
            }
        );
        return true;
    } catch (error) {
        console.error(error);

        dialog.add(AlertDialog, {
            title: "Printer",
            body: "Unable to print the receipt. You can reprint it later from the Laundry Order.",
        });

        return false;
    }
}