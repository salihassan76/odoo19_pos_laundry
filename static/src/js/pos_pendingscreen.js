/** @odoo-module **/

import { Component,useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";

export class PendingScreen extends Component {
    static template = "pos_laundry.pos_pendingscreen";

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

registry.category("pos_pages").add("pos_pendingscreen", {
    name: "pos_pendingscreen",
    component: PendingScreen,
    route: `/pos/ui/${odoo.pos_config_id}/laundry-orders`,
    params: {},
});