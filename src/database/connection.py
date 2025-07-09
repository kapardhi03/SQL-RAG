import psycopg2
from psycopg2.extensions import connection

from config import settings


class PGConnection:
    def __init__(self, dsn=settings.POSTGRES_DSN.unicode_string()) -> None:
        self.dsn = dsn
        self.check_connection()
        self.conn = psycopg2.connect(self.dsn)

    def check_connection(self) -> None:
        try:
            conn = psycopg2.connect(self.dsn)
            conn.cursor()
            conn.close()
        except Exception as e:
            print(e)

    def get_conn(self) -> connection:
        return self.conn
