/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { CustomerEditPopup } from "./pos_customereditpopup";

export class PosHomeScreen extends Component {
    static template = "pos_laundry.pos_homescreen";

    setup() {
        this.pos = useService("pos");
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.laundry = useService("laundry");

        this.state = useState({
            customer: this.props.customer || this.pos.selected_customer || null,
            orderTypes: [],
            activePackages: [],
        });

        onWillStart(async () => {
            this.state.orderTypes = await this.laundry.getVisibleOrderTypes();
            await this.getActivePackages();
        });
    }

    async openCustomerDetails() {
        const customer = this.state.customer;

        if (!customer) {
            await this.pos.selectPartner();
            return;
        }

        this.dialog.add(CustomerEditPopup, {
            customer,
            save: async (values) => {
                await this.orm.write("res.partner", [customer.id], values);
                Object.assign(customer, values);
                this.state.customer = customer;
            },
        });
    }

    async getActivePackages() {
        this.state.activePackages = await this.laundry.getActivePackages(
            this.state.customer?.id
        );
    }

    selectOrderType(orderType) {
        this.laundry.selectOrderType(orderType, this.state.customer);
    }

    openNewOrder() {
        const order = this.laundry.prepareOrder(this.state.customer);

        this.pos.navigate("ProductScreen", {
            orderUuid: order.uuid,
        });
    }

    openPendingOrders() {
        this.pos.navigate("pos_pendingscreen");
    }

    async selectPackage(pkg) {
        await this.laundry.selectPackage(pkg, this.state.customer);
    }
}

registry.category("pos_pages").add("pos_homescreen", {
    name: "pos_homescreen",
    component: PosHomeScreen,
    route: `/pos/ui/${odoo.pos_config_id}/home`,
    params: {},
});