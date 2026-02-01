from flask_login import current_user
from flask_socketio import join_room, leave_room
from . import socketio

@socketio.on('join_thread')
def on_join_thread(data):
    thread_id = int(data.get('thread_id'))
    join_room(f'thread_{thread_id}')

@socketio.on('leave_thread')
def on_leave_thread(data):
    thread_id = int(data.get('thread_id'))
    leave_room(f'thread_{thread_id}')