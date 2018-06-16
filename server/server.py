import tornado.web
import tornado.websocket
import tornado.ioloop
import struct

next_index = 0
boards = []
targets = []
enemies = []
sockets = []
waiting = -1
turns = []
sunk = []


def create_player(index):
    if(index<len(turns)):
        boards[index]=[0 for x in range(0, 100)]
        targets[index]=[1 for x in range(0, 100)]
        turns[index]=-2

    while (len(turns) <= index):
        boards.append([0 for x in range(0, 100)])
        targets.append([1 for x in range(0, 100)])
        turns.append(-2)

def start_game(a, b):
    while (len(enemies) <= a or len(enemies) <= b):
        enemies.append(-1);
        sunk.append(0)
    sunk[a]=0
    sunk[b]=0
    enemies[a] = b
    enemies[b] = a
    turns[a] = 3
    turns[b] = 0
    sockets[a].write_message(struct.pack("bb", 4, turns[a]), binary=True)
    sockets[b].write_message(struct.pack("bb", 4, turns[b]), binary=True)


def check_sunk(board, x, y):
    x2 = x - 1
    l = [x, y]
    r = 0
    while (x2 >= 0):
        s = board[x2 * 10 + y]
        if (s == 0 or s==3):
            break
        if (s == 1):
            return 0, []
        if (s == 2):
            l.append(x2)
            r = r + 1;
        x2 = x2 - 1
    x2 = x + 1
    while (x2 < 10):
        s = board[x2 * 10 + y]
        if (s == 0 or s==3):
            break
        if (s == 1):
            return 0, []
        if (s == 2):
            l.append(x2)
            r = r + 1;
        x2 = x2 + 1
    y2 = y - 1
    while (y2 >= 0):
        s = board[x * 10 + y2]
        if (s == 0 or s==3):
            break
        if (s == 1):
            return 0, []
        if (s == 2):
            l.append(y2)
            r = r - 1;
        y2 = y2 - 1
    y2 = y + 1
    while (y2 < 10):
        s = board[x * 10 + y2]
        if (s == 0 or s==3):
            break
        if (s == 1):
            return 0, []
        if (s == 2):
            l.append(y2)
            r = r - 1;
        y2 = y2 + 1
    return (r, l)


def sink(a, b, s, l):
    f = "bbb" + str(len(l)) + "s"
    sockets[b].write_message(struct.pack(f, 7, 1, s, bytes(l)), binary=True)
    sockets[a].write_message(struct.pack(f, 7, 0, s, bytes(l)), binary=True)
    b1 = boards[b]
    b2 = targets[a]
    x = l[0]
    y = l[1]
    b1[x * 10 + y] = 4
    b2[x * 10 + y] = 4
    if (s > 0):
        for i in range(0, s):
            x2 = l[2 + i]
            b1[x2 * 10 + y] = 4
            b2[x2 * 10 + y] = 4
    else:
        for i in range(0, -s):
            y2 = l[2 + i]
            b1[x * 10 + y2] = 4
            b2[x * 10 + y2] = 4
    sunk[a] += 1
    if(sunk[a]==5):
        sockets[b].write_message(struct.pack("bb", 8, 0), binary=True)
        sockets[a].write_message(struct.pack("bb", 8, 1), binary=True)
        create_player(a)
        create_player(b)

def resolve_shot(id, x, y):
    enemy = enemies[id]
    board = boards[enemy]
    target = targets[id]
    s1 = -1
    s2 = -1
    s = 0
    l = []
    if board[x * 10 + y] == 0:
        s1 = 3
        s2 = 0
    elif board[x * 10 + y] == 1:
        s1 = 2
        s2 = 2
        (s, l) = check_sunk(board, x, y)
    board[x * 10 + y] = s1
    target[x * 10 + y] = s2
    sockets[enemy].write_message(struct.pack("bbbbb", 6, 1, x, y, s1), binary=True)
    sockets[id].write_message(struct.pack("bbbbb", 6, 0, x, y, s2), binary=True)
    turns[id] -= 1
    if (turns[id] == 0):
        turns[enemy] = 3
    sockets[id].write_message(struct.pack("bb", 4, turns[id]), binary=True)
    sockets[enemy].write_message(struct.pack("bb", 4, turns[enemy]), binary=True)
    if (s != 0):
        sink(id, enemy, s, l)


class EchoHandler(tornado.websocket.WebSocketHandler):
    def open(self):
        print("open")

    def on_close(self):
        print("close")

    def on_message(self, message):
        global next_index, boards, targets, sockets, waiting, turns
        print("message " + str(message[0]))
        if (message == "Hello"):
            self.write_message(bytes([1, next_index]), binary=True)
            create_player(next_index)
            next_index = next_index + 1

        elif (message[0] == 0):
            if (len(turns) <= message[1]):
                create_player(message[1])
            self.write_message(struct.pack("bb100s100s", 2, turns[message[1]],
                                           bytes(boards[message[1]]),
                                           bytes(targets[message[1]])), binary=True)
            while (len(sockets) <= message[1]):
                sockets.append(0)
            sockets[message[1]] = self
        elif message[0] == 3:
            if (waiting < 0):
                waiting = message[1]
                tmp = -1
                turns[message[1]] = -1
                self.write_message(struct.pack("bb", 4, turns[message[1]]), binary=True)
            else:
                tmp = waiting
                waiting = -1
            boards[message[1]] = [x for x in message[2:]]
            if (tmp >= 0):
                start_game(tmp, message[1])
        elif (message[0] == 5):
            resolve_shot(message[1], message[2], message[3])
        elif (message[0]==10):
            if(turns[message[1]]!=-2):
                sockets[enemies[message[1]]].write_message(struct.pack("bb", 11, 0), binary=True)
                create_player(enemies[message[1]])
            create_player(message[1])

        else:
            print(message);

    def check_origin(self, origin):
        print("ORIGIN: ", origin)
        return True



if __name__ == "__main__":
    app = tornado.web.Application([
        ("/ws", EchoHandler),
    ])
    app.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
