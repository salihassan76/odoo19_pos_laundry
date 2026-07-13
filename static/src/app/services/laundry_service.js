/** @odoo-module **/

import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { printLaundryReceipt } from "../utils/receipt_service";
import {
    setLaundryVisibility,
    traceLaundryState,
} from "../utils/laundry_visibility";


function getOrderLines(order) {
    return Array.from(
        order?.lines ||
        order?.orderlines ||
        order?.getOrderlines?.() ||
        order?.get_orderlines?.() ||
        []
    );
}


function getLineProduct(line) {
    return (
        line?.product_id ||
        line?.product ||
        line?.get_product?.() ||
        null
    );
}


function getLineQty(line) {
    return (
        line?.qty ??
        line?.quantity ??
        line?.getQuantity?.() ??
        line?.get_quantity?.() ??
        1
    );
}


function getLinePrice(line) {
    return (
        line?.price_unit ??
        line?.price ??
        line?.getUnitPrice?.() ??
        line?.get_unit_price?.() ??
        0
    );
}


export const laundryService = {
    dependencies: [
        "pos",
        "orm",
        "dialog",
        "printer",
    ],

    start(env, { pos, orm, dialog, printer }) {
        return {
            pos,
            orm,
            dialog,
            printer,

            // -------------------------------------------------------------
            // Basic helpers
            // -------------------------------------------------------------

            isEnabled() {
                return Boolean(
                    this.pos.config
                        ?.enable_laundry_workflow
                );
            },

            getOrder() {
                return (
                    this.pos.getOrder?.() ||
                    this.pos.get_order?.() ||
                    null
                );
            },

            setCurrentOrder(order) {
                if (!order) {
                    return;
                }

                if (this.pos.setOrder) {
                    this.pos.setOrder(order);
                } else if (this.pos.set_order) {
                    this.pos.set_order(order);
                }
            },

            removeOrder(order) {
                if (!order) {
                    return;
                }

                if (this.pos.removeOrder) {
                    this.pos.removeOrder(
                        order,
                        false
                    );
                } else if (
                    this.pos.remove_order
                ) {
                    this.pos.remove_order(order);
                }
            },

            addNewOrder() {
                return (
                    this.pos.addNewOrder?.() ||
                    this.pos.add_new_order?.() ||
                    null
                );
            },

            setOrderPartner(
                order,
                partner
            ) {
                if (!order || !partner) {
                    return;
                }

                if (order.setPartner) {
                    order.setPartner(partner);
                } else if (
                    order.set_partner
                ) {
                    order.set_partner(partner);
                }
            },

            getPartner() {
                const order = this.getOrder();

                return (
                    order?.getPartner?.() ||
                    order?.get_partner?.() ||
                    order?.partner_id ||
                    this.pos.selected_customer ||
                    null
                );
            },

            getOrderType() {
                const order = this.getOrder();

                return {
                    id:
                        order?.uiState
                            ?.laundry_order_type_id ||
                        false,

                    name:
                        order?.uiState
                            ?.laundry_order_type_name ||
                        "",

                    prefix:
                        order?.uiState
                            ?.laundry_order_type_prefix ||
                        "",
                };
            },

            getAllowedCategoryIds() {
                const order =
                    this.getOrder();

                return this._normalizeCategoryIds(
                    order?.uiState
                        ?.laundry_allowed_pos_category_ids ||
                    []
                );
            },

            // -------------------------------------------------------------
            // Order types
            // -------------------------------------------------------------

            getVisibleOrderTypeDomain() {
                return [
                    ["active", "=", true],
                    ["is_hidden", "=", false],
                ];
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
                    "allow_pay",
                ];
            },

            async getVisibleOrderTypes() {
                const orderTypes =
                    await this.orm.searchRead(
                        "laundry.order.type",
                        this
                            .getVisibleOrderTypeDomain(),
                        this
                            .getVisibleOrderTypeFields()
                    );

                return orderTypes.sort(
                    (a, b) =>
                        (a.sequence || 0) -
                        (b.sequence || 0)
                );
            },

            // -------------------------------------------------------------
            // POS order creation
            // -------------------------------------------------------------

            prepareOrder(
                customer = null
            ) {
                let order = this.getOrder();

                if (!order) {
                    order = this.addNewOrder();
                }

                if (!order) {
                    return null;
                }

                this.setCurrentOrder(order);

                if (customer) {
                    this.setOrderPartner(
                        order,
                        customer
                    );
                }

                order.uiState =
                    order.uiState || {};

                order.uiState.is_saved =
                    Boolean(
                        order.uiState
                            .laundry_order_id
                    );

                order.uiState.status_id =
                    order.uiState.status_id ||
                    false;

                order.uiState.status_name =
                    order.uiState.status_name ||
                    (
                        order.uiState.is_saved
                            ? ""
                            : _t("Unsaved")
                    );

                return order;
            },

            async createFreshOrder(
                customer = null
            ) {
                const currentOrder =
                    this.getOrder();

                if (
                    currentOrder &&
                    currentOrder.isEmpty?.()
                ) {
                    this.removeOrder(
                        currentOrder
                    );
                }

                const order =
                    this.addNewOrder();

                if (!order) {
                    throw new Error(
                        _t(
                            "Unable to create a new POS order."
                        )
                    );
                }

                this.setCurrentOrder(order);

                if (customer) {
                    this.setOrderPartner(
                        order,
                        customer
                    );
                }

                order.uiState =
                    order.uiState || {};

                order.uiState.is_saved =
                    false;

                order.uiState
                    .is_existing_laundry_order =
                    false;

                order.uiState.status_id =
                    false;

                order.uiState.status_name =
                    _t("Unsaved");

                order.uiState
                    .laundry_has_changes =
                    false;

                return order;
            },

            // -------------------------------------------------------------
            // Data normalization
            // -------------------------------------------------------------

            _normalizeCategoryIds(
                values = []
            ) {
                return [
                    ...new Set(
                        (values || [])
                            .map((value) => {
                                if (
                                    typeof value ===
                                    "number"
                                ) {
                                    return value;
                                }

                                if (
                                    typeof value ===
                                    "string"
                                ) {
                                    return Number(
                                        value
                                    );
                                }

                                if (
                                    Array.isArray(
                                        value
                                    )
                                ) {
                                    return Number(
                                        value[0]
                                    );
                                }

                                return Number(
                                    value?.id
                                );
                            })
                            .filter(
                                (value) =>
                                    Number.isInteger(
                                        value
                                    ) &&
                                    value > 0
                            )
                    ),
                ];
            },

            _getModelRecord(
                modelName,
                id
            ) {
                if (!id) {
                    return null;
                }

                return (
                    this.pos.models
                        ?.[modelName]
                        ?.get?.(id) ||
                    this.pos.data
                        ?.models
                        ?.[modelName]
                        ?.get?.(id) ||
                    null
                );
            },

            // -------------------------------------------------------------
            // Laundry order state
            // -------------------------------------------------------------

            /*
             * Extension hook used by optional addons,
             * including pos_laundry_packages.
             */
            _afterSetLaundryOrderState(
                order,
                values = {}
            ) {},

            _setLaundryOrderState(
                order,
                values = {}
            ) {
                if (!order) {
                    return;
                }

                order.uiState =
                    order.uiState || {};

                const isSaved =
                    Boolean(
                        values
                            .laundry_order_id
                    );

                order.uiState
                    .laundry_order_id =
                    values
                        .laundry_order_id ||
                    false;

                order.uiState
                    .laundry_order_name =
                    values
                        .laundry_order_name ||
                    "";

                order.uiState.is_saved =
                    isSaved;

                order.uiState
                    .is_existing_laundry_order =
                    isSaved;

                /*
                 * Compatibility fields.
                 */
                order.uiState.status_id =
                    values.status_id ||
                    values
                        .laundry_status_id ||
                    false;

                order.uiState.status_name =
                    values.status_name ||
                    values
                        .laundry_status_name ||
                    (
                        isSaved
                            ? ""
                            : _t("Unsaved")
                    );

                /*
                 * Structured order-status state.
                 */
                order.uiState
                    .laundry_status_id =
                    values
                        .laundry_status_id ||
                    values.status_id ||
                    false;

                order.uiState
                    .laundry_status_name =
                    values
                        .laundry_status_name ||
                    values.status_name ||
                    "";

                order.uiState
                    .laundry_status =
                    values.laundry_status ||
                    {};

                /*
                 * Payment-status state.
                 */
                order.uiState
                    .laundry_payment_status_id =
                    values
                        .laundry_payment_status_id ||
                    false;

                order.uiState
                    .laundry_payment_status_name =
                    values
                        .laundry_payment_status_name ||
                    "";

                /*
                 * Order type.
                 */
                order.uiState
                    .laundry_order_type_id =
                    values
                        .laundry_order_type_id ||
                    false;

                order.uiState
                    .laundry_order_type_name =
                    values
                        .laundry_order_type_name ||
                    "";

                order.uiState
                    .laundry_order_type_prefix =
                    values
                        .laundry_order_type_prefix ||
                    "";

                order.uiState
                    .laundry_allowed_pos_category_ids =
                    this._normalizeCategoryIds(
                        values
                            .allowed_category_ids ||
                        values
                            .laundry_allowed_pos_category_ids ||
                        []
                    );

                if (
                        values.laundry_allow_pay !== undefined ||
                        values.allow_pay !== undefined
                    ) {
                        order.uiState
                            .laundry_allow_pay =
                            (
                                values.laundry_allow_pay ??
                                values.allow_pay
                            ) !== false;
                    }
                

                /*
                 * Financial state.
                 */
                order.uiState
                    .laundry_total_amount =
                    Number(
                        values
                            .laundry_total_amount ||
                        0
                    );

                order.uiState
                    .laundry_paid_amount =
                    Number(
                        values
                            .laundry_paid_amount ||
                        0
                    );

                order.uiState
                    .laundry_balance =
                    Number(
                        values
                            .laundry_balance ||
                        0
                    );

                order.uiState
                    .laundry_refundable_amount =
                    Number(
                        values
                            .laundry_refundable_amount ||
                        0
                    );

                /*
                 * Editing state.
                 */
                order.uiState
                    .laundry_has_changes =
                    Boolean(
                        values
                            .laundry_has_changes
                    );

                order.uiState
                    .return_to_laundry_home =
                    Boolean(
                        values
                            .return_to_laundry_home
                    );

                this._afterSetLaundryOrderState(
                    order,
                    values
                );
            },

            _prepareOrderTypeState(
                orderType
            ) {
                return {
                    laundry_order_type_id:
                        orderType.id,

                    laundry_order_type_name:
                        orderType.name,

                    laundry_order_type_prefix:
                        orderType.prefix ||
                        "",

                    allowed_category_ids:
                        this._normalizeCategoryIds(
                            orderType
                                .pos_category_ids ||
                            []
                        ),
                    allow_pay:
                        orderType.allow_pay !== false,
                };
            },

            async selectOrderType(
                orderType,
                customer = null
            ) {
                const currentOrder =
                    this.getOrder();

                const hasExistingContext =
                    Boolean(
                        currentOrder?.uiState
                            ?.laundry_order_id ||
                        currentOrder?.uiState
                            ?.laundry_order_type_id ||
                        currentOrder?.uiState
                            ?.is_existing_laundry_order
                    );

                const order =
                    hasExistingContext
                        ? await this
                            .createFreshOrder(
                                customer
                            )
                        : this.prepareOrder(
                            customer
                        );

                if (!order) {
                    return;
                }

                const stateValues =
                    this._prepareOrderTypeState(
                        orderType
                    );

                this._setLaundryOrderState(
                    order,
                    stateValues
                );

                this.pos
                    .selected_laundry_order_type =
                    {
                        ...orderType,

                        pos_category_ids:
                            this._normalizeCategoryIds(
                                orderType
                                    .pos_category_ids ||
                                []
                            ),
                    };

                this.clearCategorySelection(
                    order
                );

                this.setCurrentOrder(
                    order
                );

                this.pos.navigate(
                    "ProductScreen",
                    {
                        orderUuid:
                            order.uuid,
                    }
                );
            },

            clearCategorySelection(
                order = null
            ) {
                this.pos.selectedCategory =
                    undefined;

                this.pos.selectedCategoryId =
                    undefined;

                this.pos.selected_category =
                    undefined;

                this.pos.selected_category_id =
                    undefined;

                this.pos.productListCategoryId =
                    undefined;

                if (order?.uiState) {
                    order.uiState
                        .laundry_start_category_opened =
                        false;
                }
            },

            // -------------------------------------------------------------
            // Validation and payload building
            // -------------------------------------------------------------

            _validateLaundryOrderData(
                order,
                partner,
                lines
            ) {
                if (!partner) {
                    throw new Error(
                        _t(
                            "Please select a customer first."
                        )
                    );
                }

                if (
                    !order.uiState
                        ?.laundry_order_type_id
                ) {
                    throw new Error(
                        _t(
                            "Please select a laundry order type."
                        )
                    );
                }

                if (!lines.length) {
                    throw new Error(
                        _t(
                            "Please add at least one product."
                        )
                    );
                }
            },

            /*
             * Extension hook used by optional addons.
             */
            _extendLaundryOrderData(
                data,
                order
            ) {
                return data;
            },

            buildLaundryOrderData() {
                const order =
                    this.getOrder();

                if (!order) {
                    throw new Error(
                        _t(
                            "No active POS order found."
                        )
                    );
                }

                const partner =
                    this.getPartner();

                const lines =
                    getOrderLines(order)
                        .map((line) => {
                            const product =
                                getLineProduct(
                                    line
                                );

                            return {
                                product_id:
                                    product?.id ||
                                    false,

                                qty:
                                    getLineQty(
                                        line
                                    ),

                                price_unit:
                                    getLinePrice(
                                        line
                                    ),
                            };
                        })
                        .filter(
                            (line) =>
                                line.product_id
                        );

                this._validateLaundryOrderData(
                    order,
                    partner,
                    lines
                );

                const data = {
                    pos_config_id:
                        this.pos.config?.id ||
                        false,

                    laundry_order_id:
                        order.uiState
                            ?.laundry_order_id ||
                        false,

                    partner_id:
                        partner.id,

                    laundry_order_type_id:
                        order.uiState
                            .laundry_order_type_id,

                    notes:
                        order.uiState
                            ?.notes ||
                        "",

                    lines,
                };

                return this._extendLaundryOrderData(
                    data,
                    order
                );
            },

            async saveOrder() {
                const data =
                    this.buildLaundryOrderData();

                return await this.orm.call(
                    "laundry.order",
                    "process_pos_laundry_order",
                    [data]
                );
            },

            // -------------------------------------------------------------
            // Receipt handling
            // -------------------------------------------------------------

            async handleReceipt(result) {
                if (!result?.receipt) {
                    return;
                }

                if (
                    result
                        .show_receipt_preview
                ) {
                    this.dialog.add(
                        AlertDialog,
                        {
                            title:
                                _t(
                                    "Receipt Preview"
                                ),

                            body:
                                JSON.stringify(
                                    result.receipt,
                                    null,
                                    2
                                ),
                        }
                    );
                }

                if (result.direct_print) {
                    await printLaundryReceipt(
                        this.printer,
                        result.receipt,
                        this.dialog
                    );
                }
            },

            async printSavedLaundryOrder(
                laundryOrderId = null
            ) {
                const order =
                    this.getOrder();

                const orderId =
                    laundryOrderId ||
                    order?.uiState
                        ?.laundry_order_id;

                if (!orderId) {
                    throw new Error(
                        _t(
                            "Please save the laundry order before printing."
                        )
                    );
                }

                const result =
                    await this.orm.call(
                        "laundry.order",
                        "action_get_receipt_data",
                        [[orderId]]
                    );

                if (!result?.receipt) {
                    throw new Error(
                        _t(
                            "No receipt data was returned."
                        )
                    );
                }

                await printLaundryReceipt(
                    this.printer,
                    result.receipt,
                    this.dialog
                );

                return result;
            },

            // -------------------------------------------------------------
            // Navigation and order reset
            // -------------------------------------------------------------

            resetOrder() {
                const order =
                    this.getOrder();

                if (order) {
                    this.removeOrder(order);
                }

                const newOrder =
                    this.addNewOrder();

                if (newOrder) {
                    this.setCurrentOrder(
                        newOrder
                    );
                }

                return newOrder;
            },

            backToLaundryHome() {
                const currentOrder =
                    this.getOrder();

                const customer =
                    currentOrder
                        ?.getPartner?.() ||
                    currentOrder
                        ?.get_partner?.() ||
                    currentOrder
                        ?.partner_id ||
                    this.pos
                        .selected_customer ||
                    null;

                console.log(
                    "[Laundry:Navigation] Back to laundry home",
                    {
                        orderUuid:
                            currentOrder?.uuid ||
                            false,

                        laundryOrderId:
                            currentOrder
                                ?.uiState
                                ?.laundry_order_id ||
                            false,

                        customerId:
                            customer?.id ||
                            false,
                    }
                );

                if (currentOrder) {
                    this.removeOrder(
                        currentOrder
                    );
                }

                const newOrder =
                    this.addNewOrder();

                if (newOrder) {
                    this.setCurrentOrder(
                        newOrder
                    );

                    if (customer) {
                        this.setOrderPartner(
                            newOrder,
                            customer
                        );
                    }
                }

                this.pos
                    .selected_laundry_order_id =
                    false;

                this.pos
                    .selected_laundry_order_type =
                    null;

                this.pos.selected_customer =
                    customer;

                this.clearCategorySelection(
                    newOrder
                );

                this.pos.navigate?.(
                    "pos_homescreen",
                    {
                        customer,
                    }
                );
            },

            navigateHome() {
                this.pos.navigate?.(
                    "pos_homescreen"
                );
            },

            discardCurrentOrder() {
                const currentOrder =
                    this.getOrder();

                const customer =
                    currentOrder
                        ?.getPartner?.() ||
                    currentOrder
                        ?.get_partner?.() ||
                    currentOrder
                        ?.partner_id ||
                    this.pos
                        .selected_customer ||
                    null;

                if (currentOrder) {
                    this.removeOrder(
                        currentOrder
                    );
                }

                const newOrder =
                    this.addNewOrder();

                if (newOrder) {
                    this.setCurrentOrder(
                        newOrder
                    );

                    if (customer) {
                        this.setOrderPartner(
                            newOrder,
                            customer
                        );
                    }
                }

                this.pos
                    .selected_laundry_order_id =
                    false;

                this.pos
                    .selected_laundry_order_type =
                    null;

                this.pos.selected_customer =
                    customer;

                this.clearCategorySelection(
                    newOrder
                );

                this.pos.navigate?.(
                    "pos_homescreen",
                    {
                        customer,
                    }
                );

                return true;
            },

            // -------------------------------------------------------------
            // State preparation
            // -------------------------------------------------------------

            _prepareOpenOrderStateValues(
                data
            ) {
                return {
                    laundry_order_id:
                        data.id || false,

                    laundry_order_name:
                        data.name || "",

                    laundry_order_type_id:
                        data
                            .order_type_id ||
                        false,

                    laundry_order_type_name:
                        data
                            .order_type_name ||
                        "",

                    laundry_order_type_prefix:
                        data
                            .order_type_prefix ||
                        "",
                    laundry_allow_pay:
                        data.allow_pay !== false,

                    allowed_category_ids:
                        this._normalizeCategoryIds(
                            data
                                .allowed_category_ids ||
                            []
                        ),

                    laundry_status_id:
                        data.status_id ||
                        false,

                    laundry_status_name:
                        data.status_name ||
                        "",

                    laundry_status:
                        data.status || {},

                    laundry_payment_status_id:
                        data
                            .payment_status_id ||
                        false,

                    laundry_payment_status_name:
                        data
                            .payment_status_name ||
                        "",

                    laundry_total_amount:
                        Number(
                            data.total_amount ||
                            0
                        ),

                    laundry_paid_amount:
                        Number(
                            data.paid_amount ||
                            0
                        ),

                    laundry_balance:
                        Number(
                            data.balance ||
                            0
                        ),

                    laundry_refundable_amount:
                        Number(
                            data
                                .refundable_amount ||
                            0
                        ),

                    laundry_has_changes:
                        false,

                    return_to_laundry_home:
                        true,

                    is_existing_laundry_order:
                        true,
                };
            },

            _prepareSavedStateValues(
                result,
                order
            ) {
                return {
                    laundry_order_id:
                        result
                            .laundry_order_id,

                    laundry_order_name:
                        result
                            .laundry_order_name ||
                        order.uiState
                            .laundry_order_name,

                    laundry_status_id:
                        result.status_id ||
                        false,

                    laundry_status_name:
                        result.status_name ||
                        "",

                    laundry_status:
                        result.status || {},

                    laundry_payment_status_id:
                        result
                            .payment_status_id ||
                        false,

                    laundry_payment_status_name:
                        result
                            .payment_status_name ||
                        "",

                    laundry_order_type_id:
                        order.uiState
                            .laundry_order_type_id,

                    laundry_order_type_name:
                        order.uiState
                            .laundry_order_type_name,

                    laundry_order_type_prefix:
                        order.uiState
                            .laundry_order_type_prefix,
                    
                    laundry_allow_pay:
                        order.uiState
                            .laundry_allow_pay !== false,

                    allowed_category_ids:
                        order.uiState
                            .laundry_allowed_pos_category_ids,

                    laundry_total_amount:
                        Number(
                            result
                                .total_amount ||
                            order
                                .getTotalWithTax?.() ||
                            0
                        ),

                    laundry_paid_amount:
                        Number(
                            result
                                .paid_amount ||
                            0
                        ),

                    laundry_balance:
                        Number(
                            result.balance ||
                            0
                        ),

                    laundry_refundable_amount:
                        Number(
                            result
                                .refundable_amount ||
                            0
                        ),

                    laundry_has_changes:
                        false,

                    return_to_laundry_home:
                        true,
                };
            },

            // -------------------------------------------------------------
            // Snapshot and change detection
            // -------------------------------------------------------------

            createLaundryOrderSnapshot(
                order
            ) {
                if (!order) {
                    return null;
                }

                const partner =
                    order.getPartner?.() ||
                    order.get_partner?.() ||
                    order.partner_id ||
                    null;

                const lines =
                    getOrderLines(order)
                        .map((line) => {
                            const product =
                                getLineProduct(
                                    line
                                );

                            return {
                                product_id:
                                    product?.id ||
                                    false,

                                qty:
                                    Number(
                                        getLineQty(
                                            line
                                        ) || 0
                                    ),

                                price_unit:
                                    Number(
                                        getLinePrice(
                                            line
                                        ) || 0
                                    ),
                            };
                        })
                        .filter(
                            (line) =>
                                line.product_id
                        )
                        .sort((a, b) => {
                            if (
                                a.product_id !==
                                b.product_id
                            ) {
                                return (
                                    a.product_id -
                                    b.product_id
                                );
                            }

                            if (
                                a.qty !== b.qty
                            ) {
                                return (
                                    a.qty -
                                    b.qty
                                );
                            }

                            return (
                                a.price_unit -
                                b.price_unit
                            );
                        });

                return {
                    partner_id:
                        partner?.id ||
                        false,

                    laundry_order_type_id:
                        order.uiState
                            ?.laundry_order_type_id ||
                        false,

                    notes:
                        order.uiState
                            ?.notes ||
                        "",

                    lines,
                };
            },

            hasLaundryOrderChanges(
                order
            ) {
                if (!order) {
                    return false;
                }

                const originalSnapshot =
                    order.uiState
                        ?.laundry_original_snapshot;

                if (!originalSnapshot) {
                    return false;
                }

                const currentSnapshot =
                    this
                        .createLaundryOrderSnapshot(
                            order
                        );

                const hasChanges =
                    JSON.stringify(
                        currentSnapshot
                    ) !==
                    JSON.stringify(
                        originalSnapshot
                    );

                order.uiState
                    .laundry_has_changes =
                    hasChanges;

                return hasChanges;
            },

            // -------------------------------------------------------------
            // Save / update
            // -------------------------------------------------------------

            async saveAndHandleResult() {
                if (!this.isEnabled()) {
                    return;
                }

                const order =
                    this.getOrder();

                if (!order) {
                    return;
                }

                const result =
                    await this.saveOrder();

                if (!result) {
                    return;
                }

                await this.handleReceipt(
                    result
                );

                this._setLaundryOrderState(
                    order,
                    this
                        ._prepareSavedStateValues(
                            result,
                            order
                        )
                );

                order.uiState
                    .laundry_original_snapshot =
                    this
                        .createLaundryOrderSnapshot(
                            order
                        );

                order.uiState
                    .laundry_has_changes =
                    false;

                if (result.direct_sale) {
                    this.pos.pay?.();
                    return result;
                }

                this.resetOrder();
                this.navigateHome();

                return result;
            },

            // -------------------------------------------------------------
            // Payment
            // -------------------------------------------------------------

            async payLaundryOrder() {
                const order =
                    this.getOrder();

                const laundryOrderId =
                    order?.uiState
                        ?.laundry_order_id;

                if (!laundryOrderId) {
                    throw new Error(
                        _t(
                            "Please save the laundry order before receiving payment."
                        )
                    );
                }

                await this.orm.call(
                    "laundry.order",
                    "action_create_invoice",
                    [[laundryOrderId]]
                );

                this.pos
                    .selected_laundry_order_id =
                    laundryOrderId;

                this.pos.navigate?.(
                    "LaundryPaymentScreen",
                    {
                        laundryOrderId,

                        customer:
                            order
                                .getPartner?.() ||
                            order
                                .get_partner?.() ||
                            null,
                    }
                );
            },

            // -------------------------------------------------------------
            // Refund
            // -------------------------------------------------------------

            async refundLaundryOrder() {
                const order =
                    this.getOrder();

                const laundryOrderId =
                    order?.uiState
                        ?.laundry_order_id;

                if (!laundryOrderId) {
                    throw new Error(
                        _t(
                            "Please save the laundry order before refunding."
                        )
                    );
                }

                const policy =
                    this.getActionPolicy(
                        order
                    );

                if (!policy.canRefund) {
                    throw new Error(
                        _t(
                            "This laundry order cannot be refunded."
                        )
                    );
                }

                const result =
                    await this.orm.call(
                        "laundry.order",
                        "action_refund_from_pos",
                        [[laundryOrderId]]
                    );

                if (!result?.success) {
                    throw new Error(
                        _t(
                            "The laundry order refund failed."
                        )
                    );
                }

                this._setLaundryOrderState(
                    order,
                    {
                        laundry_order_id:
                            laundryOrderId,

                        laundry_order_name:
                            order.uiState
                                .laundry_order_name,

                        laundry_order_type_id:
                            order.uiState
                                .laundry_order_type_id,

                        laundry_order_type_name:
                            order.uiState
                                .laundry_order_type_name,

                        laundry_order_type_prefix:
                            order.uiState
                                .laundry_order_type_prefix,

                        allowed_category_ids:
                            order.uiState
                                .laundry_allowed_pos_category_ids,

                        laundry_status_id:
                            result
                                .status_id ||
                            false,

                        laundry_status_name:
                            result
                                .status_name ||
                            "",

                        laundry_status:
                            result.status ||
                            {},

                        laundry_payment_status_id:
                            result
                                .payment_status_id ||
                            false,

                        laundry_payment_status_name:
                            result
                                .payment_status_name ||
                            "",

                        laundry_total_amount:
                            Number(
                                result
                                    .total_amount ||
                                0
                            ),

                        laundry_paid_amount:
                            Number(
                                result
                                    .paid_amount ||
                                0
                            ),

                        laundry_balance:
                            Number(
                                result.balance ||
                                0
                            ),

                        laundry_refundable_amount:
                            Number(
                                result
                                    .refundable_amount ||
                                0
                            ),

                        laundry_has_changes:
                            false,

                        return_to_laundry_home:
                            true,
                    }
                );

                order.uiState
                    .laundry_original_snapshot =
                    this
                        .createLaundryOrderSnapshot(
                            order
                        );

                return result;
            },

            // -------------------------------------------------------------
            // Backend saved-order cancellation
            // -------------------------------------------------------------

            async cancelOrder() {
                const order =
                    this.getOrder();

                const laundryOrderId =
                    order?.uiState
                        ?.laundry_order_id;

                if (!laundryOrderId) {
                    throw new Error(
                        _t(
                            "Please save the laundry order before cancelling it."
                        )
                    );
                }

                const policy =
                    this.getActionPolicy(
                        order
                    );

                if (!policy.canCancel) {
                    throw new Error(
                        _t(
                            "This laundry order cannot be cancelled."
                        )
                    );
                }

                const result =
                    await this.orm.call(
                        "laundry.order",
                        "action_cancel_from_pos",
                        [[laundryOrderId]]
                    );

                if (!result?.success) {
                    throw new Error(
                        _t(
                            "The laundry order cancellation failed."
                        )
                    );
                }

                this._setLaundryOrderState(
                    order,
                    {
                        laundry_order_id:
                            laundryOrderId,

                        laundry_order_name:
                            order.uiState
                                .laundry_order_name,

                        laundry_order_type_id:
                            order.uiState
                                .laundry_order_type_id,

                        laundry_order_type_name:
                            order.uiState
                                .laundry_order_type_name,

                        laundry_order_type_prefix:
                            order.uiState
                                .laundry_order_type_prefix,

                        allowed_category_ids:
                            order.uiState
                                .laundry_allowed_pos_category_ids,

                        laundry_status_id:
                            result
                                .status_id ||
                            false,

                        laundry_status_name:
                            result
                                .status_name ||
                            "",

                        laundry_status:
                            result.status ||
                            {},

                        laundry_payment_status_id:
                            result
                                .payment_status_id ||
                            false,

                        laundry_payment_status_name:
                            result
                                .payment_status_name ||
                            "",

                        laundry_total_amount:
                            Number(
                                result
                                    .total_amount ||
                                order.uiState
                                    .laundry_total_amount ||
                                0
                            ),

                        laundry_paid_amount:
                            Number(
                                result
                                    .paid_amount ||
                                0
                            ),

                        laundry_balance:
                            Number(
                                result.balance ||
                                0
                            ),

                        laundry_refundable_amount:
                            Number(
                                result
                                    .refundable_amount ||
                                0
                            ),

                        laundry_has_changes:
                            false,

                        return_to_laundry_home:
                            true,
                    }
                );

                order.uiState
                    .laundry_original_snapshot =
                    this
                        .createLaundryOrderSnapshot(
                            order
                        );

                return result;
            },

            // -------------------------------------------------------------
            // Backend queries
            // -------------------------------------------------------------

            async getCustomerOrdersByStatus(
                partnerId
            ) {
                if (!partnerId) {
                    return [];
                }

                return await this.orm.call(
                    "laundry.order",
                    "get_customer_orders_by_status_for_pos",
                    [partnerId]
                );
            },

            async getLaundryOrderForPos(
                orderId
            ) {
                if (!orderId) {
                    return null;
                }

                return await this.orm.call(
                    "laundry.order",
                    "get_laundry_order_for_pos",
                    [orderId]
                );
            },

            // -------------------------------------------------------------
            // Open existing order
            // -------------------------------------------------------------

            async openLaundryOrder(
                orderId
            ) {
                const data =
                    await this
                        .getLaundryOrderForPos(
                            orderId
                        );

                if (!data) {
                    return;
                }

                const allowedCategoryIds =
                    this._normalizeCategoryIds(
                        data
                            .allowed_category_ids ||
                        []
                    );

                const partner =
                    this._getModelRecord(
                        "res.partner",
                        data.partner_id
                    );

                const order =
                    await this
                        .createFreshOrder(
                            partner || null
                        );

                this._setLaundryOrderState(
                    order,
                    this
                        ._prepareOpenOrderStateValues(
                            {
                                ...data,

                                allowed_category_ids:
                                    allowedCategoryIds,
                            }
                        )
                );

                console.log(
                    "OPEN EXISTING LAUNDRY ORDER",
                    order.uiState
                );

                this.pos
                    .selected_laundry_order_type =
                    {
                        id:
                            data
                                .order_type_id,

                        name:
                            data
                                .order_type_name,

                        prefix:
                            data
                                .order_type_prefix ||
                            "",

                        pos_category_ids:
                            allowedCategoryIds,
                    };

                this.clearCategorySelection(
                    order
                );

                this.setCurrentOrder(order);

                setLaundryVisibility(
                    order,
                    {
                        orderTypeId:
                            order.uiState
                                .laundry_order_type_id,

                        allowedCategoryIds:
                            order.uiState
                                .laundry_allowed_pos_category_ids,

                        isPackageUsage:
                            order.uiState
                                .is_package_usage,

                        allowedPackageProductIds:
                            order.uiState
                                .allowed_package_products,
                    }
                );

                traceLaundryState(
                    "OpenOrder:BeforeLines",
                    this.pos,
                    {
                        requestedOrderId:
                            orderId,

                        activeMatchesOpened:
                            this.getOrder()
                                ?.uuid ===
                            order.uuid,
                    }
                );

                this.setCurrentOrder(order);

                for (
                    const line of
                    data.lines || []
                ) {
                    const product =
                        this._getModelRecord(
                            "product.product",
                            line.product_id
                        );

                    if (!product) {
                        console.warn(
                            "Laundry product was not found in POS cache:",
                            line.product_id
                        );

                        continue;
                    }

                    await this.pos
                        .addLineToCurrentOrder(
                            {
                                product_id:
                                    product,

                                product_tmpl_id:
                                    product
                                        .product_tmpl_id,

                                qty:
                                    Number(
                                        line.qty ||
                                        0
                                    ),

                                price_unit:
                                    Number(
                                        line
                                            .price_unit ||
                                        0
                                    ),
                            },
                            {
                                force: true,
                            },
                            false
                        );
                }

                this.setCurrentOrder(order);

                /*
                 * Loading backend lines must not be
                 * treated as local modifications.
                 */
                order.uiState
                    .laundry_original_snapshot =
                    this
                        .createLaundryOrderSnapshot(
                            order
                        );

                order.uiState
                    .laundry_has_changes =
                    false;

                traceLaundryState(
                    "OpenOrder:BeforeProductScreen",
                    this.pos,
                    {
                        requestedOrderId:
                            orderId,

                        lineCount:
                            (
                                data.lines ||
                                []
                            ).length,

                        activeMatchesOpened:
                            this.getOrder()
                                ?.uuid ===
                            order.uuid,

                        originalSnapshot:
                            order.uiState
                                .laundry_original_snapshot,
                    }
                );

                this.pos.navigate(
                    "ProductScreen",
                    {
                        orderUuid:
                            order.uuid,
                    }
                );
            },

            // -------------------------------------------------------------
            // Read-only payment statuses
            // -------------------------------------------------------------

            isReadOnlyPaymentStatus(
                paymentStatusId
            ) {
                const config =
                    this.pos.config;

                const readOnlyStatusIds =
                    [
                        config
                            ?.paid_payment_id,

                        config
                            ?.refund_payment_id,

                        config
                            ?.cancelled_payment_id,
                    ]
                        .map((value) => {
                            if (
                                typeof value ===
                                "number"
                            ) {
                                return value;
                            }

                            if (
                                Array.isArray(
                                    value
                                )
                            ) {
                                return value[0];
                            }

                            return value?.id;
                        })
                        .filter(Boolean);

                const normalizedId =
                    Array.isArray(
                        paymentStatusId
                    )
                        ? paymentStatusId[0]
                        : (
                            paymentStatusId
                                ?.id ||
                            paymentStatusId
                        );

                return readOnlyStatusIds
                    .includes(
                        normalizedId
                    );
            },

            // -------------------------------------------------------------
            // Central ActionPad policy
            // -------------------------------------------------------------

            getActionPolicy(
                order = this.getOrder()
            ) {
                if (!order) {
                    return {
                        canSave: false,
                        canDiscard: false,
                        canUpdate: false,
                        canDiscardChanges:
                            false,
                        canCancel: false,
                        canPayment: false,
                        canRefund: false,
                        canPrint: false,
                    };
                }

                const ui =
                    order.uiState || {};

                const status =
                    ui.laundry_status ||
                    {};

                const isSaved =
                    Boolean(
                        ui.laundry_order_id
                    );

                const hasChanges =
                    isSaved
                        ? this
                            .hasLaundryOrderChanges(
                                order
                            )
                        : false;

                const balance =
                    Number(
                        ui.laundry_balance ||
                        0
                    );

                const refundableAmount =
                    Number(
                        ui
                            .laundry_refundable_amount ||
                        0
                    );

                return {
                    canSave:
                        !isSaved,

                    canDiscard:
                        !isSaved,

                    canUpdate:
                        isSaved &&
                        hasChanges &&
                        Boolean(
                            status.can_edit
                        ),

                    canDiscardChanges:
                        isSaved &&
                        hasChanges,

                    canCancel:
                        isSaved &&
                        !hasChanges &&
                        Boolean(
                            status.can_cancel
                        ),

                    canPayment:
                        isSaved &&
                        ui.laundry_allow_pay !== false &&
                        Boolean(
                            status
                                .can_receive_payment
                        ) &&
                        balance > 0,

                    canRefund:
                        isSaved &&
                        Boolean(
                            status.can_refund
                        ) &&
                        refundableAmount > 0,

                    canPrint:
                        isSaved &&
                        Boolean(
                            status.can_print
                        ),
                };
            },
        };
    },
};


registry
    .category("services")
    .add(
        "laundry",
        laundryService
    );
