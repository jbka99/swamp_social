#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=.

# websocket stack
export USE_EVENTLET="${USE_EVENTLET:-1}"
export SOCKETIO_ASYNC_MODE="${SOCKETIO_ASYNC_MODE:-eventlet}"

# миграции
python -m flask --app run:app db upgrade || (python -m flask --app run:app db stamp head && python -m flask --app run:app db upgrade)

# запуск
exec gunicorn -k eventlet -w 1 -b 0.0.0.0:${PORT:-8000} --timeout 120 run:app