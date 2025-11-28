# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool, PoolMeta
from trytond.model import fields
from trytond.model import Model, ModelView
from trytond.pyson import Eval
from trytond.i18n import gettext
from trytond.exceptions import UserError


class CancelMoves(metaclass=PoolMeta):
    __name__ = 'account.move.cancel'

    def transition_cancel(self):
        moves = self.records
        for move in moves:
            if isinstance(move.origin, Model):
                raise UserError(gettext(
                    'account_common.msg_cancel_move_with_origin',
                    move=move.rec_name,
                    origin=move.origin.rec_name))
        return super().transition_cancel()


class Move(metaclass=PoolMeta):
    __name__ = 'account.move'

    allow_button_draft = fields.Function(fields.Boolean(
            'Allow Button Draft Move'), 'get_allow_button_draft')
    allow_draft = fields.Function(fields.Boolean('Allow Draft Move'),
        'get_allow_draft')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        if 'state' not in cls._check_modify_exclude:
            cls._check_modify_exclude.append('state')
        cls._buttons.update({
                'draft': {
                    'invisible': ((Eval('state') == 'draft')
                        | ((Eval('state') != 'draft') &
                        (~Eval('allow_button_draft', True)))),
                    'depends': ['allow_button_draft'],
                    },
                })

    def get_allow_button_draft(self, name):
        pool = Pool()
        FiscalYear = pool.get('account.fiscalyear')

        if ((self.origin and not isinstance(self.origin, FiscalYear))
                or [l.origin for l in self.lines if l.origin]):
            return False
        return True

    def get_allow_draft(self, name):
        pool = Pool()
        Invoice = pool.get('account.invoice')

        if self.origin and isinstance(self.origin, Invoice):
            return True
        return self.allow_button_draft

    @classmethod
    @ModelView.button
    def draft(cls, moves):
        pool = Pool()
        Line = pool.get('account.move.line')

        moves_to_draft = [m for m in moves if m.allow_draft]
        if moves_to_draft:
            cls.write(moves_to_draft, {
                'state': 'draft',
                })
            Line.check_modify([l for m in moves_to_draft for l in m.lines])
