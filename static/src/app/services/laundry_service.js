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

            getAllowedCategoryIds() {
                const order = this.getOrder();
                return order?.uiState?.laundry_allowed_pos_category_ids || [];
            },

            getVisibleOrderTypeDomain() {
                return [["active", "=", true], ["is_hidden", "=", false]];
            },

            getVisibleOrderTypeFields() {
                return [
                    "id",
                    "name",
                    "prefix",
                    "icon_class",
                    "icon_color",
                    "sequence",
                    "pos_category_ids",
                    "direct_sale",
                    "billing_method",
                ];
            },

            async getVisibleOrderTypes() {
                const orderTypes = await this.orm.searchRead(
                    "laundry.order.type",
                    this.getVisibleOrderTypeDomain(),
                    this.getVisibleOrderTypeFields()
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
                if (order) {
                    order.uiState = order.uiState || {};
                    order.uiState.is_saved = Boolean(order.uiState.laundry_order_id);
                    order.uiState.status_id = order.uiState.status_id || false;
                    order.uiState.status_name = order.uiState.status_name || (order.uiState.is_saved ? "" : _t("Unsaved"));
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
                if (order) {
                    order.uiState = order.uiState || {};
                    order.uiState.is_saved = false;
                    order.uiState.status_id = false;
                    order.uiState.status_name = _t("Unsaved");
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

            _afterSetLaundryOrderState(order, values = {}) {},

            _setLaundryOrderState(order, values = {}) {
                order.uiState = order.uiState || {};

                const isSaved = Boolean(values.laundry_order_id);

                order.uiState.laundry_order_id = values.laundry_order_id || false;
                order.uiState.laundry_order_name = values.laundry_order_name || "";
                order.uiState.is_saved = isSaved;
                order.uiState.is_existing_laundry_order = isSaved;
                order.uiState.status_id = values.status_id || false;
                order.uiState.status_name = values.status_name || (isSaved ? "" : _t("Unsaved"));
                order.uiState.laundry_order_type_id = values.laundry_order_type_id || false;
                order.uiState.laundry_order_type_name = values.laundry_order_type_name || "";
                order.uiState.laundry_order_type_prefix = values.laundry_order_type_prefix || "";
                order.uiState.laundry_allowed_pos_category_ids = values.allowed_category_ids || [];

                this._afterSetLaundryOrderState(order, values);
            },

            _prepareOrderTypeState(orderType) {
                return {
                    laundry_order_type_id: orderType.id,
                    laundry_order_type_name: orderType.name,
                    laundry_order_type_prefix: orderType.prefix || "",
                    allowed_category_ids: this._normalizeCategoryIds(orderType.pos_category_ids || []),
                };
            },

            selectOrderType(orderType, customer = null) {
                const order = this.prepareOrder(customer);
                if (!order) {
                    return;
                }

                this._setLaundryOrderState(order, this._prepareOrderTypeState(orderType));

                this.pos.selected_laundry_order_type = orderType;
                this.pos.navigate("ProductScreen", { orderUuid: order.uuid });
            },

            _validateLaundryOrderData(order, partner, lines) {
                if (!partner) {
                    throw new Error(_t("Please select a customer first."));
                }
                if (!order.uiState?.laundry_order_type_id) {
                    throw new Error(_t("Please select a laundry order type."));
                }
                if (!lines.length) {
                    throw new Error(_t("Please add at least one product."));
                }
            },

            _extendLaundryOrderData(data, order) {
                return data;
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

                this._validateLaundryOrderData(order, partner, lines);

                const data = {
                    pos_config_id: this.pos.config?.id || false,
                    laundry_order_id: order.uiState?.laundry_order_id || false,
                    partner_id: partner.id,
                    laundry_order_type_id: order.uiState.laundry_order_type_id,
                    notes: order.uiState?.notes || "",
                    lines,
                };

                return this._extendLaundryOrderData(data, order);
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

            _prepareSavedStateValues(result, order) {
                return {
                    laundry_order_id: result.laundry_order_id,
                    laundry_order_name: result.laundry_order_name || order.uiState.laundry_order_name,
                    status_id: result.status_id || false,
                    status_name: result.status_name || "",
                    laundry_order_type_id: order.uiState.laundry_order_type_id,
                    laundry_order_type_name: order.uiState.laundry_order_type_name,
                    laundry_order_type_prefix: order.uiState.laundry_order_type_prefix,
                    allowed_category_ids: order.uiState.laundry_allowed_pos_category_ids,
                };
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
                this._setLaundryOrderState(order, this._prepareSavedStateValues(result, order));

                if (result.direct_sale) {
                    pos.pay?.();
                    return;
                }

                this.resetOrder();
                this.navigateHome();
                return result;
            },

            async payLaundryOrder() {
                const order = this.pos.getOrder();
                const laundryOrderId = order?.uiState?.laundry_order_id;
                if (!laundryOrderId) {
                    return;
                }

                await this.orm.call("laundry.order", "action_create_invoice", [[laundryOrderId]]);

                this.pos.selected_laundry_order_id = laundryOrderId;
                this.pos.navigate?.("LaundryPaymentScreen", {
                    laundryOrderId,
                    customer: order.getPartner?.() || null,
                });
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

            _prepareOpenOrderStateValues(data) {
                return {
                    laundry_order_id: data.id,
                    laundry_order_name: data.name,
                    laundry_order_type_id: data.order_type_id,
                    laundry_order_type_name: data.order_type_name,
                    laundry_order_type_prefix: data.order_type_prefix,
                    status_id: data.status_id || false,
                    status_name: data.status_name || "",
                    allowed_category_ids: data.allowed_category_ids || [],
                };
            },

            async openLaundryOrder(orderId) {
                const data = await this.getLaundryOrderForPos(orderId);
                if (!data) {
                    return;
                }

                const partner = this._getModelRecord("res.partner", data.partner_id);
                const order = await this.createFreshOrder(partner || null);

                this._setLaundryOrderState(order, this._prepareOpenOrderStateValues(data));

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
