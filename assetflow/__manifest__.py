{
    'name': 'AssetFlow',
    'version': '17.0.1.0.0',
    'category': 'Operations/Assets',
    'summary': 'Enterprise Asset & Resource Management System',
    'description': """
AssetFlow
=========
Modular asset lifecycle and resource management: registration, allocation,
transfer, booking, maintenance and audit trail, governed by role-based
access control and automated business validations. Scoped to asset
lifecycle only, no dependency on accounting or purchasing.
""",
    'author': 'AssetFlow',
    'license': 'LGPL-3',
    'depends': ['base', 'mail'],
    'data': [
        'security/assetflow_groups.xml',
        'security/ir.model.access.csv',
        'security/assetflow_security.xml',
        'data/assetflow_sequence.xml',
        'data/assetflow_cron.xml',
        'data/assetflow_branding.xml',
        'views/asset_department_views.xml',
        'views/asset_category_views.xml',
        'views/res_users_views.xml',
        'views/asset_asset_views.xml',
        'views/asset_allocation_views.xml',
        'views/asset_transfer_views.xml',
        'views/resource_booking_views.xml',
        'views/asset_maintenance_request_views.xml',
        'views/asset_activity_log_views.xml',
        'views/assetflow_dashboard_views.xml',
        'views/assetflow_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'assetflow/static/src/scss/assetflow_theme.scss',
            'assetflow/static/src/dashboard/assetflow_dashboard.js',
            'assetflow/static/src/dashboard/assetflow_dashboard.xml',
            'assetflow/static/src/dashboard/assetflow_dashboard.scss',
        ],
    },
    'installable': True,
    'application': True,
    'post_init_hook': 'post_init_hook',
}
