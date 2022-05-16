#!/usr/bin/env python3
import os
from logging.config import dictConfig

import connexion
from environs import Env
from flask_cors import CORS

from settings import set_ext_logger
from swagger_server import encoder

SERVICE_ENVIRONMENT = os.getenv("SERVICE_ENVIRONMENT", "development")
debug = True
if SERVICE_ENVIRONMENT == 'production':
    debug = False

dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    }},
    'root': {
        'level': 'INFO',
        'handlers': ['wsgi']
    }
})

app = connexion.App(__name__, specification_dir='swagger_server/swagger/')
app.app.json_encoder = encoder.JSONEncoder
app.app.logger.info("The logger configured!")
set_ext_logger(app.app.logger)
app.add_api('swagger.yaml', arguments={'title': 'SYSNET Managed Dictionaries API'}, pythonic_params=True)
CORS(app.app)
env = Env()
env.read_env()


if __name__ == '__main__':
    app.run(port=8080, debug=debug)
