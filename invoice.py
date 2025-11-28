# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool, PoolMeta
from trytond.model import fields, ModelView, Workflow
from trytond.pyson import Eval
from itertools import chain
from trytond.i18n import gettext
from trytond.exceptions import UserError
from trytond.transaction import Transaction


class Invoice(metaclass=PoolMeta):
    __name__ = 'account.invoice'

    def _get_move_line(self, date, amount):
        line = super()._get_move_line(date, amount)
        number = self.reference or self.number if self.type == 'in' else self.number
        if line.description:
            if self.party.name not in line.description:
                line.description = self.party.name + ' ' + line.description
            if number not in line.description:
                line.description = number + ' ' + line.description
        else:
            line.description = number + ' ' + self.party.name
        return line

    @classmethod
    def cancel(cls, invoices):
        pool = Pool()
        Data = pool.get('ir.model.data')

        group_invoice_cancel = Data.search([
                ('fs_id','=','group_invoice_cancel'),
                ('model','=','res.group'),
                ('module','=','account_common'),
                ])
        cancel_group = (group_invoice_cancel[0].db_id
            if group_invoice_cancel else None)
        user_groups = Transaction().context.get('groups', [])
        for invoice in invoices:
            if (invoice.state == 'posted' or (invoice.type == 'out'
                        and invoice.state == 'draft'
                        and invoice.number is not None)):
                if cancel_group not in user_groups:
                    raise UserError(gettext(
                            'account_common.'
                            'msg_cancel_invoice_with_group_permission'))
            if not invoice.move:
                continue
            if invoice.move.state != 'posted':
                raise UserError(gettext(
                        'account_common.msg_cancel_invoice_with_move_post'))
        return super(Invoice, cls).cancel(invoices)


class InvoiceUndoPay(metaclass=PoolMeta):
    __name__ = 'account.invoice'

    paid_directly = fields.Function(fields.Boolean("Has Payed directly",
            help="The invoice has payed with the 'PAY' button"),
        'get_paid_directly')

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls._buttons.update({
                'undo_pay': {
                    'invisible': ~Eval('paid_directly', False),
                    'depends': ['paid_directly'],
                    },
                })

    def get_paid_directly(self, name):
        for line in chain(self.payment_lines, self.reconciliation_lines):
            if line.move_origin == self:
                return True
        return False

    @classmethod
    @ModelView.button
    @Workflow.transition('posted')
    def undo_pay(cls, invoices):
        pool = Pool()
        Move = pool.get('account.move')
        Reconciliation = pool.get('account.move.reconciliation')

        reconciliations = []
        moves = []
        for invoice in invoices:
            for line in chain(invoice.payment_lines,
                    invoice.reconciliation_lines):
                if line.move_origin == invoice:
                    moves.append(line.move)
                    # In case the move are created manually and assigned the
                    # invoice as origin, and after reconciled manually too,
                    # it will be removed too.
                    if line.reconciliation:
                        reconciliations.append(line.reconciliation)
        if reconciliations:
            Reconciliation.delete(reconciliations)
        if moves:
            moves = list(set(moves))
            Move.draft(moves)
            Move.delete(moves)


class CreditInvoiceStart(metaclass=PoolMeta):
    __name__ = 'account.invoice.credit.start'

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.with_refund.states['invisible'] = True


class CreditInvoice(metaclass=PoolMeta):
    __name__ = 'account.invoice.credit'

    def default_start(self, fields):
        defaults = super(CreditInvoice, self).default_start(fields)
        if 'with_refund' in defaults.keys():
            defaults['with_refund'] = False
        return defaults
