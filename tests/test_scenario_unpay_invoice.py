import unittest
from decimal import Decimal

from proteus import Model
from trytond.modules.account.tests.tools import (create_chart, create_tax,
    create_fiscalyear, create_tax_code, get_accounts)
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

        # Create chart of accounts
        _ = create_chart(company)
        accounts = get_accounts(company)
        revenue = accounts['revenue']
        expense = accounts['expense']
        account_cash = accounts['cash']

        # Create tax
        tax = create_tax(Decimal('.10'))
        tax.save()
        invoice_base_code = create_tax_code(tax, 'base', 'invoice')
        invoice_base_code.save()
        invoice_tax_code = create_tax_code(tax, 'tax', 'invoice')
        invoice_tax_code.save()
        credit_note_base_code = create_tax_code(tax, 'base', 'credit')
        credit_note_base_code.save()
        credit_note_tax_code = create_tax_code(tax, 'tax', 'credit')
        credit_note_tax_code.save()

        # Create payment method
        Journal = Model.get('account.journal')
        PaymentMethod = Model.get('account.invoice.payment.method')
        journal_cash, = Journal.find([('type', '=', 'cash')])
        payment_method = PaymentMethod()
        payment_method.name = 'Cash'
        payment_method.journal = journal_cash
        payment_method.credit_account = account_cash
        payment_method.debit_account = account_cash
        payment_method.save()

        # Create party
        Party = Model.get('party.party')
        party = Party(name='Party')
        party.save()

        # Create account category
        ProductCategory = Model.get('product.category')
        account_category = ProductCategory(name="Account Category")
        account_category.accounting = True
        account_category.account_expense = expense
        account_category.account_revenue = revenue
        account_category.customer_taxes.append(tax)
        account_category.save()

        # Create product
        ProductUom = Model.get('product.uom')
        unit, = ProductUom.find([('name', '=', 'Unit')])
        ProductTemplate = Model.get('product.template')
        template = ProductTemplate()
        template.name = 'product'
        template.default_uom = unit
        template.type = 'service'
        template.list_price = Decimal('40')
        template.account_category = account_category
        template.save()
        product, = template.products

        # Create payment term
        PaymentTerm = Model.get('account.invoice.payment_term')
        payment_term = PaymentTerm(name='Term')
        line = payment_term.lines.new(type='percent', ratio=Decimal('.5'))
        delta, = line.relativedeltas
        delta.days = 20
        line = payment_term.lines.new(type='remainder')
        delta = line.relativedeltas.new(days=40)
        payment_term.save()

        # Create invoice
        Invoice = Model.get('account.invoice')
        InvoiceLine = Model.get('account.invoice.line')
        invoice = Invoice()
        invoice.party = party
        invoice.payment_term = payment_term
        line = InvoiceLine()
        invoice.lines.append(line)
        line.product = product
        line.quantity = 5
        line.unit_price = Decimal('40')
        line = InvoiceLine()
        invoice.lines.append(line)
        line.account = revenue
        line.description = 'Test'
        line.quantity = 1
        line.unit_price = Decimal(20)
        self.assertEqual(invoice.untaxed_amount, Decimal('220.00'))
        self.assertEqual(invoice.tax_amount, Decimal('20.00'))
        self.assertEqual(invoice.total_amount, Decimal('240.00'))
        invoice.save()

        # Post invoice
        invoice.click('post')
        self.assertEqual(invoice.state, 'posted')
        move = invoice.move
        self.assertEqual(move.state, 'posted')

        # Pay partially invoice
        pay = invoice.click('pay')
        self.assertEqual(pay.form.amount, Decimal('240.00'))
        pay.form.amount = Decimal('100.00')
        pay.form.payment_method = payment_method
        pay.execute('choice')
        pay.execute('pay')
        self.assertEqual(pay.state, 'end')
        self.assertEqual(invoice.amount_to_pay, Decimal('140.00'))
        self.assertEqual(invoice.state, 'posted')

        # UnPay
        pay = invoice.click('unpay')
        self.assertEqual(invoice.amount_to_pay, Decimal('240.00'))
        self.assertEqual(invoice.state, 'posted')

        # Pay invoice
        pay = invoice.click('pay')
        self.assertEqual(pay.form.amount, Decimal('240.00'))
        pay.form.payment_method = payment_method
        pay.execute('choice')
        self.assertEqual(pay.state, 'end')
        self.assertEqual(invoice.amount_to_pay, Decimal('0'))
        self.assertEqual(invoice.state, 'paid')

        # UnPay
        pay = invoice.click('unpay')
        self.assertEqual(invoice.amount_to_pay, Decimal('240.00'))
        self.assertEqual(invoice.state, 'posted')
