# This file is part account_common module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.modules.party.party import TAX_IDENTIFIER_TYPES
from trytond.model import fields
from trytond.pool import PoolMeta


class Configuration(metaclass=PoolMeta):
    __name__ = 'party.configuration'

    tax_identifier_types = fields.MultiSelection(
        'get_tax_identifier_types', "Additional Tax Identifier Types",
        help="Defines extra identifier types that are considered fiscal.\n"
        "The standard fiscal identifier types from Party are always included.")

    def get_tax_identifier_types(self):
        selection = self.fields_get(
            ['identifier_types'])['identifier_types']['selection']
        try:
            identifier_types = self.identifier_types
        except AttributeError:
            identifier_types = None
        return [
            (k, v) for k, v in selection
            if k not in TAX_IDENTIFIER_TYPES
            and (not identifier_types or k in identifier_types)]
