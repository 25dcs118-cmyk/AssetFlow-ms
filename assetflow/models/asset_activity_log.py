from odoo import fields, models
from odoo.exceptions import AccessError


class AssetActivityLog(models.Model):
    _name = 'asset.activity.log'
    _description = 'Asset Activity Log'
    _order = 'timestamp desc'
    _rec_name = 'action'

    res_model = fields.Char(required=True, index=True)
    res_id = fields.Integer(required=True, index=True)
    action = fields.Char(required=True)
    actor_id = fields.Many2one('res.users', required=True, default=lambda self: self.env.user)
    timestamp = fields.Datetime(required=True, default=fields.Datetime.now)
    description = fields.Text()

    def write(self, vals):
        raise AccessError("Activity log entries are append-only and cannot be modified.")

    def unlink(self):
        raise AccessError("Activity log entries are append-only and cannot be deleted.")

    def log(self, record, action, description=False):
        return self.sudo().create({
            'res_model': record._name,
            'res_id': record.id,
            'action': action,
            'description': description,
        })
