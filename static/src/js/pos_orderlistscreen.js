/** @odoo-module **/

import {
    Component,
    onWillStart,
    useState,
} from "@odoo/owl";

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";


export class OrderListScreen extends Component {
    static template = "pos_laundry.OrderListScreen";

    setup() {
        this.pos = usePos();
        this.orm = useService("orm");
        this.laundry = useService("laundry");

        this.state = useState({
            loading: false,

            searchTerm: "",
            dateFilter: "today",

            unpaidOnly: false,
            readyOnly: false,
            selectedStatusId: false,

            dashboard: this.getEmptyDashboardData(),
        });

        this.searchTimer = null;

        onWillStart(async () => {
            await this.getDashboardData();
        });
    }

    // ---------------------------------------------------------------------
    // Dashboard loading
    // ---------------------------------------------------------------------

    async getDashboardData() {
        this.state.loading = true;

        try {
            const posConfigId = this.getPosConfigId();
            const partnerId = this.getSelectedPartnerId();

            if (!posConfigId) {
                console.warn(
                    "[Laundry Dashboard] POS configuration ID is missing."
                );

                this.state.dashboard =
                    this.getMockDashboardData();

                return;
            }

            const result = await this.orm.call(
                "laundry.order",
                "get_pos_dashboard_data",
                [
                    posConfigId,
                    partnerId,
                    this.state.searchTerm || "",
                    this.state.dateFilter || "today",
                    Boolean(this.state.unpaidOnly),
                    Boolean(this.state.readyOnly),
                    this.state.selectedStatusId || false,
                    20,
                ]
            );

            console.log(
                "[Laundry Dashboard] Dashboard data loaded:",
                result
            );

            this.state.dashboard =
                this.normalizeDashboardData(result);
        } catch (error) {
            console.error(
                "[Laundry Dashboard] Failed to load dashboard data:",
                error
            );

            /*
             * Keep mock data as a development fallback.
             *
             * Once the backend is fully tested, this can be replaced with:
             *
             * this.state.dashboard =
             *     this.getEmptyDashboardData();
             */
            this.state.dashboard =
                this.getMockDashboardData();
        } finally {
            this.state.loading = false;
        }
    }

    async refreshDashboard() {
        await this.getDashboardData();
    }

    // ---------------------------------------------------------------------
    // POS configuration and customer
    // ---------------------------------------------------------------------

    getPosConfigId() {
        return (
            this.pos?.config?.id ||
            this.pos?.config_id ||
            false
        );
    }

    getSelectedPartner() {
        const currentOrder =
            this.pos.getOrder?.() ||
            this.pos.get_order?.() ||
            null;

        return (
            currentOrder?.getPartner?.() ||
            currentOrder?.get_partner?.() ||
            currentOrder?.partner_id ||
            this.pos.selected_customer ||
            null
        );
    }

    getSelectedPartnerId() {
        const partner = this.getSelectedPartner();

        if (!partner) {
            return false;
        }

        if (Array.isArray(partner)) {
            return partner[0] || false;
        }

        return partner.id || false;
    }

    // ---------------------------------------------------------------------
    // Dashboard normalization
    // ---------------------------------------------------------------------

    getEmptyDashboardData() {
        return {
            today_orders: 0,
            unpaid_orders: 0,
            ready_orders: 0,
            today_sales: 0,
            statuses: [],
            recent_orders: [],
        };
    }

    normalizeDashboardData(data) {
        const source =
            data && typeof data === "object"
                ? data
                : {};

        return {
            today_orders: this.toNumber(
                source.today_orders
            ),

            unpaid_orders: this.toNumber(
                source.unpaid_orders
            ),

            ready_orders: this.toNumber(
                source.ready_orders
            ),

            today_sales: this.toNumber(
                source.today_sales
            ),

            statuses: Array.isArray(
                source.statuses
            )
                ? source.statuses.map(
                    (status) =>
                        this.normalizeStatus(status)
                )
                : [],

            recent_orders: Array.isArray(
                source.recent_orders
            )
                ? source.recent_orders.map(
                    (order) =>
                        this.normalizeOrder(order)
                )
                : [],
        };
    }

    normalizeStatus(status) {
        return {
            id: status?.id || false,
            name: status?.name || "",
            color:
                status?.color ||
                "text-primary",
            order_count: this.toNumber(
                status?.order_count
            ),
        };
    }

    normalizeOrder(order) {
        return {
            id: order?.id || false,
            name: order?.name || "",

            customer_id:
                order?.customer_id || false,

            customer_name:
                order?.customer_name ||
                "Walk-In Customer",

            customer_phone:
                order?.customer_phone || "",

            order_type_id:
                order?.order_type_id || false,

            order_type_name:
                order?.order_type_name || "",

            status_id:
                order?.status_id || false,

            status_name:
                order?.status_name || "",

            status_color:
                order?.status_color ||
                "text-primary",

            payment_status_id:
                order?.payment_status_id ||
                false,

            payment_status_name:
                order?.payment_status_name ||
                "",

            total_amount: this.toNumber(
                order?.total_amount
            ),

            currency_id:
                order?.currency_id || false,

            currency_symbol:
                order?.currency_symbol ||
                this.pos?.currency?.symbol ||
                "",

            order_datetime:
                order?.order_datetime || "",
        };
    }

    toNumber(value) {
        const number = parseFloat(value);

        return Number.isNaN(number)
            ? 0
            : number;
    }

    formatAmount(value) {
        return this.toNumber(value).toFixed(3);
    }

    // ---------------------------------------------------------------------
    // Search
    // ---------------------------------------------------------------------

    onSearchInput(event) {
        this.state.searchTerm =
            event?.target?.value || "";

        if (this.searchTimer) {
            clearTimeout(this.searchTimer);
        }

        this.searchTimer = setTimeout(
            async () => {
                await this.getDashboardData();
            },
            350
        );
    }

    async clearSearch() {
        if (this.searchTimer) {
            clearTimeout(this.searchTimer);
            this.searchTimer = null;
        }

        this.state.searchTerm = "";

        await this.getDashboardData();
    }

    // ---------------------------------------------------------------------
    // KPI filters
    // ---------------------------------------------------------------------

    async showTodayOrders() {
        this.state.dateFilter = "today";
        this.state.unpaidOnly = false;
        this.state.readyOnly = false;
        this.state.selectedStatusId = false;

        await this.getDashboardData();
    }

    async showUnpaidOrders() {
        this.state.dateFilter = "all";
        this.state.unpaidOnly = true;
        this.state.readyOnly = false;
        this.state.selectedStatusId = false;

        await this.getDashboardData();
    }

    async showReadyOrders() {
        this.state.dateFilter = "all";
        this.state.unpaidOnly = false;
        this.state.readyOnly = true;
        this.state.selectedStatusId = false;

        await this.getDashboardData();
    }

    async showAllOrders() {
        this.state.dateFilter = "all";
        this.state.unpaidOnly = false;
        this.state.readyOnly = false;
        this.state.selectedStatusId = false;

        await this.getDashboardData();
    }

    async toggleUnpaidFilter() {
        this.state.unpaidOnly =
            !this.state.unpaidOnly;

        if (this.state.unpaidOnly) {
            this.state.readyOnly = false;
            this.state.selectedStatusId =
                false;
        }

        await this.getDashboardData();
    }

    async toggleReadyFilter() {
        this.state.readyOnly =
            !this.state.readyOnly;

        if (this.state.readyOnly) {
            this.state.unpaidOnly = false;
            this.state.selectedStatusId =
                false;
        }

        await this.getDashboardData();
    }

    // ---------------------------------------------------------------------
    // Status filtering
    // ---------------------------------------------------------------------

    async selectStatus(status) {
        const statusId =
            typeof status === "object"
                ? status?.id
                : status;

        this.state.selectedStatusId =
            statusId || false;

        this.state.unpaidOnly = false;
        this.state.readyOnly = false;

        /*
         * Status cards show all orders for that status,
         * rather than limiting the list to today.
         */
        this.state.dateFilter = "all";

        await this.getDashboardData();
    }

    async clearStatusFilter() {
        this.state.selectedStatusId = false;

        await this.getDashboardData();
    }

    async resetFilters() {
        if (this.searchTimer) {
            clearTimeout(this.searchTimer);
            this.searchTimer = null;
        }

        this.state.searchTerm = "";
        this.state.dateFilter = "today";
        this.state.unpaidOnly = false;
        this.state.readyOnly = false;
        this.state.selectedStatusId = false;

        await this.getDashboardData();
    }

    // ---------------------------------------------------------------------
    // Filter state helpers
    // ---------------------------------------------------------------------

    get hasActiveFilters() {
        return Boolean(
            this.state.searchTerm ||
            this.state.unpaidOnly ||
            this.state.readyOnly ||
            this.state.selectedStatusId ||
            this.state.dateFilter !== "today"
        );
    }

    isStatusSelected(status) {
        return (
            Number(
                this.state.selectedStatusId
            ) === Number(status?.id)
        );
    }

    get selectedStatusName() {
        const selectedId =
            this.state.selectedStatusId;

        if (!selectedId) {
            return "";
        }

        const status =
            this.state.dashboard.statuses.find(
                (item) =>
                    Number(item.id) ===
                    Number(selectedId)
            );

        return status?.name || "";
    }

    // ---------------------------------------------------------------------
    // Orders
    // ---------------------------------------------------------------------

    get filteredOrders() {
        /*
         * Filtering is performed by the backend.
         * The server returns only the matching orders.
         */
        return (
            this.state.dashboard
                .recent_orders || []
        );
    }

    get hasOrders() {
        return this.filteredOrders.length > 0;
    }

    async openOrder(order) {
        const orderId =
            typeof order === "object"
                ? order?.id
                : order;

        if (!orderId) {
            console.warn(
                "[Laundry Dashboard] Cannot open order without an ID.",
                order
            );

            return;
        }

        try {
            await this.laundry.openLaundryOrder(
                orderId
            );
        } catch (error) {
            console.error(
                "[Laundry Dashboard] Failed to open order:",
                {
                    orderId,
                    error,
                }
            );

            throw error;
        }
    }

    // ---------------------------------------------------------------------
    // Badge classes
    // ---------------------------------------------------------------------

    getStatusBadgeClass(order) {
        const statusClass =
            order?.status_color ||
            "text-primary";

        /*
         * laundry.order.status.color stores Bootstrap
         * text classes such as:
         *
         * text-primary
         * text-success
         * text-warning
         * text-danger
         */
        return [
            "badge",
            "rounded-pill",
            "border",
            "bg-white",
            statusClass,
        ].join(" ");
    }

    getStatusCardClass(status) {
        const statusClass =
            status?.color ||
            "text-primary";

        const selectedClass =
            this.isStatusSelected(status)
                ? "border-primary shadow-sm"
                : "";

        return [
            "card",
            "h-100",
            "cursor-pointer",
            statusClass,
            selectedClass,
        ]
            .filter(Boolean)
            .join(" ");
    }

    getPaymentBadgeClass(order) {
        const paymentStatus = (
            order?.payment_status_name || ""
        )
            .trim()
            .toLowerCase();

        let badgeClass =
            "text-bg-secondary";

        if (
            paymentStatus === "paid" ||
            paymentStatus ===
                "package paid"
        ) {
            badgeClass =
                "text-bg-success";
        } else if (
            paymentStatus.includes("partial")
        ) {
            badgeClass =
                "text-bg-warning";
        } else if (
            paymentStatus.includes("unpaid")
        ) {
            badgeClass =
                "text-bg-danger";
        } else if (
            paymentStatus.includes("refund")
        ) {
            badgeClass =
                "text-bg-info";
        } else if (
            paymentStatus.includes("cancel")
        ) {
            badgeClass =
                "text-bg-dark";
        }

        return [
            "badge",
            "rounded-pill",
            badgeClass,
        ].join(" ");
    }

    // ---------------------------------------------------------------------
    // Mock dashboard data
    // ---------------------------------------------------------------------

    getMockDashboardData() {
        const currencySymbol =
            this.pos?.currency?.symbol ||
            "BD";

        return this.normalizeDashboardData({
            today_orders: 12,
            unpaid_orders: 4,
            ready_orders: 3,
            today_sales: 85.750,

            /*
             * These represent statuses where
             * show_on_home = True.
             */
            statuses: [
                {
                    id: 1,
                    name: "Confirmed",
                    color: "text-primary",
                    order_count: 5,
                },
                {
                    id: 2,
                    name: "Processing",
                    color: "text-warning",
                    order_count: 4,
                },
                {
                    id: 3,
                    name: "Ready",
                    color: "text-success",
                    order_count: 3,
                },
            ],

            recent_orders: [
                {
                    id: 101,
                    name: "LO/2026/00101",
                    customer_id: 10,
                    customer_name:
                        "Ahmed Mohammed",
                    customer_phone:
                        "39000001",
                    order_type_id: 1,
                    order_type_name:
                        "Walk-In",
                    status_id: 3,
                    status_name: "Ready",
                    status_color:
                        "text-success",
                    payment_status_id: 3,
                    payment_status_name:
                        "Paid",
                    total_amount: 7.500,
                    currency_symbol:
                        currencySymbol,
                    order_datetime:
                        "21/07/2026 08:45 AM",
                },
                {
                    id: 102,
                    name: "LO/2026/00102",
                    customer_id: 11,
                    customer_name:
                        "Ali Hassan",
                    customer_phone:
                        "39000002",
                    order_type_id: 2,
                    order_type_name:
                        "Home Collection",
                    status_id: 2,
                    status_name:
                        "Processing",
                    status_color:
                        "text-warning",
                    payment_status_id: 2,
                    payment_status_name:
                        "Partial Paid",
                    total_amount: 12.250,
                    currency_symbol:
                        currencySymbol,
                    order_datetime:
                        "21/07/2026 08:20 AM",
                },
                {
                    id: 103,
                    name: "LO/2026/00103",
                    customer_id: 12,
                    customer_name:
                        "Mohammed Salman",
                    customer_phone:
                        "39000003",
                    order_type_id: 1,
                    order_type_name:
                        "Walk-In",
                    status_id: 1,
                    status_name:
                        "Confirmed",
                    status_color:
                        "text-primary",
                    payment_status_id: 1,
                    payment_status_name:
                        "Unpaid",
                    total_amount: 4.000,
                    currency_symbol:
                        currencySymbol,
                    order_datetime:
                        "21/07/2026 07:55 AM",
                },
            ],
        });
    }
}

console.log(
    "[Laundry] Registering pos_orderlistscreen"
);

registry.category("pos_pages").add(
    "pos_orderlistscreen",
    {
        name: "pos_orderlistscreen",
        component: OrderListScreen,
        route:
            `/pos/ui/${odoo.pos_config_id}/orderslist`,
        params: {},
    }
);

