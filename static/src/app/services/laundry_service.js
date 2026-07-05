/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { printLaundryReceipt } from "../utils/receipt_service";

function getOrderLines(order) {
    return order?.lines || order?.orderlines || order?.getOrderlines?.() || [];
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
                    order?.getPartner?.() ||
                    order?.get_partner?.() ||
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
                return await orm.call("partner.package", "get_active_packages_for_pos", [partnerId]);
            },

            async getVisibleOrderTypes() {
                const orderTypes = await this.orm.searchRead(
                    "laundry.order.type",
                    [["active", "=", true], ["is_hidden", "=", false]],
                    [
                        "id",
                        "name",
                        "prefix",
                        "icon_class",
                        "icon_color",
                        "sequence",
                        "pos_category_ids",
                        "is_package_sale",
                        "is_package_use",
                    ]
                );
                return orderTypes.sort((a, b) => (a.sequence || 0) - (b.sequence || 0));
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

            async createFreshOrder(customer = null) {
                const currentOrder = this.getOrder();
                if (currentOrder && currentOrder.isEmpty?.()) {
                    this.pos.removeOrder?.(currentOrder, false);
                }
                const order = this.pos.addNewOrder?.() || this.pos.add_new_order?.();
                if (customer) {
                    order.setPartner?.(customer);
                    order.set_partner?.(customer);
                }
                return order;
            },

            _normalizeCategoryIds(ids = []) {
                return ids.map((cat) => (typeof cat === "object" ? cat.id : cat)).filter(Boolean);
            },

            _getModelRecord(modelName, id) {
                if (!id) {
                    return null;
                }
                return this.pos.models?.[modelName]?.get?.(id) || this.pos.data?.models?.[modelName]?.get?.(id) || null;
            },

            _setLaundryOrderState(order, values = {}) {
                order.uiState.laundry_order_id = values.laundry_order_id || false;
                order.uiState.laundry_order_name = values.laundry_order_name || "";
                order.uiState.is_existing_laundry_order = Boolean(values.laundry_order_id);
                order.uiState.laundry_order_type_id = values.laundry_order_type_id || false;
                order.uiState.laundry_order_type_name = values.laundry_order_type_name || "";
                order.uiState.laundry_order_type_prefix = values.laundry_order_type_prefix || "";
                order.uiState.laundry_allowed_pos_category_ids = values.allowed_category_ids || [];
                order.uiState.is_package_sale = Boolean(values.is_package_sale);
                order.uiState.is_package_usage = Boolean(values.is_package_usage);
                order.uiState.partner_package_id = values.partner_package_id || false;
                order.uiState.package_rule_id = values.package_rule_id || false;
                order.uiState.package_rule_name = values.package_rule_name || "";
            },

            selectOrderType(orderType, customer = null) {
                const order = this.prepareOrder(customer);
                if (!order) {
                    return;
                }

                const allowedCategoryIds = this._normalizeCategoryIds(orderType.pos_category_ids || []);
                this._setLaundryOrderState(order, {
                    laundry_order_type_id: orderType.id,
                    laundry_order_type_name: orderType.name,
                    laundry_order_type_prefix: orderType.prefix || "",
                    allowed_category_ids: allowedCategoryIds,
                    is_package_sale: Boolean(orderType.is_package_sale),
                    is_package_usage: Boolean(orderType.is_package_use),
                });

                this.pos.selected_laundry_order_type = orderType;
                this.pos.navigate("ProductScreen", { orderUuid: order.uuid });
            },

            async selectPackage(pkg, customer = null) {
                const order = await this.createFreshOrder(customer);
                if (!order) {
                    return;
                }

                this._setLaundryOrderState(order, {
                    laundry_order_type_id: false,
                    laundry_order_type_name: _t("Package Usage"),
                    laundry_order_type_prefix: "",
                    allowed_category_ids: pkg.allowed_category_ids || [],
                    is_package_sale: false,
                    is_package_usage: true,
                    partner_package_id: pkg.id,
                    package_rule_id: pkg.package_rule_id?.[0] || false,
                    package_rule_name: pkg.package_rule_name || pkg.package_rule_id?.[1] || "",
                });

                this.pos.navigate("ProductScreen", { orderUuid: order.uuid });
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
                if (!order.uiState?.laundry_order_type_id && !order.uiState?.is_package_usage) {
                    throw new Error(_t("Please select a laundry order type."));
                }
                if (!lines.length) {
                    throw new Error(_t("Please add at least one product."));
                }

                return {
                    pos_config_id: this.pos.config?.id || false,
                    laundry_order_id: order.uiState?.laundry_order_id || false,
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
                return await orm.call("laundry.order", "process_pos_laundry_order", [data]);
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
                    await printLaundryReceipt(printer, result.receipt, dialog);
                }
            },

            resetOrder() {
                const order = this.getOrder();
                if (order) {
                    pos.removeOrder?.(order, false);
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
                order.uiState.laundry_order_name = result.laundry_order_name || order.uiState.laundry_order_name;

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

            async getCustomerOrdersByStatus(partnerId) {
                if (!partnerId) {
                    return [];
                }
                return await this.orm.call("laundry.order", "get_customer_orders_by_status_for_pos", [partnerId]);
            },

            async getLaundryOrderForPos(orderId) {
                if (!orderId) {
                    return null;
                }
                return await this.orm.call("laundry.order", "get_laundry_order_for_pos", [orderId]);
            },

            async openLaundryOrder(orderId) {
                const data = await this.getLaundryOrderForPos(orderId);
                if (!data) {
                    return;
                }

                const partner = this._getModelRecord("res.partner", data.partner_id);
                const order = await this.createFreshOrder(partner || null);

                this._setLaundryOrderState(order, {
                    laundry_order_id: data.id,
                    laundry_order_name: data.name,
                    laundry_order_type_id: data.order_type_id,
                    laundry_order_type_name: data.order_type_name,
                    laundry_order_type_prefix: data.order_type_prefix,
                    allowed_category_ids: data.allowed_category_ids || [],
                    is_package_sale: false,
                    is_package_usage: Boolean(data.is_package),
                    partner_package_id: data.partner_package_id || false,
                    package_rule_id: data.package_rule_id || false,
                    package_rule_name: data.package_rule_name || "",
                });

                this.pos.selected_laundry_order_type = {
                    id: data.order_type_id,
                    name: data.order_type_name,
                    prefix: data.order_type_prefix,
                    pos_category_ids: data.allowed_category_ids || [],
                };

                for (const line of data.lines || []) {
                    const product = this._getModelRecord("product.product", line.product_id);
                    if (!product) {
                        continue;
                    }
                    await this.pos.addLineToCurrentOrder(
                        {
                            product_id: product,
                            product_tmpl_id: product.product_tmpl_id,
                            qty: line.qty,
                            price_unit: line.price_unit,
                        },
                        { force: true },
                        false
                    );
                }

                this.pos.navigate("ProductScreen", { orderUuid: order.uuid });
            },
        };
    },
};

registry.category("services").add("laundry", laundryService);
