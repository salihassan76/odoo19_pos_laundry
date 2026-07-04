/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { printLaundryReceipt } from "../utils/receipt_service";

function getOrderLines(order) {
    return order?.lines || order?.orderlines || [];
}

function getLineProduct(line) {
    return line.product_id || line.product || line.get_product?.();
}

function getLineQty(line) {
    return line.qty || line.quantity || line.get_quantity?.() || 1;
}

function getLinePrice(line) {
    return line.price_unit || line.price || line.get_unit_price?.() || 0;
}

export const laundryService = {
    dependencies: ["pos", "orm", "dialog", "printer"],

    start(env, { pos, orm, dialog, printer }) {
        return {
            pos,
            orm,
            dialog,
            printer,

            isEnabled() {
                return Boolean(pos.config?.enable_laundry_workflow);
            },

            getOrder() {
                return pos.getOrder?.() || pos.get_order?.();
            },

            getPartner() {
                const order = this.getOrder();

                return (
                    order?.get_partner?.() ||
                    order?.getPartner?.() ||
                    order?.partner_id ||
                    pos.selected_customer ||
                    null
                );
            },

            getOrderType() {
                const order = this.getOrder();

                return {
                    id: order?.uiState?.laundry_order_type_id || false,
                    name: order?.uiState?.laundry_order_type_name || "",
                    prefix: order?.uiState?.laundry_order_type_prefix || "",
                };
            },

            isPackageSale() {
                const order = this.getOrder();
                return Boolean(order?.uiState?.is_package_sale);
            },

            isPackageUsage() {
                const order = this.getOrder();
                return Boolean(order?.uiState?.is_package_usage);
            },

            getCurrentPackageId() {
                const order = this.getOrder();
                return order?.uiState?.partner_package_id || false;
            },

            getAllowedCategoryIds() {
                const order = this.getOrder();
                return order?.uiState?.laundry_allowed_pos_category_ids || [];
            },

            async getActivePackages(partnerId) {
                if (!partnerId) {
                    return [];
                }

                return await orm.call(
                    "partner.package",
                    "get_active_packages_for_pos",
                    [partnerId]
                );
            },
            async getVisibleOrderTypes() {
                const orderTypes = await this.orm.searchRead(
                    "laundry.order.type",
                    [
                        ["active", "=", true],
                        ["is_hidden", "=", false],
                    ],
                    [
                        "id",
                        "name",
                        "icon_class",
                        "icon_color",
                        "sequence",
                        "pos_category_ids",
                        "is_package_sale",
                    ]
                );

                return orderTypes.sort((a, b) => {
                    return (a.sequence || 0) - (b.sequence || 0);
                });
            },
            prepareOrder(customer = null) {
                let order = this.getOrder();

                if (!order) {
                    order = this.pos.addNewOrder?.() || this.pos.add_new_order?.();
                }

                if (order && customer) {
                    order.setPartner?.(customer);
                    order.set_partner?.(customer);
                }

                return order;
            },

            selectOrderType(orderType, customer = null) {
                const order = this.prepareOrder(customer);

                if (!order) {
                    return;
                }

                const allowedCategoryIds = (orderType.pos_category_ids || []).map((cat) =>
                    typeof cat === "object" ? cat.id : cat
                );

                order.uiState.laundry_order_type_id = orderType.id;
                order.uiState.laundry_order_type_name = orderType.name;
                order.uiState.laundry_order_type_prefix = orderType.prefix || "";
                order.uiState.laundry_allowed_pos_category_ids = allowedCategoryIds;

                order.uiState.is_package_sale = Boolean(orderType.is_package_sale);
                order.uiState.is_package_usage = false;
                order.uiState.partner_package_id = false;
                order.uiState.package_rule_id = false;

                this.pos.selected_laundry_order_type = orderType;

                this.pos.navigate("ProductScreen", {
                    orderUuid: order.uuid,
                });
            },

            buildLaundryOrderData() {
                const order = this.getOrder();

                if (!order) {
                    throw new Error(_t("No active POS order found."));
                }

                const partner = this.getPartner();

                const lines = getOrderLines(order)
                    .map((line) => {
                        const product = getLineProduct(line);

                        return {
                            product_id: product?.id || false,
                            qty: getLineQty(line),
                            price_unit: getLinePrice(line),
                        };
                    })
                    .filter((line) => line.product_id);

                if (!partner) {
                    throw new Error(_t("Please select a customer first."));
                }

                if (!order.uiState?.laundry_order_type_id) {
                    throw new Error(_t("Please select a laundry order type."));
                }

                if (!lines.length) {
                    throw new Error(_t("Please add at least one product."));
                }

                return {
                    pos_config_id: this.pos.config?.id || false,
                    

                    partner_id: partner.id,
                    laundry_order_type_id: order.uiState.laundry_order_type_id,

                    package_rule_id: order.uiState?.package_rule_id || false,
                    partner_package_id: order.uiState?.partner_package_id || false,

                    is_package_sale: Boolean(order.uiState?.is_package_sale),
                    is_package_usage: Boolean(order.uiState?.is_package_usage),

                    notes: order.uiState?.notes || "",

                    lines,
                };
            },

            async saveOrder() {
                const data = this.buildLaundryOrderData();

                return await orm.call(
                    "laundry.order",
                    "process_pos_laundry_order",
                    [data]
                );
            },

            async handleReceipt(result) {
                if (!result?.receipt) {
                    return;
                }

                if (result.show_receipt_preview) {
                    dialog.add(AlertDialog, {
                        title: _t("Receipt Preview"),
                        body: JSON.stringify(result.receipt, null, 2),
                    });
                }

                if (result.direct_print) {
                    await printLaundryReceipt(
                        printer,
                        result.receipt,
                        dialog
                    );
                }
            },

            resetOrder() {
                const order = this.getOrder();

                if (order) {
                    pos.removeOrder?.(order);
                    pos.remove_order?.(order);
                }

                pos.addNewOrder?.();
                pos.add_new_order?.();
            },

            navigateHome() {
                pos.navigate?.("pos_homescreen");
            },

            async saveAndHandleResult() {
                if (!this.isEnabled()) {
                    return;
                }

                const order = this.getOrder();
                if (!order) {
                    return;
                }

                const result = await this.saveOrder();

                if (!result) {
                    return;
                }

                await this.handleReceipt(result);

                order.uiState.laundry_order_id = result.laundry_order_id;

                if (result.direct_sale) {
                    pos.pay?.();
                    return;
                }

                this.resetOrder();
                this.navigateHome();

                return result;
            },
            cancelOrder() {
                const order = this.getOrder();

                if (order) {
                    this.resetOrder();
                }

                this.pos.navigate?.("pos_customerscreen");
            },
        };
    },
};

registry.category("services").add("laundry", laundryService);