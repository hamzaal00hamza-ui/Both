"""
طبقة توافق Postgres تحاكي واجهة sqlite3.
تتيح لـ database.py الاشتغال على Postgres بدون تعديل.
"""
import os
import re
import psycopg2
import psycopg2.extras

Error = psycopg2.Error
OperationalError = psycopg2.OperationalError
IntegrityError = psycopg2.IntegrityError


class Row(dict):
    def __init__(self, mapping):
        super().__init__(mapping)
        self._keys = list(mapping.keys())

    def __getitem__(self, k):
        if isinstance(k, int):
            return super().__getitem__(self._keys[k])
        return super().__getitem__(k)

    def keys(self):
        return list(self._keys)


def _translate_placeholders(sql):
    out = []
    in_str = False
    quote = None
    for ch in sql:
        if in_str:
            out.append(ch)
            if ch == quote:
                in_str = False
        else:
            if ch in ("'", '"'):
                in_str = True
                quote = ch
                out.append(ch)
            elif ch == '?':
                out.append('%s')
            else:
                out.append(ch)
    return ''.join(out)


_TYPE_RE = re.compile(r'\bINTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT\b', re.IGNORECASE)
_REAL_RE = re.compile(r'\bREAL\b', re.IGNORECASE)
_IGNORE_RE = re.compile(r'INSERT\s+OR\s+IGNORE\s+INTO', re.IGNORECASE)
_REPLACE_RE = re.compile(r'INSERT\s+OR\s+REPLACE\s+INTO', re.IGNORECASE)
_ALTER_ADD_RE = re.compile(r'(ALTER\s+TABLE\s+\w+\s+ADD\s+COLUMN)\s+(?!IF\s+NOT\s+EXISTS)', re.IGNORECASE)
_INSERT_HEAD_RE = re.compile(r'^\s*INSERT\s+INTO', re.IGNORECASE)
_RETURNING_RE = re.compile(r'\bRETURNING\b', re.IGNORECASE)


def _translate(sql):
    has_ignore = bool(_IGNORE_RE.search(sql))
    if has_ignore:
        sql = _IGNORE_RE.sub('INSERT INTO', sql)
    if _REPLACE_RE.search(sql):
        sql = _REPLACE_RE.sub('INSERT INTO', sql)
    sql = _TYPE_RE.sub('SERIAL PRIMARY KEY', sql)
    sql = _REAL_RE.sub('DOUBLE PRECISION', sql)
    sql = _ALTER_ADD_RE.sub(r'\1 IF NOT EXISTS ', sql)
    sql = _translate_placeholders(sql)
    if has_ignore and 'ON CONFLICT' not in sql.upper():
        sql = sql.rstrip().rstrip(';') + ' ON CONFLICT DO NOTHING'
    is_insert = bool(_INSERT_HEAD_RE.match(sql))
    if is_insert and not _RETURNING_RE.search(sql):
        sql = sql.rstrip().rstrip(';') + ' RETURNING *'
    return sql, is_insert


class _Cursor:
    def __init__(self, conn):
        self._conn = conn
        self._cur = conn._conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        self.lastrowid = None
        self._consumed_insert = False

    def execute(self, sql, params=()):
        sql_pg, is_insert = _translate(sql)
        params_t = tuple(params) if params else None
        try:
            self._cur.execute(sql_pg, params_t)
        except psycopg2.Error:
            try:
                self._conn._conn.rollback()
            except Exception:
                pass
            raise
        self.lastrowid = None
        self._consumed_insert = False
        if is_insert:
            try:
                if self._cur.description:
                    row = self._cur.fetchone()
                    if row is not None:
                        try:
                            self.lastrowid = row[0]
                        except Exception:
                            self.lastrowid = None
                self._consumed_insert = True
            except psycopg2.Error:
                pass
        return self

    def executemany(self, sql, seq):
        for params in seq:
            self.execute(sql, params)
        return self

    def fetchone(self):
        if self._consumed_insert:
            self._consumed_insert = False
            return None
        try:
            row = self._cur.fetchone()
        except psycopg2.Error:
            return None
        if row is None:
            return None
        return Row(dict(row))

    def fetchall(self):
        if self._consumed_insert:
            self._consumed_insert = False
            return []
        try:
            rows = self._cur.fetchall()
        except psycopg2.Error:
            return []
        return [Row(dict(r)) for r in rows]

    def close(self):
        try:
            self._cur.close()
        except Exception:
            pass

    @property
    def rowcount(self):
        try:
            return self._cur.rowcount
        except Exception:
            return -1

    def __iter__(self):
        return iter(self.fetchall())


class _Connection:
    row_factory = None

    def __init__(self, dsn):
        self._conn = psycopg2.connect(dsn)
        self._conn.autocommit = True

    def cursor(self):
        return _Cursor(self)

    def commit(self):
        pass

    def rollback(self):
        try:
            self._conn.rollback()
        except Exception:
            pass

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


def connect(_path_unused=None):
    dsn = os.environ.get('DATABASE_URL', '')
    if not dsn:
        raise RuntimeError('DATABASE_URL environment variable is not set')
    if dsn.startswith('postgres://'):
        dsn = 'postgresql://' + dsn[len('postgres://'):]
    return _Connection(dsn)
