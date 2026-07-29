/** @odoo-module **/

import { Component } from "@odoo/owl";

export class LaundryReceipt extends Component {
    static template =
        "pos_laundry.LaundryReceipt";

    static props = {
        receipt: {
            type: Object,
        },
    };
}