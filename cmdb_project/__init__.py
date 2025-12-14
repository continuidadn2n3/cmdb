try:
    import MySQLdb
except ImportError:
    import pymysql
    pymysql.install_as_MySQLdb()
