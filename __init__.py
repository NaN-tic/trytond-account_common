# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.pool import Pool
from . import account
from . import currency
from . import invoice
from . import move


def register():
    Pool.register(
        account.Period,
        currency.Currency,
        move.Move,
        invoice.CreditInvoiceStart,
        module='account_common', type_='model')
    Pool.register(
        move.CancelMoves,
        module='account_common', type_='wizard')
    Pool.register(
        invoice.Invoice,
        invoice.InvoiceUnpay,
        depends=['account_invoice'],
        module='account_common', type_='model')
    Pool.register(
        invoice.CreditInvoice,
        depends=['account_invoice'],
        module='account_common', type_='wizard')
