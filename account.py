# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction


class Period(metaclass=PoolMeta):
    __name__ = 'account.period'
    code = fields.Char('Code', size=None)

    @classmethod
    def search_rec_name(cls, name, clause):
        if clause[1].startswith('!') or clause[1].startswith('not '):
            bool_op = 'AND'
        else:
            bool_op = 'OR'
        return [bool_op,
            ('code',) + tuple(clause[1:]),
            (cls._rec_name,) + tuple(clause[1:]),
            ]


class _TaxRuleLineMixin:
    __slots__ = ()

    from_organization = fields.Many2One(
        'country.organization', 'From Organization', ondelete='RESTRICT',
        help="Apply only to addresses in countries belonging to this organization.")
    to_organization = fields.Many2One(
        'country.organization', 'To Organization', ondelete='RESTRICT',
        help="Apply only to addresses in countries belonging to this organization.")


class TaxRuleLineTemplate(_TaxRuleLineMixin, metaclass=PoolMeta):
    __name__ = 'account.tax.rule.line.template'

    def _get_tax_rule_line_value(self, rule_line=None):
        value = super()._get_tax_rule_line_value(rule_line=rule_line)
        for name in ['from_organization', 'to_organization']:
            organization = getattr(self, name)
            if not rule_line or getattr(rule_line, name) != organization:
                value[name] = organization.id if organization else None
        return value


class TaxRuleLine(_TaxRuleLineMixin, metaclass=PoolMeta):
    __name__ = 'account.tax.rule.line'

    def match(self, pattern):
        pool = Pool()
        Member = pool.get('country.organization.member')
        Date = pool.get('ir.date')

        if not super().match(pattern):
            return False
        if not self.from_organization and not self.to_organization:
            return True

        date = pattern.get('date')
        if not date:
            with Transaction().set_context(company=self.rule.company.id):
                date = Date.today()

        for direction in ['from', 'to']:
            organization = getattr(self, f'{direction}_organization')
            if not organization:
                continue
            country = pattern.get(f'{direction}_country')
            if not country:
                return False
            if not Member.search([
                        ('country', '=', country),
                        ('organization', '=', organization.id),
                        ['OR',
                            ('from_date', '=', None),
                            ('from_date', '<=', date),
                            ],
                        ['OR',
                            ('to_date', '=', None),
                            ('to_date', '>=', date),
                            ],
                        ], limit=1, order=[]):
                return False
        return True
