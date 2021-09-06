import socket
import random

HOST = 'localhost'
PORT = 3333

weight_list_1 = ['00848', '00546', '00547', '02546', '00346', '00596', '00226', '00386', '00506',
                 '00986', '00506', '02546', '03546', '03746', '00446', '00847', '00946', '00236',
                 '01116', '03336', '01246', '05446']

weight_list = ['00848']

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.settimeout(5)
    s.listen(1)
    while True:
        connection = ''
        data = f'\x02{random.choice(weight_list)}\x03'.encode()
        try:
            print("Waiting for connection...", end=' ')
            connection, addr = s.accept()
            address, port = addr
            print('Connecting with tcp://{0}:{1}'.format(address, port), end=' ')
            if address:
                connection.sendall(data)
        except socket.error as msg:
            print(msg, end='\r')
        finally:
            try:
                connection.close()
                print('Disconnecting')
            except NameError:
                pass
            except Exception as e:
                pass
                print(repr(e), end='\r')
