{
    "name": "POS Laundry",
    "version": "1.0.4",
    "depends": ["point_of_sale", "project", "sale_management"],
    "category": "Operations",
    "summary": "Production-ready Laundry POS System",
    "description": """
        POS Laundry

        Features:
        - Delivery Teams
        - Pickup Vouchers
        - Delivery Vouchers
        - Driver Assignment
        - Route Management
        - Laundry Order Logistics Tracking
    """,
    "author": "Sayed Ali Hassan",
    "website": "",
    "license": "LGPL-3",
    "data": [
        'security/ir.model.access.csv',
        'views/laundry_order_type_views.xml',
        "views/laundry_order_type_actions.xml",
        "views/laundry_package_rule_views.xml",
        "views/laundry_package_rule_action.xml",
        "views/laundry_configuration_views.xml",
        "views/laundry_res_config_settings_view.xml",
        "views/laundry_res_config_settings_action.xml",
        "views/laundry_order_status_views.xml",
        "views/laundry_order_status_action.xml",
        "views/laundry_order_payment_status_views.xml",
        "views/laundry_order_payment_status_action.xml",
        "views/laundry_order_view.xml",
        "views/laundry_order_action.xml",
        "views/laundry_menus.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_laundry/static/src/xml/pos_navbar.xml",
            "pos_laundry/static/src/xml/pos_actionpad.xml",
            "pos_laundry/static/src/xml/pos_pendingscreen.xml",
            "pos_laundry/static/src/css/pos_laundry.css",
            "pos_laundry/static/src/xml/pos_ordertype.xml",
            "pos_laundry/static/src/xml/pos_productprice.xml",
            "pos_laundry/static/src/xml/pos_orderlistscreen.xml",
            "pos_laundry/static/src/xml/CustomerEditPopup.xml",
            "pos_laundry/static/src/js/pos_pendingscreen.js",
            "pos_laundry/static/src/js/pos_customereditpopup.js",
            "pos_laundry/static/src/js/pos_homescreen.js",
            "pos_laundry/static/src/xml/pos_homescreen.xml",
            "pos_laundry/static/src/xml/pos_customerscreen.xml",
            "pos_laundry/static/src/js/pos_customerscreen.js",
            "pos_laundry/static/src/js/pos_startup.js",
            "pos_laundry/static/src/js/services/receipt_service.js",
            "pos_laundry/static/src/js/actionpad_extension.js",
            "pos_laundry/static/src/js/pos_orderlistscreen.js",

            "pos_laundry/static/src/js/package/package_utils.js",
            "pos_laundry/static/src/js/package/package_engine.js",
            "pos_laundry/static/src/js/package/package_store_patch.js",
            "pos_laundry/static/src/js/package/package_category_patch.js",
            "pos_laundry/static/src/js/package/package_product_patch.js",
            "pos_laundry/static/src/js/package/package_order_patch.js",
            "pos_laundry/static/src/js/package/package_validation.js",
            "pos_laundry/static/src/xml/package_category_badge.xml",
            "pos_laundry/static/src/overrides/models/pos_patch.js",
            "pos_laundry/static/src/overrides/models/paymentscreen_patch.js",
            
            "pos_laundry/static/src/xml/laundry_receipt.xml",
        ],
    },
    "installable": True,
    "application": True
}
