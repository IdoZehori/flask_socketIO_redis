from flask import Flask, request, render_template
import redis
from flask_socketio import SocketIO
import threading
from flask_login import UserMixin
from datetime import datetime

app = Flask(__name__)
socketio = SocketIO(app, async_mode='threading')
r = redis.StrictRedis(host='localhost', port=6379, db=0)


def createUserId(name):
    return '.'.join([name, '#'])


class User(UserMixin):

    def __init__(self, name):
        self.name = name
        self.id = createUserId(name)
        r.hset('active_users', self.name, self.id)

    def __repr__(self):
        return f'{self.id}, {self.name}'


class OnlineUsersThread(threading.Thread):
    def __init__(self, r):
        threading.Thread.__init__(self)

    def sendOnlineUsers(self):
        allUsers = [str(user, 'utf-8') for user in r.hgetall('active_users')]
        socketio.emit('newOnlineUser', {'users': allUsers})

    def run(self):
        self.sendOnlineUsers()


class Listener(threading.Thread):
    def __init__(self, r, channels):
        threading.Thread.__init__(self)
        self.pubsub = r.pubsub()
        self.pubsub.subscribe(channels)

    def send(self, data):
        print(f"send function got {data}")
        now = datetime.now().strftime('%a, %d %b %Y %H:%M:%S')

        socketio.send({'message': data, 'time': now})

    def decodeUtf(self, item):
        # noinspection PyBroadException
        try:
            data = str(item, 'utf-8')
        except:
            data = str(item)
        return data

    def run(self):
        for item in self.pubsub.listen():
            decoded = self.decodeUtf(item['data'])
            if decoded == '1':
                continue
            self.send(decoded)


@socketio.on('connect')
def handle_listen():
    Listener(r, ['test']).start()
    OnlineUsersThread(r).start()


@socketio.on('disconectUser')
def handle_listen(user):
    print(f'deleting user: {user} from active users list')
    r.hdel('active_users', user)


@socketio.on('disconnect')
def disconnect():
    print('disconnect')


@socketio.on('message')
def handle_message(message):
    r.publish('test', message)


@app.route('/')
def index():
    return render_template('login.html')


@app.route('/conversation', methods=['POST'])
def conversation():
    context = {'username': request.form['username']}
    User(request.form['username'])

    return render_template('index.html', **context)


if __name__ == '__main__':
    socketio.run(app=app, debug=True)
