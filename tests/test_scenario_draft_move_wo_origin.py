import unittest
from decimal import Decimal

from proteus import Model
from trytond.modules.account.tests.tools import (create_chart,
    create_fiscalyear, get_accounts)
from trytond.modules.account_invoice.tests.tools import \
    set_fiscalyear_invoice_sequences
from trytond.modules.company.tests.tools import create_company, get_company
from trytond.tests.test_tryton import drop_db
from trytond.tests.tools import activate_modules


class Test(unittest.TestCase):

    def setUp(self):
        drop_db()
        super().setUp()

    def tearDown(self):
        drop_db()
        super().tearDown()

    def test(self):

        # Install account_invoice
        activate_modules('account_common')

        # Create company
        _ = create_company()
        company = get_company()
        tax_identifier = company.party.identifiers.new()
        tax_identifier.type = 'eu_vat'
        tax_identifier.code = 'BE0897290877'
        company.party.save()

        # Create fiscal year
        fiscalyear = set_fiscalyear_invoice_sequences(
            create_fiscalyear(company))
        fiscalyear.click('create_period')
        period = fiscalyear.periods[0]

        # Create chart of accounts
        _ = create_chart(company)
        accounts = get_accounts(company)
        receivable = accounts['receivable']
        cash = accounts['cash']

        # Create party
        Party = Model.get('party.party')
        party = Party(name='Party')
        party.save()

        # Create and post Moves in Cash Journal
        Journal = Model.get('account.journal')
        Move = Model.get('account.move')
        journal_cash, = Journal.find([
            ('code', '=', 'CASH'),
        ])
        move = Move()
        move.period = period
        move.journal = journal_cash
        move.date = period.start_date
        line = move.lines.new()
        line.account = cash
        line.debit = Decimal(42)
        line = move.lines.new()
        line.account = receivable
        line.credit = Decimal(42)
        line.party = party
        move.click('post')

        # Draft move and delete
        move.click('draft')
        self.assertEqual(move.state, 'draft')
