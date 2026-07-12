import base64
import os

from odoo import api, SUPERUSER_ID


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    company = env.ref('base.main_company', raise_if_not_found=False)
    if not company:
        return
    icon_path = os.path.join(os.path.dirname(__file__), 'static', 'description', 'icon.png')
    with open(icon_path, 'rb') as f:
        company.write({'logo': base64.b64encode(f.read())})
