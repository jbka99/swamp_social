import os
# Патчим максимально рано — еще до импорта gunicorn и всего остального
if os.getenv("USE_EVENTLET", "0") == "1":
    import eventlet
    eventlet.monkey_patch()