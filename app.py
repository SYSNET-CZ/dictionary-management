#!/usr/bin/env python3
import logging
import os
from logging.config import dictConfig

import connexion
from environs import Env
from flask_cors import CORS

from settings import set_ext_logger, LOG_DATE_FORMAT, ERROR_FILE_PATH, LOG_FILE_PATH, DEBUG_FILE_PATH, APP_NAME
from swagger_server import encoder

SERVICE_ENVIRONMENT = os.getenv("SERVICE_ENVIRONMENT", "development")
debug = True
if SERVICE_ENVIRONMENT == 'production':
    debug = False

dictConfig({
    'version': 1,
    'formatters': {
        'default': {
            'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
            'datefmt': LOG_DATE_FORMAT,
        },
        'simple': {
            'format': '%(asctime)s %(levelname)s in %(name)s: %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'info': {
            'format': '[%(asctime)s] %(levelname)s in %(name)s::%(module)s|%(lineno)s:: %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'error': {
            'format': '[%(asctime)s] %(levelname)s in %(name)s %(process)d::%(module)s|%(lineno)s:: %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        'wsgi': {
            'class': 'logging.StreamHandler',
            'stream': 'ext://flask.logging.wsgi_errors_stream',
            'formatter': 'default',
            'level': logging.INFO,
        },
        'error_file_handler': {
            'class': 'logging.FileHandler',
            'formatter': 'error',
            'filename': ERROR_FILE_PATH,
            'level': logging.WARN,
            'mode': 'a',
            'encoding': 'utf-8',
        },
        'info_rotating_file_handler': {
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'info',
            'level': logging.INFO,
            'filename': LOG_FILE_PATH,
            'mode': 'a',
            'encoding': 'utf-8',
            'maxBytes': 500000,
            'backupCount': 10
        },
        'debug_rotating_file_handler': {
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'error',
            'level': logging.DEBUG,
            'filename': DEBUG_FILE_PATH,
            'mode': 'a',
            'encoding': 'utf-8',
            'maxBytes': 1000000,
            'backupCount': 10
        },
    },
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi', 'info_rotating_file_handler', 'error_file_handler', 'debug_rotating_file_handler']
    },
})

app = connexion.App(__name__, specification_dir='swagger_server/swagger/')
app.app.json_encoder = encoder.JSONEncoder
app.app.logger.info("The logger configured!")
set_ext_logger(app.app.logger)
app.add_api('swagger.yaml', arguments={'title': APP_NAME}, pythonic_params=True)
CORS(app.app)
env = Env()
env.read_env()


if __name__ == '__main__':
    app.run(port=8080, debug=debug)
