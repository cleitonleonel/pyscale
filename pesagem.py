# -*- coding: utf-8 -*-
#
import os
import sys
import time
import socket
import PySimpleGUIQt as sg
from datetime import datetime
from pytz import timezone
from threading import Thread
from tests.weighing import ProductsController
from ctypes import cdll, c_uint

__version__ = 'beta-001'
__user__ = 'Cleiton'

products_list = ['Selecione']
stock_data = []
totalizer_data = []
single_data = []
QT_ENTER_KEY1 = 'special 16777220'
QT_ENTER_KEY2 = 'special 16777221'


def ngrok_session():
    global host
    global port
    file_path = 'remote/ngrok_session.txt'
    if os.path.exists(file_path):
        for lines in open(file_path, 'r'):
            line = lines.split(",")
            host = line[0]
            port = int(line[1])


def get_uppercase_state():
    state = 'off'
    result = int(os.popen("xset q | grep LED").read()[65])
    if result > 0:
        state = 'on'
    return state


def force_uppercase():
    command = 0
    try:
        state = get_uppercase_state()
    except:
        state = 'off'
    if state == 'off':
        command = 2
    x11 = cdll.LoadLibrary("libX11.so.6")
    display = x11.XOpenDisplay(None)
    x11.XkbLockModifiers(display, c_uint(0x0100), c_uint(2), c_uint(command))
    x11.XCloseDisplay(display)


def get_products(parameter=None):
    if len(products_list) == 0:
        products_list.append('Selecione')
    products_base = ProductsController()
    for item in products_base.get_by_filter(parameter):
        if item.get('PROCDESC'):
            products_list.append(item.get('PROCDESC'))
    return products_list


def long_operation_thread(fun, *args):
    try:
        fun(*args)
    except:
        pass


def get_current_date():
    return datetime.now().astimezone(timezone("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M:%S")


class WeighingThread(Thread):

    def __init__(self, *args, **kwargs):
        super(WeighingThread, self).__init__(*args, **kwargs)
        self.ip = None
        self.port = 3333
        self.is_alive = True

    def stop(self):
        self.is_alive = False

    def run(self):
        cont = 0
        global result_dict
        global current_weight
        current_weight = 0
        while self.is_alive:
            result_dict['last_weight'] = current_weight
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.connect((self.ip, self.port))
                    s.sendall(b'\x05')
                    data = s.recv(1024)
                    if len(data) == 7:
                        line = data[1:6].decode()
                        if line.isdigit():
                            current_weight = int(line)
                    else:
                        try:
                            current_weight = int(data.decode())
                        except:
                            pass
                    time.sleep(0.2)
                    if current_weight > 0:
                        result_dict = {
                            "result": True,
                            "value": current_weight / 1000
                        }
                    elif cont == 5:
                        result_dict = {
                            "result": False,
                            "value": "0.00"
                        }
                except:
                    print('NENHUM SERVER ENCONTRADO.')
                    break
            cont += 1


def progress_bar(location):
    bar_layout = [[sg.Text('Salvando no estockue...', font=("verdana", 14), justification='center')],
                  [sg.Column([[sg.Frame('', layout=[
                      [sg.ProgressBar(1000, orientation='h', size=(20, 20), key='progbar')]],
                                        element_justification='center')],
                              [sg.Frame('', layout=[[sg.Cancel(size=(8, 1.2))]], element_justification='center')]])]]
    win_ = sg.Window('Melinux', bar_layout, location=location, keep_on_top=True)
    for i in range(1000):
        _event, _values = win_.read(timeout=1)
        if event == 'Cancel' or _event == sg.WIN_CLOSED:
            break
        win_['progbar'].update_bar(i + 1)
    win_.close()


def my_popup(location):
    global event_call
    button_left_frame = [
        [sg.Button("Individual", key='single', size=(8, 1.2), font=("verdana", 10),
                   button_color=('write', 'lightblue'))]
    ]
    button_right_frame = [
        [sg.Button("Totalizada", key='totalize', size=(8, 1.2), font=("verdana", 10),
                   button_color=('write', 'lightblue'))]
    ]
    popup_layout = [
        [sg.Text("Selecione o tipo de pesagem", justification='center', font=("verdana", 14))],
        [sg.Text('')],
        [sg.Column([[sg.Frame('', layout=[[sg.Text('Imprimir etiquetas automaticamente???', font=("verdana", 11))],
                                          [sg.Checkbox('', default=False, key='auto_print',
                                                       font=("verdana", 14))]])]])],
        [sg.Column([[sg.Frame('', layout=button_left_frame, element_justification='left'),
                     sg.Frame('', layout=button_right_frame, element_justification='right')]])],
        [sg.Text('')],
    ]
    win = sg.Window("Melinux", popup_layout, location=location, size=(100, 100), keep_on_top=True).Finalize()
    event_, value_ = win.read()
    click = None
    if event_ == sg.WIN_CLOSED:
        click = "cancel"
    if event_ == 'single':
        click = "single"
    if event_ == "totalize":
        click = "totalize"
    event_call = {
        "event": click,
        "check": value_['auto_print']
    }
    win.close()


def welcome_layout():
    global screen_size
    menu_def = [['File', ['Open', 'Save', 'Exit', 'Properties']],
                ['Edit', ['Paste', ['Special', 'Normal', ], 'Undo'], ],
                ['Help', 'About...'], ]

    weight_frame = [
        [sg.Text('0.00 KG', font=('digital-7', 78), background_color='lightgrey', pad=(0, 0), size_px=(600, 120),
                 key='weight', text_color='black', justification='center')]
    ]

    container_frame = [
        [sg.Frame('', layout=[[sg.Text('EMBALAGEM', font=('verdana', 15), text_color='black', background_color='grey'),
                               ]],
                  element_justification='left', background_color='grey'),
         sg.Frame('', layout=[[sg.Text('VALIDADE', font=('verdana', 15), text_color='black', background_color='grey'),
                               ]],
                  element_justification='center', background_color='grey'),
         sg.Frame('', layout=[
             [sg.Text('FAIXA ACEITÁVEL', font=('verdana', 15), text_color='black', background_color='grey'),
              ]],
                  element_justification='center', background_color='grey')],

        [sg.Frame('', layout=[[sg.Text('KG COM 1.000', font=('verdana', 20))]], element_justification='left'),
         sg.Frame('', layout=[[sg.Text(f'{dias} DIAS', font=('verdana', 20))]], element_justification='center'),
         sg.Frame('', layout=[[sg.Text(f'{acceptable_range}', font=('verdana', 20))]], element_justification='center')],
    ]

    info_frame = [
        # [sg.Frame('', layout=[[sg.Text('TESTE', font=('verdana', 15), text_color='black', background_color='grey'),
        # ]],
        # element_justification='left', background_color='grey'),
        [sg.Frame('', layout=[[sg.Text('ACUMULADO', font=('verdana', 15), text_color='black', background_color='grey'),
                               ]],
                  element_justification='center', background_color='grey'),
         sg.Frame('', layout=[[sg.Text('EXCEDENTE', font=('verdana', 15), text_color='black', background_color='grey'),
                               ]],
                  element_justification='center', background_color='grey')],
        [sg.Frame('', layout=[[sg.Text('0 CX', font=('verdana', 26), justification='left'), sg.Text(' ' * 5),
                               sg.Text('21.000 KG', font=('verdana', 26), justification='right')]],
                  element_justification='left'),
         sg.Frame('', layout=[[sg.Text('21.600 KG', font=('verdana', 26))]], element_justification='center')],

    ]

    # SEPARAR DEPOIS....
    combo_frame = [
        [sg.Text('\n' * 3)],
        [sg.Combo(default_value='Selecione', values=products_list, visible_items=6, font=('', 18), text_color='black',
                  change_submits=True, size_px=(600, 60), key='selected', pad=(0, 0), enable_events=True,
                  auto_complete=True, background_color='lightgrey'),
         # sg.Text(' '), sg.Button('Individual', size=(10, 1.5), key='toggle', enable_events=True, font=("verdana", 14)),
         # sg.Text(' '),
         sg.Text(' '), sg.Button('Imprimir', key='print', size=(10, 1.5), enable_events=True, font=("verdana", 14),
                                 button_color=('write', 'lightblue'), disabled=True),
         sg.Text(' '), sg.Button('Estocar', key='stock', size=(10, 1.5), enable_events=True, font=("verdana", 14),
                                 button_color=('write', 'lightblue'), disabled=True),
         sg.Text(' '), sg.Button('Sair', key='exit', size=(10, 1.5), font=("verdana", 14),
                                 button_color=('write', 'lightblue')), sg.Text(' ')],
    ]

    footer_frame = [
        [sg.Frame('', layout=[[sg.Text(f'Usuário: {__user__}', pad=(0, 0), background_color='lightblue',
                                       text_color="black", font=("verdana", 15), justification='left'),
                               sg.Text(f'Horário: {str(get_current_date())}', pad=(0, 0), key='clock',
                                       background_color='lightblue',
                                       text_color="black", font=("verdana", 15), justification='right')]],
                  background_color='lightblue')]
    ]

    home_layout = [
        [sg.Menu(menu_def, tearoff=True)],
        [sg.Text('Nenhum item Selecionado', font=('', 48), background_color='lightblue', pad=(1, 1),
                 size_px=(None, 130), enable_events=True, key='product_selected',
                 text_color='black', margins=(1, 1, 1, 1), justification='center')],
        [sg.Column([[sg.Frame('', layout=container_frame)]], pad=(0, 0))],
        [sg.Column([[sg.Frame('', layout=weight_frame, element_justification='left'),
                     sg.Frame('', layout=info_frame)]])],
        [sg.Text(' \n' * 17)] if screen_size[0] == 1920 else '',
        [sg.Column([[sg.Frame('', layout=combo_frame)]])],  # TENHO QUE SEPARAR DEPOIS...
        [sg.Column(layout=footer_frame, background_color='lightblue')],
    ]
    return home_layout


def create_window(layout, title):
    return sg.Window(f'Melinux | {title}',
                     layout=layout,
                     no_titlebar=False,
                     location=(0, 0),
                     border_depth=1,
                     grab_anywhere=True,
                     # disable_minimize=True,
                     # resizable=False,
                     return_keyboard_events=True,
                     keep_on_top=False).Finalize()


if __name__ == '__main__':
    screen_size = sg.Window('', alpha_channel=0).get_screen_dimensions()
    result_dict = {}
    event_call = {}
    host = 'localhost'  # '2.tcp.ngrok.io'  # 'localhost'  # '192.168.1.154'
    port = 3333
    ngrok_session()
    down = True
    disable_popup = False
    text_toggle_button = ''
    prediction_list = []
    width = None
    height = None
    last_weight = None
    current_weight = None
    dias = '180'
    max_weight = '21.600'
    min_weight = '21.000'
    acceptable_range = f'{max_weight} a {min_weight}'
    weight_thread = WeighingThread()
    weight_thread.ip = host
    weight_thread.port = port
    weight_thread.start()
    weight_task = Thread(target=long_operation_thread, args=(get_products,), daemon=True)
    weight_task.start()
    force_uppercase()
    current_layout = welcome_layout()
    window = create_window(current_layout, title='Pesagem')
    # screen_size = window.get_screen_dimensions()
    print('OLHA RESOLUÇÃO DA TELA', screen_size)
    window.Maximize()
    if screen_size[0] == 1366 and screen_size[1] == 768:
        width, height = window.size
    elif screen_size[0] == 1920 and screen_size[1] == 1080:
        width, height = screen_size
        window.size = screen_size
    while True:
        event, values = window.Read(timeout=1.5)
        # print(event, values)
        # print(result_dict)
        window['clock'].update(get_current_date())
        x, y = window.current_location()
        if event == sg.WIN_CLOSED:
            weight_thread.stop()
            weight_thread.join()
            sys.exit(0)
        elif event == 'exit':
            weight_thread.stop()
            weight_thread.join()
            force_uppercase()
            sys.exit(0)
        elif event is None:
            weight_thread.stop()
            weight_thread.join()
            break
        if event == 'About...':
            # window.disappear()
            sg.popup('Sobre o Programa', __version__,
                     'Melinux', __version__, location=(width // 2 + y - 100, height // 2 + x - 50),
                     grab_anywhere=True, keep_on_top=True, background_color="grey")
            window.reappear()
        if event == 'Open':
            filename = sg.popup_get_file('file to open', no_window=True)
            print(filename)
        if event == 'Properties':
            print(event)
            # second_window()

            ##################################### USAR MAIS TARDE ################################
            """if event == 'toggle':
                down = not down
                text_toggle_button = ('Totalizada', 'Individual')[down]
                window['toggle'].update(text_toggle_button)
                if text_toggle_button == 'Totalizada':
                    window['selected'].update(disabled=True)
                else:
                    window['selected'].update(disabled=False)
    
                if sg.Popup('Imprimir etiquetas automaticamente???',
                            title="Impressão Automática",
                            custom_text=('Sim', 'Não'),
                            location=(width // 2 + y - 50, height // 2 + x - 50),
                            keep_on_top=True,
                            font=('', 12)
                            ) == "OK":
                    print('IMPRESSÃO AUTOMÁTICA AUTORIZADA')
            """

            ##################################### USAR MAIS TARDE ################################
            """if 3 <= len(values['selected']) < 7:
                search_text = values['selected'].upper()
                get_products(search_text)
                window['selected'].update(values=products_list)
                values['selected'] = 'Selecione'
                window['selected'].update(set_to_index=0)
                # window.Refresh()
             """

            # if values['selected'] not in 'abcdefghijklmnopqrstuvxwyzABCDEFGHIJKLMNOPQRSTUVXWYZ':
            # window['selected'].update('')

        if event == 'selected':
            if values['selected'] != 'Selecione' and values['selected'] != '':
                window['product_selected'].update(values['selected'])
                window['stock'].update(disabled=False)
                window['print'].update(disabled=False)
                if not disable_popup:
                    window.disable()
                    my_popup(location=(width // 2 + y - 150, height // 2 + x - 100))
                    print('OLHA AI O TIPO DE PESAGEM:', event_call)
                    if event_call['event'] == 'totalize':
                        text_toggle_button = 'Totalizada'
                    if event_call['event'] == 'single':
                        text_toggle_button = 'Individual'
                    if event_call['check']:
                        disable_popup = True
                        window['print'].update(disabled=True)
                    window.enable()
            elif values['selected'] == 'Selecione' and values['selected'] != '':
                window['product_selected'].update('')
            products_list.clear()
            window.Refresh()
        if result_dict.get('result') and values['selected'] != 'Selecione':
            window['weight'].update(f"{result_dict['value']} KG")
            window.Refresh()
        if result_dict.get('value') and float(0.600) < float(result_dict['value']) < float(0.800) \
                and result_dict['value'] != last_weight:
            print('VOU IMPRIMIR SAPORRA...')
            event = 'print'
        if event == 'print':
            print('VOU IMPRIMIR A ETIQUETA')
            # if len(window['selected'].Values) > 0:
            # window['selected'].update(set_to_index=0)
            # values['selected'] = 'Selecione'
            last_weight = result_dict.get('value')
            result_dict['value'] = '0.00'
            # window['product_selected'].update('')
            window['weight'].update(f"{result_dict['value']} KG")
            if text_toggle_button == 'Totalizada':
                window['selected'].update(disabled=False)
                # window['toggle'].update('Individual')
                # down = True
            window.Refresh()
        if event == 'stock':
            progress_bar(location=(width // 2 + y - 150, height // 2 + x - 100))
            disable_popup = False
            window['selected'].update(set_to_index=0)
            window['product_selected'].update('')
            # window['print'].update(disabled=False)
            window['stock'].update(disabled=True)
            window['print'].update(disabled=True)
            window['weight'].update(f"0.00 KG")
        time.sleep(0.1)

    window.close()

quit()
