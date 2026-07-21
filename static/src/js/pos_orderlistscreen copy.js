/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";

export class OrderListScreen extends Component {
    static template = "pos_laundry.pos_orderlistscreen";

    setup() {
        this.pos = usePos();
        
    }


    backToRegister() {
        this.pos.navigate("ProductScreen");
    }
}

registry.category("pos_pages").add("pos_orderlistscreen", {
    name: "pos_orderlistscreen",
    component: OrderListScreen,
    route: `/pos/ui/${odoo.pos_config_id}/orderslist`,
    params: {},
});