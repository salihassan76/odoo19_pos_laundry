/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { useState } from "@odoo/owl";

export class LaundryOrdersScreen extends Component {
    static template = "laundry_pos.LaundryOrdersScreens";

    setup() {
        this.pos = usePos();
        this.state = useState({
        searchTerm: "",
        });
    }


    backToRegister() {
        this.pos.navigate("ProductScreen");
    }
}

registry.category("pos_pages").add("LaundryOrdersScreen", {
    name: "LaundryOrdersScreen",
    component: LaundryOrdersScreen,
    route: `/pos/ui/${odoo.pos_config_id}/laundry-orders`,
    params: {},
});