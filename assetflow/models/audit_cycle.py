from odoo import api, fields, models
from odoo.exceptions import UserError


class AuditCycle(models.Model):
    _name = 'audit.cycle'
    _description = 'Asset Audit Cycle'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'date_from desc'

    name = fields.Char(required=True, default='New', copy=False, tracking=True)
    department_id = fields.Many2one('asset.department', string='Department Scope', tracking=True)
    location = fields.Char(string='Location Scope')
    date_from = fields.Date(required=True, default=fields.Date.context_today, tracking=True)
    date_to = fields.Date(required=True, tracking=True)
    auditor_ids = fields.Many2many('res.users', string='Auditors', tracking=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('closed', 'Closed'),
    ], default='draft', required=True, tracking=True)
    line_ids = fields.One2many('audit.line', 'cycle_id', string='Audit Lines')
    line_count = fields.Integer(compute='_compute_line_counts')
    discrepancy_count = fields.Integer(compute='_compute_line_counts')
    unverified_count = fields.Integer(compute='_compute_line_counts')

    @api.depends('line_ids.result')
    def _compute_line_counts(self):
        for cycle in self:
            cycle.line_count = len(cycle.line_ids)
            cycle.discrepancy_count = len(cycle.line_ids.filtered(lambda l: l.result in ('missing', 'damaged')))
            cycle.unverified_count = len(cycle.line_ids.filtered(lambda l: not l.result))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('audit.cycle') or 'New'
        return super().create(vals_list)

    def action_start(self):
        for cycle in self:
            if cycle.state != 'draft':
                raise UserError("Only draft audit cycles can be started.")
            if not cycle.auditor_ids:
                raise UserError("Assign at least one auditor before starting the cycle.")
            domain = [('state', 'not in', ('retired', 'lost'))]
            if cycle.department_id:
                domain.append(('department_id', '=', cycle.department_id.id))
            if cycle.location:
                domain.append(('location', '=', cycle.location))
            assets = self.env['asset.asset'].search(domain)
            self.env['audit.line'].create([{
                'cycle_id': cycle.id,
                'asset_id': asset.id,
            } for asset in assets])
            cycle.state = 'in_progress'
            self.env['asset.activity.log'].log(
                cycle, 'audit_started', f"Audit cycle {cycle.name} started with {len(assets)} asset(s) in scope."
            )
        return True

    def action_close(self):
        for cycle in self:
            if cycle.state != 'in_progress':
                raise UserError("Only in-progress audit cycles can be closed.")
            if cycle.unverified_count:
                raise UserError(f"{cycle.unverified_count} asset(s) still unverified. Mark every line before closing.")
            missing = cycle.line_ids.filtered(lambda l: l.result == 'missing')
            missing.mapped('asset_id').write({'state': 'lost'})
            for line in missing:
                self.env['asset.activity.log'].log(
                    line.asset_id, 'audit_missing',
                    f"Asset {line.asset_id.tag} confirmed missing in audit cycle {cycle.name}, marked Lost."
                )
            cycle.state = 'closed'
            self.env['asset.activity.log'].log(
                cycle, 'audit_closed',
                f"Audit cycle {cycle.name} closed. {cycle.discrepancy_count} discrepancy(ies) found."
            )
            if cycle.discrepancy_count:
                managers = self.env['res.users'].search([
                    ('groups_id', 'in', self.env.ref('assetflow.group_assetflow_asset_manager').id),
                ])
                if managers:
                    cycle.message_post(
                        body=f"Audit Discrepancy Flagged: {cycle.discrepancy_count} discrepancy(ies) found "
                             f"in audit cycle {cycle.name}. Review required.",
                        partner_ids=managers.mapped('partner_id.id'),
                    )
        return True
