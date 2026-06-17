# This file is part account_common module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool, PoolMeta


class Party(metaclass=PoolMeta):
    __name__ = 'party.party'

    @classmethod
    def tax_identifier_types(cls):
        Configuration = Pool().get('party.configuration')
        types = list(super().tax_identifier_types())
        try:
            extra_types = Configuration(1).tax_identifier_types or []
        except (AssertionError, AttributeError):
            # During module setup the model or field descriptor may not yet be
            # fully bound.
            extra_types = []
        for identifier_type in extra_types:
            if identifier_type not in types:
                types.append(identifier_type)
        return types
