# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from decimal import ROUND_HALF_UP
from trytond.pool import PoolMeta


class Currency(metaclass=PoolMeta):
    __name__ = 'currency.currency'

    def round(self, amount, rounding=ROUND_HALF_UP, opposite=False):
        return super(Currency, self).round(amount, rounding=rounding,
            opposite=opposite)
