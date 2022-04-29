import logging
from logging.handlers import SMTPHandler, RotatingFileHandler
from flask import Flask
from config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
import os
from flask_mail import Mail
from flask_session import Session
from waitress import serve
import redis

app = Flask(__name__)
app.config.from_object(Config)
if app.config["CACHE_TYPE"] == "RedisCache" :
    redis_password = os.environ.get('REDIS_PASSWORD') or 'REDIS_PASSWORD'
    redis_address = os.environ.get('REDIS_ADDRESS') or None
    session_redis= redis.from_url('redis://:%s@%s' %(redis_password,redis_address))
    app.config["REDIS_ADDRESS"]=redis_address
    app.config["SESSION_REDIS"]=session_redis
elif app.config["CACHE_TYPE"] == "RedisSentinelCache" :
    sentinel = redis.sentinel.Sentinel([ (os.environ.get('CACHE_REDIS_SENTINELS_address'), os.environ.get('CACHE_REDIS_SENTINELS_port')) ], password=os.environ.get('REDIS_PASSWORD'), sentinel_kwargs={"password": os.environ.get('REDIS_PASSWORD')})
    connection=sentinel.master_for(os.environ.get('CACHE_REDIS_SENTINEL_MASTER'), socket_timeout=0.1)
    app.config["SESSION_REDIS"]=connection

db = SQLAlchemy(app ,engine_options={"pool_pre_ping":True, "pool_size":0,"pool_recycle":-1} )
migrate = Migrate(app, db)
login = LoginManager(app)
login.login_view = 'login'
mail = Mail(app)
sess = Session()
sess.init_app(app)

#wsgi_app = app.wsgi_app

from flaski import routes, models, errors, storage, settings
from flaski.apps import base

# from flaski.apps.routes import scatterplot, iscatterplot, heatmap, iheatmap, venndiagram, icellplot, david, aarnaseqlake, pca, histogram, violinplot, iviolinplot, mds, tsne

# if app.config['INSTANCE'] != "latest" :
#     from flaski.apps.routes import ihistogram, lifespan

if not app.debug:
    if app.config['MAIL_SERVER']:
        auth = None
        if app.config['MAIL_USERNAME'] or app.config['MAIL_PASSWORD']:
            auth = (app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        secure = None
        if app.config['MAIL_USE_TLS']:
            secure = ()
        mail_handler = SMTPHandler(
            mailhost=(app.config['MAIL_SERVER'], app.config['MAIL_PORT']),
            fromaddr=app.config['ADMINS'][0],
            toaddrs=app.config['ADMINS'], subject='%s :: Flaski Failure' %(app.config['INSTANCE']),
            credentials=auth, secure=secure)
        mail_handler.setLevel(logging.ERROR)
        app.logger.addHandler(mail_handler)

    if not os.path.exists(app.config['LOGS']):
        os.mkdir(app.config['LOGS'])
    file_handler = RotatingFileHandler(app.config['LOGS']+'flaski.log', maxBytes=10240, backupCount=10)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'))
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)

    app.logger.setLevel(logging.INFO)
    app.logger.info('Flaski startup')

# if __name__ == "__main__":
#    #app.run() ##Replaced with below code to run it using waitress 
#    serve(app, host='0.0.0.0', port=8000)
