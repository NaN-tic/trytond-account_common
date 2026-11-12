# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool, PoolMeta
from trytond.model import fields, ModelView, Workflow
from trytond.pyson import Eval
from itertools import chain
from trytond.i18n import gettext
from trytond.exceptions import UserError, UserWarning
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
        User = pool.get('res.user')

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
                if (cancel_group not in user_groups
                        and not User.is_administrator()):
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
        Warning = pool.get('res.user.warning')

        for invoice in invoices:
            payment_lines = set(chain(
                    invoice.payment_lines, invoice.reconciliation_lines))
            if not any(l.move_origin == invoice for l in payment_lines):
                continue
            other_moves = {l.move for l in payment_lines
                if l.move_origin != invoice and l.move != invoice.move}
            if other_moves:
                warning_name = Warning.format(
                    'undo_pay_mixed', [invoice] + sorted(
                        other_moves, key=lambda m: m.id))
                if Warning.check(warning_name):
                    raise UserWarning(warning_name, gettext(
                            'account_common.msg_undo_pay_mixed',
                            invoice=invoice.rec_name,
                            moves=', '.join(m.rec_name for m in sorted(
                                    other_moves, key=lambda m: m.id))))

        reconciliations = set()
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
                        reconciliations.add(line.reconciliation)
        if reconciliations:
            Reconciliation.delete(list(reconciliations))
        if moves:
            moves = list(set(moves))
            Move.draft(moves)
            Move.delete(moves)


class PayInvoiceStart(metaclass=PoolMeta):
    __name__ = 'account.invoice.pay.start'

    multiple = fields.Boolean("Multiple Invoices", readonly=True)
    invoices = fields.Many2Many(
        'account.invoice', None, None, "Invoices", readonly=True,
        states={'invisible': ~Eval('multiple', False)})

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.amount.states['readonly'] = Eval('multiple', False)
        cls.payee.states['readonly'] = Eval('multiple', False)


class PayInvoice(metaclass=PoolMeta):
    __name__ = 'account.invoice.pay'

    def default_start(self, fields):
        defaults = super().default_start(fields)
        if len(self.records) > 1:
            self.check_multiple_invoices()
            defaults.update(
                multiple=True,
                invoices=[i.id for i in self.records],
                payee=self.record.party.id,
                amount=sum(i.amount_to_pay for i in self.records))
        return defaults

    def check_multiple_invoices(self):
        invoices = self.records
        first = invoices[0]
        for invoice in invoices:
            if (invoice.state != 'posted' or not invoice.amount_to_pay
                    or invoice.party != first.party
                    or invoice.company != first.company
                    or invoice.currency != first.currency
                    or invoice.type != first.type
                    or invoice.alternative_payees):
                raise UserError(gettext(
                        'account_common.msg_multiple_payment_invoices'))

    def transition_choice(self):
        if len(self.records) > 1:
            return 'pay'
        return super().transition_choice()

    def transition_pay(self):
        if len(self.records) == 1:
            return super().transition_pay()

        pool = Pool()
        Invoice = pool.get('account.invoice')
        Move = pool.get('account.move')
        Line = pool.get('account.move.line')
        Currency = pool.get('currency.currency')
        Period = pool.get('account.period')

        invoices = self.records
        Invoice.lock(invoices)
        self.check_multiple_invoices()
        first = invoices[0]
        currency = first.currency
        company = first.company
        date = self.start.date
        method = self.start.payment_method
        if (self.start.amount != sum(i.amount_to_pay for i in invoices)
                or self.start.currency != currency
                or self.start.payee != first.party):
            raise UserError(gettext(
                    'account_common.msg_multiple_payment_changed'))
        if (method.company != company
                or any(i.account in {
                        method.debit_account, method.credit_account}
                    for i in invoices)):
            raise UserError(gettext(
                    'account_common.msg_multiple_payment_method'))

        lines = []
        reconciliations = []
        for invoice in invoices:
            amount = invoice.amount_to_pay
            reconcile_lines, remainder = self.get_reconcile_lines_for_amount(
                invoice, amount, currency)
            if remainder:
                raise UserError(gettext(
                        'account_common.msg_multiple_payment_changed'))
            with Transaction().set_context(date=date):
                company_amount = Currency.compute(
                    currency, amount, company.currency)
            balance = (company_amount if invoice.type == 'in'
                else -company_amount)
            line = Line(
                account=invoice.account,
                debit=max(balance, 0), credit=max(-balance, 0),
                description=invoice.reference or invoice.number)
            if line.account.party_required:
                line.party = invoice.party
            if currency != company.currency:
                line.second_currency = currency
                line.amount_second_currency = (
                    amount if invoice.type == 'in' else -amount)
            lines.append(line)
            reconciliations.append(reconcile_lines)

        balance = -sum(l.debit - l.credit for l in lines)
        account = (method.debit_account if balance > 0
            else method.credit_account).current(date=date)
        counterpart = Line(
            account=account, debit=max(balance, 0), credit=max(-balance, 0))
        if account.party_required:
            counterpart.party = first.party
        if currency != company.currency:
            counterpart.second_currency = currency
            counterpart.amount_second_currency = -sum(
                l.amount_second_currency for l in lines)
        move = Move(
            company=company, journal=method.journal,
            period=Period.find(company, date=date), date=date,
            description=self.start.description)
        move.save()
        for line in lines + [counterpart]:
            line.move = move
        Line.save(lines + [counterpart])
        Move.post([move])
        Invoice.add_payment_lines(dict(zip(invoices, ([l] for l in lines))))
        for reconcile_lines, line in zip(reconciliations, lines):
            Line.reconcile(reconcile_lines + [line])
        return 'end'


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
