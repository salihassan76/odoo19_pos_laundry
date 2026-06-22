/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosCategory } from "@point_of_sale/app/models/pos_category";

patch(PosCategory.prototype, {
    get associatedProducts() {

        console.log("================================");
        console.log("THIS", this);
        console.log("MODELS", this.models);
        console.log("================================");

        return super.associatedProducts;
    },
});