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
        activePackages: [],
        });

        onWillStart(async () => {
            this.state.orderTypes = await this.orm.searchRead(
                "laundry.order.type",
                [["active", "=", true]],
                ["id", "name", "icon_class", "icon_color", "sequence", "pos_category_ids","is_package_sale",]
            );

            this.state.orderTypes.sort((a, b) => {
                return (a.sequence || 0) - (b.sequence || 0);
            });

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
        const customer = this.state.customer;

        if (!customer) {
            this.state.activePackages = [];
            return;
        }

        try {
            const packages = await this.orm.searchRead(
                "partner.package",
                [
                    ["partner_id", "=", customer.id],
                    ["state", "=", "active"],
                ],
                [
                    "id",
                    "name",
                    "package_rule_id",
                    "start_date",
                    "end_date",
                    "state",
                ]
            );

            this.state.activePackages = packages || [];
            console.log("Active packages:", packages);

        } catch (error) {
            console.error("Package RPC failed full error:", error);
            console.error("Error data:", error.data);
            console.error("Error message:", error.message);
            this.state.activePackages = [];
        }
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

        if (!order) {
            return;
        }

        if (this.state.customer) {
            order.set_partner?.(this.state.customer);
            order.setPartner?.(this.state.customer);
        }

        const allowedCategoryIds = (orderType.pos_category_ids || []).map((cat) =>
            typeof cat === "object" ? cat.id : cat
        );

        order.uiState.laundry_order_type_id = orderType.id;
        order.uiState.laundry_order_type_name = orderType.name;
        order.uiState.laundry_order_type_prefix = orderType.prefix;
        order.uiState.laundry_allowed_pos_category_ids = allowedCategoryIds;
        order.uiState.is_package_sale = orderType.is_package_sale;

        this.pos.selected_laundry_order_type = orderType;

        console.log("Selected order type:", orderType.name);
        console.log("Allowed categories:", allowedCategoryIds);
        

        this.pos.navigate("ProductScreen");
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


    selectPackage(pkg) {
        let order = this.pos.get_order
            ? this.pos.get_order()
            : this.pos.getOrder?.();

        if (!order) {
            order = this.pos.add_new_order
                ? this.pos.add_new_order()
                : this.pos.addNewOrder?.();
        }

        if (!order) {
            return;
        }

        if (this.state.customer) {
            order.set_partner?.(this.state.customer);
            order.setPartner?.(this.state.customer);
        }

        order.uiState.is_package_sale = false;
        order.uiState.partner_package_id = pkg.id;
        order.uiState.package_rule_id = pkg.package_rule_id?.[0] || false;
        order.uiState.package_rule_name = pkg.package_rule_id?.[1] || "";

        order.is_package_sale = false;
        order.partner_package_id = pkg.id;
        order.package_rule_id = pkg.package_rule_id?.[0] || false;
        order.package_rule_name = pkg.package_rule_id?.[1] || "";

        console.log("Selected active package:", pkg);

        this.pos.navigate("ProductScreen");
    }
}

registry.category("pos_pages").add("pos_homescreen", {
    name: "pos_homescreen",
    component: PosHomeScreen,
    route: `/pos/ui/${odoo.pos_config_id}/home`,
    params: {},
});