import logging

_logger = logging.getLogger(__name__)


def invalid_response(*, head, message, status=400):
    _logger.error(message)
    return {'status_code': status, 'error_type': head, 'error_msg': message}


def valid_response(*, head, message, status=200):
    return {'status_code': status, 'info_type': head, 'info_msg': message}
