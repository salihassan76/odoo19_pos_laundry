/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class PosCustomerScreen extends Component {
    static template = "pos_laundry.pos_customerscreen";

    setup() {
        this.pos = useService("pos");
        this.orm = useService("orm");

        this.state = useState({
            searchTerm: "",
            results: [],
            loading: false,
        });

        this.searchTimeout = null;
    }

    onSearchInput(ev) {
        this.state.searchTerm = ev.target.value;

        clearTimeout(this.searchTimeout);

        this.searchTimeout = setTimeout(() => {
            this.searchCustomers();
        }, 300);
    }

    async searchCustomers() {
    const term = this.state.searchTerm.toLowerCase().trim();

    if (!term) {
        this.state.results = [];
        return;
    }

    let partners = [];

    if (this.pos.models["res.partner"]) {
        partners = this.pos.models["res.partner"].getAll();
    }

    console.log("Loaded partners:", partners);

    this.state.results = partners.filter((partner) => {
        const name = (partner.name || "").toLowerCase();
        const mobile = (partner.mobile || "").toLowerCase();
        const phone = (partner.phone || "").toLowerCase();
        const email = (partner.email || "").toLowerCase();

        return (
            name.includes(term) ||
            mobile.includes(term) ||
            phone.includes(term) ||
            email.includes(term)
        );
    }).slice(0, 20);

    console.log("Search results:", this.state.results);
}

    selectCustomer(customer) {
        this.pos.selected_customer = customer;

        this.pos.navigate("pos_homescreen", {
            customer: customer,
        });
    }
/*
async createNewCustomer() {
    const partner = await this.pos.selectPartner({
        create: true,
    });

    if (partner) {
        this.pos.selected_customer = partner;

        this.pos.navigate("pos_homescreen", {
            customer: partner,
        });
    }
}

*/

    
    async createNewCustomer() {
    // Open Product Screen
        this.pos.navigate("ProductScreen");

        setTimeout(async () => {
            const partner = await this.pos.editPartner({
                name: this.state.searchTerm || "",
            });

            if (partner) {
                const order = this.pos.get_order
                    ? this.pos.get_order()
                    : this.pos.getOrder();

                if (order) {
                    if (order.set_partner) {
                        order.set_partner(partner);
                    } else if (order.setPartner) {
                        order.setPartner(partner);
                    }
                }

                this.pos.selected_customer = partner;
            }
        }, 300);
    }

    openNewOrder() {
        this.pos.navigate("ProductScreen");
    }

    openPendingOrders() {
        this.pos.navigate("pos_pendingscreen");
    }
}

registry.category("pos_pages").add("pos_customerscreen", {
    name: "pos_customerscreen",
    component: PosCustomerScreen,
    route: `/pos/ui/${odoo.pos_config_id}/customer`,
    params: {},
});