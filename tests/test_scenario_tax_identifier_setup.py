import unittest
from unittest.mock import patch

from proteus import Model
from trytond.pool import Pool
from trytond.tests.test_tryton import DB_NAME, drop_db
from trytond.tests.tools import activate_modules
from trytond.transaction import Transaction


class TestTaxIdentifierSetup(unittest.TestCase):

    def setUp(self):
        drop_db()
        super().setUp()

    def tearDown(self):
        drop_db()
        super().tearDown()

    def test(self):
        activate_modules('account_common')
        with Transaction().start(DB_NAME, 0):
            Party = Pool().get('party.party')
            Configuration = Pool().get('party.configuration')
            standard = Party.tax_identifier_types()
            extra = Configuration(1).get_tax_identifier_types()[0][0]
        ConfigurationModel = Model.get('party.configuration')
        configuration = ConfigurationModel(1)
        configuration.tax_identifier_types = [extra]
        configuration.save()

        with Transaction().start(DB_NAME, 0):
            Party = Pool().get('party.party')
            Configuration = Pool().get('party.configuration')
            self.assertEqual(Party.tax_identifier_types(), standard + [extra])
            for field in [
                    Configuration.id, Configuration.tax_identifier_types]:
                with self.subTest(field=field.name):
                    with patch.object(field, 'name', None):
                        self.assertEqual(
                            Party.tax_identifier_types(), standard)
            self.assertEqual(Party.tax_identifier_types(), standard + [extra])
