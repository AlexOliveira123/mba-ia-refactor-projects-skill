import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

logger = logging.getLogger('task_manager_api')


def register_error_handlers(app):
    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        if isinstance(error, HTTPException):
            # let Flask/Werkzeug's own handling stand for expected HTTP errors
            # (404, 405, ...) instead of masking them as a 500.
            return error
        logger.exception('Unhandled error: %s', error)
        return jsonify({'error': 'Erro interno'}), 500
