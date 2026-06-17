# This file is part account_common module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool
from trytond.tests.test_tryton import ModuleTestCase, with_transaction


class AccountCommonTestCase(ModuleTestCase):
    'Test Account Common module'
    module = 'account_common'
    extras = ['account_payment']

    @with_transaction()
    def test_tax_identifier_types(self):
        'Test additional tax identifier types from configuration'
        pool = Pool()
        Configuration = pool.get('party.configuration')
        Party = pool.get('party.party')

        default_types = list(Party.tax_identifier_types())
        additional_type = 'be_businessid'

        configuration = Configuration(1)
        self.assertNotIn(additional_type, default_types)
        self.assertEqual(default_types, Party.tax_identifier_types())
        self.assertIn(
            (additional_type, "Belgian Company Number"),
            configuration.get_tax_identifier_types())
        self.assertIn(
            ('es_cif', "Spanish Company Tax"),
            configuration.get_tax_identifier_types())

        configuration.tax_identifier_types = [additional_type]
        configuration.save()

        self.assertEqual(
            Party.tax_identifier_types(),
            default_types + [additional_type])

del ModuleTestCase
