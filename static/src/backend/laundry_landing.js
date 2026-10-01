/** @odoo-module **/

import { Component, onMounted, onWillStart, onWillUnmount, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class LaundryLanding extends Component {
    static template = "pos_laundry.LaundryLanding";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            loading: true,
            shops: [],
            groups: [],
            selectedShop: null,
        });
        onWillStart(() => this.loadData());
        onMounted(() => this.syncMenuVisibility());
        onWillUnmount(() => document.body.classList.remove("o_laundry_shop_landing"));
    }

    async loadData() {
        this.state.loading = true;
        const data = await this.orm.call("pos.config", "get_laundry_landing_data", []);
        this.state.shops = data.shops || [];
        this.state.groups = data.workspace_groups || [];
        const selectedId = this.props.action?.params?.pos_config_id || false;
        this.state.selectedShop = this.state.shops.find((shop) => shop.id === selectedId) || null;
        this.state.loading = false;
        this.syncMenuVisibility();
    }

    syncMenuVisibility() {
        document.body.classList.toggle("o_laundry_shop_landing", !this.state.selectedShop);
    }

    async selectShop(shop) {
        await this.orm.call("pos.config", "select_laundry_shop", [shop.id]);
        await this.action.doAction(
            {
                type: "ir.actions.client",
                tag: "pos_laundry.landing",
                name: shop.name,
                params: { pos_config_id: shop.id },
            },
            { clearBreadcrumbs: false }
        );
    }

    async backToShops() {
        await this.action.doAction(
            {
                type: "ir.actions.client",
                tag: "pos_laundry.landing",
                name: "Laundry",
                params: {},
            },
            { clearBreadcrumbs: true }
        );
    }

    async openItem(item) {
        if (!this.state.selectedShop) {
            return;
        }
        const action = await this.orm.call(
            "pos.config",
            "action_open_laundry_workspace_item",
            [this.state.selectedShop.id, item.key]
        );
        await this.action.doAction(action, { clearBreadcrumbs: false });
    }
}

registry.category("actions").add("pos_laundry.landing", LaundryLanding);
