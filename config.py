import os

basedir = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-hard-to-guess-string'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.googlemail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', '587'))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_SUBJECT_PREFIX = '[PGPCSiS]'
    MAIL_SENDER = 'Admin <admin@pgpcsis.com>'

    @staticmethod
    def init_app(app):
        pass

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DEV_DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'webapp', 'data', 'app.db')

    @staticmethod
    def init_app(app):
        Config.init_app(app)
        # ensure data directory exists
        data_dir = os.path.join(basedir, 'webapp', 'data')
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL') or \
        'sqlite://' # in-memory database
    WTF_CSRF_ENABLED = False

    @staticmethod
    def init_app(app):
        Config.init_app(app)

class ProductionConfig(Config):
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(basedir, 'webapp', 'data', 'app.db')

    @staticmethod
    def init_app(app):
        Config.init_app(app)
        # ensure data directory exists
        data_dir = os.path.join(basedir, 'webapp', 'data')
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}