/** @odoo-module **/

import { Component,useState,onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { CustomerEditPopup } from "./pos_customereditpopup";

export class PosHomeScreen extends Component {
    static template = "pos_laundry.pos_homescreen";

    setup() {
        this.pos = useService("pos");
        this.orm = useService("orm");
        this.dialog = useService("dialog");
        this.state = useState({
        customer:
            this.props.customer ||
            this.pos.selected_customer ||
            null,
        orderTypes: [],
        });

        onWillStart(async () => {
            this.state.orderTypes = await this.orm.searchRead(
                "laundry.order.type",
                [["active", "=", true]],
                ["id", "name", "icon_class", "icon_color", "sequence", "pos_category_ids",]
            );

            this.state.orderTypes.sort((a, b) => {
                return (a.sequence || 0) - (b.sequence || 0);
            });
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

    selectOrderType(orderType) {
        let order = this.pos.get_order
            ? this.pos.get_order()
            : this.pos.getOrder?.();

        if (!order) {
            order = this.pos.add_new_order
                ? this.pos.add_new_order()
                : this.pos.addNewOrder?.();
        }

        if (order && this.state.customer) {
            order.set_partner?.(this.state.customer);
            order.setPartner?.(this.state.customer);
        }

        order.laundry_order_type_id = orderType.id;
        order.laundry_order_type_name = orderType.name;
        order.laundry_order_type_prefix = orderType.prefix;
        order.laundry_allowed_pos_category_ids = orderType.pos_category_ids || [];

        this.pos.selected_laundry_order_type = orderType;

        this.pos.navigate("ProductScreen", {
            laundry_order_type_id: orderType.id,
            laundry_order_type_name: orderType.name,
            laundry_order_type_prefix: orderType.prefix,
            allowed_pos_category_ids: orderType.pos_category_ids || [],
        });
    }

    openNewOrder() {
        let order = this.pos.get_order
            ? this.pos.get_order()
            : this.pos.getOrder?.();

        if (!order) {
            order = this.pos.add_new_order
                ? this.pos.add_new_order()
                : this.pos.addNewOrder?.();
        }

        if (order && this.state.customer) {
            order.set_partner?.(this.state.customer);
            order.setPartner?.(this.state.customer);
        }

        this.pos.navigate("ProductScreen");
    }
    openPendingOrders() {
        this.pos.navigate("pos_pendingscreen");
    }
}

registry.category("pos_pages").add("pos_homescreen", {
    name: "pos_homescreen",
    component: PosHomeScreen,
    route: `/pos/ui/${odoo.pos_config_id}/home`,
    params: {},
});