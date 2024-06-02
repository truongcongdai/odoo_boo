import requests
from odoo import fields, models, api
from odoo.exceptions import ValidationError


class HelpdeskStage(models.Model):
    _inherit = 'helpdesk.stage'

    def unlink(self):
        stage_new = self.env.ref('helpdesk.stage_new')
        stage_in_progress = self.env.ref('helpdesk.stage_in_progress')
        stage_solved = self.env.ref('helpdesk.stage_solved')
        stage_cancelled = self.env.ref('helpdesk.stage_cancelled')
        for rec in self:
            if stage_new:
                stage_new_id = stage_new.id
                if rec.id == stage_new_id:
                    raise ValidationError('Bản ghi không thể xóa!')
            if stage_in_progress:
                stage_in_progress_id = stage_in_progress.id
                if rec.id == stage_in_progress_id:
                    raise ValidationError('Bản ghi không thể xóa!')
            if stage_solved:
                stage_solved_id = stage_solved.id
                if rec.id == stage_solved_id:
                    raise ValidationError('Bản ghi không thể xóa!')
            if stage_cancelled:
                stage_cancelled_id = stage_cancelled.id
                if rec.id == stage_cancelled_id:
                    raise ValidationError('Bản ghi không thể xóa!')
        return super(HelpdeskStage, self).unlink()
