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

        configuration = Configuration(1)
        configuration.tax_identifier_types = ['be_vat']
        configuration.save()

        self.assertEqual(default_types, Party.tax_identifier_types())
        self.assertNotIn(
            ('be_vat', "Belgian Enterprise Number"),
            configuration.get_tax_identifier_types())
        self.assertIn(
            ('es_cif', "Spanish Company Tax"),
            configuration.get_tax_identifier_types())

        configuration.tax_identifier_types = ['es_cif']
        configuration.save()

        self.assertEqual(
            Party.tax_identifier_types(),
            default_types + ['es_cif'])

del ModuleTestCase
