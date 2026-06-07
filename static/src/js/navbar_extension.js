/** @odoo-module **/

import { Navbar } from "@point_of_sale/app/navbar/navbar";
import { patch } from "@web/core/utils/patch";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";


patch(Navbar.prototype, {
    setup() {
        super.setup();
        this.pos = usePos();
    },
    open_pos_pendingscreen(){
        this.pos.navigate("pos_customerscreen");
    },
    open_pos_homescreen(){
        this.pos.navigate("pos_homescreen");
    },
    open_pos_orderlistscreen(){
        this.pos.navigate("pos_orderlistscreen");
    },
    

});