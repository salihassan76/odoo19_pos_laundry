/** @odoo-module **/

import { Component, useState } from "@odoo/owl";

export class CustomerEditPopup extends Component {
    static template = "pos_laundry.CustomerEditPopup";

    setup() {
        this.state = useState({
            name: this.props.customer?.name || "",
            city: this.props.customer?.city || "",
            phone: this.props.customer?.phone || "",
            email: this.props.customer?.email || "",
            street: this.props.customer?.street || "",
        });
    }

    async save() {
        await this.props.save({
            name: this.state.name,
            city: this.state.city,
            phone: this.state.phone,
            email: this.state.email,
            street: this.state.street,
        });

        this.props.close();
    }

    cancel() {
        this.props.close();
    }
}