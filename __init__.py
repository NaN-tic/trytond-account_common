# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.pool import Pool
from . import account
from . import configuration
from . import currency
from . import invoice
from . import move
from . import party


def register():
    Pool.register(
        account.Period,
        account.TaxRuleLineTemplate,
        account.TaxRuleLine,
        configuration.Configuration,
        currency.Currency,
        move.Move,
        invoice.CreditInvoiceStart,
        party.Party,
        module='account_common', type_='model')
    Pool.register(
        move.CancelMoves,
        module='account_common', type_='wizard')
    Pool.register(
        account.SaleLine,
        depends=['sale'],
        module='account_common', type_='model')
    Pool.register(
        account.PurchaseLine,
        depends=['purchase'],
        module='account_common', type_='model')
    Pool.register(
        account.InvoiceLine,
        invoice.Invoice,
        invoice.InvoiceUndoPay,
        depends=['account_invoice'],
        module='account_common', type_='model')
    Pool.register(
        invoice.CreditInvoice,
        depends=['account_invoice'],
        module='account_common', type_='wizard')
