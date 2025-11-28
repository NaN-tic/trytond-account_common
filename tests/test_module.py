# This file is part account_common module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.tests.test_tryton import ModuleTestCase


class AccountCommonTestCase(ModuleTestCase):
    'Test Account Common module'
    module = 'account_common'
    extras = ['account_payment']

del ModuleTestCase
