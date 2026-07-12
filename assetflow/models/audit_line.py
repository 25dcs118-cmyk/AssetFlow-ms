from odoo import fields, models


class AuditLine(models.Model):
    _name = 'audit.line'
    _description = 'Audit Line'
    _order = 'id'

    cycle_id = fields.Many2one('audit.cycle', required=True, ondelete='cascade')
    cycle_state = fields.Selection(related='cycle_id.state', store=True)
    asset_id = fields.Many2one('asset.asset', required=True, ondelete='cascade')
    category_id = fields.Many2one(related='asset_id.category_id', store=True)
    auditor_id = fields.Many2one('res.users', string='Auditor')
    result = fields.Selection([
        ('verified', 'Verified'),
        ('missing', 'Missing'),
        ('damaged', 'Damaged'),
    ], string='Result')
    notes = fields.Text()
