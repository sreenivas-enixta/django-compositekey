__author__ = 'aldaran'

from django.conf import settings

SEPARATOR = getattr(settings, "SELECT_IN_SQL_SEPARATOR",   '#')

service = {}

class MultipleColumnsIN(object):
    def __init__(self, cols, values):
        self.cols = cols
        self.values = values

    def as_sql(self, qn, connection):
        return service.get(connection.vendor, UseConcat)(self.cols, self.values).as_sql(qn, connection)

class UseConcat(object):
    """
    Concat columns and values.

    SQLITE note quote(column)
    """
    concat = "||"
    cq = "quote(%s)"

    def __init__(self, cols, values):
        self.cols = cols
        self.values = values

    def quote_v(self, value):
        if isinstance(value, int):
            return str(value)
        return "'%s'" % (str(value).replace("'", "''"))

    def as_sql(self, qn=None, connection=None):
        col_sep = self.quote_v(SEPARATOR).join([self.concat]*2)

        if isinstance(self.cols, (list, tuple)):
            # there are more than one column
            column = col_sep.join([self.cq % qn(c) for c in self.cols])
            params = [SEPARATOR.join([self.quote_v(v) for v in val]) for val in self.values]
        else:
            column = self.cq % qn(self.cols)
            params = [self.quote_v(v) for v in self.values]
        return '%s IN (%s)' % (column, ",".join(["%s"] * len(params))), tuple(params or ())

class UseConcatQuote(UseConcat):
    """
    POSTGRES quote_literal
    """
    cq = "quote_literal(%s)"

    def quote_v(self, value):
        return "'%s'" % (str(value).replace("'", "''"))

class UseTuple(object):
    """
    MYSQL
    ORACLE
    """
    template = '%s IN (%%s)'

    def __init__(self, cols, values):
        self.cols = cols
        self.values = values

    def as_sql(self, qn=None, connection=None):
        if isinstance(self.cols, (list, tuple)):
            # there are more than one column
            column = "(%s)" % ",".join([qn(c) for c in self.cols])
            params = ["(%s)" % ",".join(val) for val in self.values]
        else:
            column = qn(self.cols)
            params = self.values
        return self.template % column, tuple(params or ())



class UseTupleValues(UseTuple):
    """
    DB2 (with values)
    """
    template = '%s IN (values %%s)'

service["sqlite"] = UseConcat
service["postgresql"] = UseConcatQuote
service["mysql"] = UseTuple
service["oracle"] = UseTuple
service["DB2"] = UseTupleValues