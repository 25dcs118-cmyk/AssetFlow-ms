from odoo import api, fields, models
from odoo.exceptions import UserError


class AssetAsset(models.Model):
    _name = 'asset.asset'
    _description = 'Asset'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'tag'

    name = fields.Char(required=True, tracking=True)
    tag = fields.Char(readonly=True, copy=False, default='New', tracking=True)
    serial_number = fields.Char(tracking=True)
    category_id = fields.Many2one('asset.category', required=True, tracking=True)
    department_id = fields.Many2one('asset.department', tracking=True)
    acquisition_date = fields.Date()
    acquisition_cost = fields.Monetary(currency_field='currency_id', help="Stored for reporting only, never posted to the ledger.")
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    condition = fields.Selection([
        ('new', 'New'),
        ('good', 'Good'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
        ('damaged', 'Damaged'),
    ], default='new', tracking=True)
    location = fields.Char()
    is_shared = fields.Boolean(string='Shared / Bookable', tracking=True)
    state = fields.Selection([
        ('available', 'Available'),
        ('allocated', 'Allocated'),
        ('reserved', 'Reserved'),
        ('maintenance', 'Under Maintenance'),
        ('lost', 'Lost'),
        ('retired', 'Retired'),
    ], default='available', required=True, tracking=True)

    allocation_ids = fields.One2many('asset.allocation', 'asset_id', string='Allocations')
    current_allocation_id = fields.Many2one(
        'asset.allocation', string='Current Allocation',
        compute='_compute_current_allocation', store=True)
    current_holder = fields.Char(compute='_compute_current_allocation', store=True)
    transfer_ids = fields.One2many('asset.transfer', 'asset_id', string='Transfers')
    booking_ids = fields.One2many('resource.booking', 'asset_id', string='Bookings')
    maintenance_ids = fields.One2many('asset.maintenance.request', 'asset_id', string='Maintenance Requests')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    _sql_constraints = [
        ('tag_uniq', 'unique(tag)', 'Asset tag must be unique.'),
        ('serial_number_uniq', 'unique(serial_number)', 'Serial number must be unique.'),
    ]

    @api.depends('allocation_ids.state', 'allocation_ids.employee_id', 'allocation_ids.department_id')
    def _compute_current_allocation(self):
        for asset in self:
            active_allocation = asset.allocation_ids.filtered(lambda a: a.state == 'active')[:1]
            asset.current_allocation_id = active_allocation
            asset.current_holder = active_allocation.holder_name if active_allocation else False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('tag', 'New') == 'New':
                vals['tag'] = self.env['ir.sequence'].next_by_code('asset.asset') or 'New'
        assets = super().create(vals_list)
        for asset in assets:
            self.env['asset.activity.log'].log(asset, 'registered', f"Asset {asset.tag} registered.")
        return assets

    def _check_available(self):
        for asset in self:
            if asset.state != 'available':
                raise UserError(
                    f"Asset {asset.tag} is currently {dict(asset._fields['state'].selection).get(asset.state)} "
                    f"and cannot be allocated. Use a Transfer Request instead."
                    + (f" Currently held by: {asset.current_holder}." if asset.current_holder else "")
                )

    def action_mark_lost(self):
        self.write({'state': 'lost'})
        for asset in self:
            self.env['asset.activity.log'].log(asset, 'lost', f"Asset {asset.tag} marked as Lost.")
        return True

    def action_retire(self):
        self.write({'state': 'retired', 'active': False})
        for asset in self:
            self.env['asset.activity.log'].log(asset, 'retired', f"Asset {asset.tag} retired.")
        return True

    def _open_form(self, res_model, extra_context=None):
        self.ensure_one()
        context = {'default_asset_id': self.id}
        context.update(extra_context or {})
        return {
            'type': 'ir.actions.act_window',
            'name': res_model,
            'res_model': res_model,
            'view_mode': 'form',
            'target': 'new',
            'context': context,
        }

    def action_open_new_allocation(self):
        self._check_available()
        return self._open_form('asset.allocation')

    def action_open_new_transfer(self):
        return self._open_form('asset.transfer')

    def action_open_new_booking(self):
        return self._open_form('resource.booking')

    def action_open_new_maintenance(self):
        return self._open_form('asset.maintenance.request')
