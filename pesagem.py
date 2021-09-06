# -*- coding: utf-8 -*-
#
import os
import io
import sys
import time
import socket
import serial
import subprocess
import PySimpleGUIQt as sg
from pytz import timezone
from threading import Thread
from datetime import datetime
from ctypes import cdll, c_uint
from PIL import Image, ImageSequence
from tests.weighing import ProductsController

__version__ = 'beta-001'
__user__ = 'Cleiton'

products_list = ['Selecione']
stock_data = []
totalizer_data = []
single_data = []

QT_ENTER_KEY1 = 'special 16777220'
QT_ENTER_KEY2 = 'special 16777221'

STX = chr(2)
CR = chr(13)

settings = {"printer": "ARGOX_OS-2140"}  # {"printer": "POS80"}


def run_command(command):
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    output, error = process.communicate()
    return output, error


def check_printer_status(printer_name):
    global status_result
    command = "lpstat -p"
    process = run_command(command)[0].decode().strip()
    printers_list = [line for line in process.split('\n') if "Unplugged or turned off" not in line]
    active_printer = [printer_status for idx, printer_status in enumerate(printers_list)
                      if printer_name in printer_status][0].split(' ')
    if "desabilitada" in active_printer or "inativa" in active_printer:
        print(f"IMPRESSORA {settings['printer']} ESTÁ DESABILITADA OU INATIVA.")
        status_result = False
    return status_result


def get_printers():
    command = "lpstat -a | awk '{print $1}'"
    result = run_command(command)[0].decode().strip()
    return result.split('\n')


def print_file(file_name):
    search_printers = [p_name for idx, p_name in enumerate(get_printers()) if p_name == settings["printer"]]
    if len(search_printers) == 1:
        command = f'cat {file_name} | lpr -P {settings["printer"]}'
        run_command(command)
    else:
        print('IMPRESSORA NÃO EXISTE!!!')


def label_make(product):
    argox_code_11 = '\n'.join([
        f"{STX}{CR}",
        f"{STX}L{CR}",
        f"121200001900020{product['name']}{CR}",
        f"111200001500020Data Emb:{product['creation_date']}{CR}",
        f"111200001500220Validade:{product['validate']}{CR}",
        f"111200001200020Peso Bruto:{CR}",
        f"112200001200120  {product['weight']} Kg{CR}",
        f"111200000900020Peso Embal:{CR}",
        f"112200000900090    {product['weight_pack']}{CR}",
        f"1E2103000600210{product['bar_code']}{CR}",
        f"111200000150020Peso liquido:{CR}",
        f"122200000150150  {product['weight']} Kg{CR}",
        f"Q0001{CR}",
        f"E{CR}",
    ])

    with open('labels/etiquetas.txt', 'w') as file:
        file.write(argox_code_11 + '\n')


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


def force_uppercase(start=False):
    command = 0
    if start:
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


def get_local_weight():
    global result_dict
    weight = 0
    ser_ = serial.Serial()
    ser_.port = '/dev/ttyUSB0'
    ser_.baudrate = 4800
    ser_.rtscts = None
    ser_.xonxoff = None
    ser_.timeout = 1

    try:
        os.system('sudo chmod 777 /dev/ttyUSB*')
        ser_.open()
    except serial.SerialException as e:
        print(e)
        result_dict = {
            "result": False,
            "value": f'{0 / 1000:.3f}',
        }
        return result_dict
    ser_.write(chr(5).encode())
    try:
        data = ser_.readline()
    except:
        result_dict = {
            "result": False,
            "value": f'{0 / 1000:.3f}',
        }
        return result_dict
    if len(data) == 7:
        line = data[1:6].decode()
        if line.isdigit():
            weight = int(line)
    if weight > 0:
        result_dict = {
            "result": True,
            "value": f'{weight / 1000:.3f}',
        }
    else:
        result_dict = {
            "result": False,
            "value": f'{0 / 1000:.3f}',
        }
    return result_dict


def check_type_weighing():
    while True:
        time.sleep(3)
        if result_dict.get("is_server"):
            print(result_dict)
            break
        else:
            print('\rNão é um servidor, vou executar a leitura local...', end='')
            get_local_weight()


def resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)


def get_img_bytes(img_bytes, extension=None):
    if not extension:
        extension = 'PNG'
    bio = io.BytesIO()
    img_bytes.save(bio, format=extension)
    return bio.getvalue()


def get_img_frames(filename):
    gif_filename = resource_path(filename)
    sequence_frames = [get_img_bytes(img.convert('RGBA')) for img in ImageSequence.Iterator(Image.open(gif_filename))]
    frame_duration = Image.open(gif_filename).info['duration']
    return sequence_frames, frame_duration


def animation_image(window, file_name, seconds=2, text=''):
    sequence, duration = get_img_frames(file_name)
    idx = 0
    while idx in range(seconds):
        for frame in sequence:
            window.read(timeout=duration)
            window['loading'].update(data=frame)
            window['p_text'].update(text)
        idx += 1


def printer(location):
    printer_layout = [[sg.Text('', font=("verdana", 14), justification='center', key="p_text")],
                      [sg.Column([[sg.Frame('', layout=[[sg.Image(key='loading')]],
                                            element_justification='center')]])]]
    win_ = sg.Window('Melinux', printer_layout, location=location, keep_on_top=True, size=(400, 300))
    status = check_printer_status(settings['printer'])
    if status:
        Thread(target=long_operation_thread, args=(print_file,
                                                   os.path.join(".", "labels/etiquetas.txt"),), daemon=True).start()
        animation_image(win_, 'src/images/printer_mine.gif', text='Imprimindo, aguarde...')
    else:
        animation_image(win_, 'src/images/balloon.gif', seconds=1, text='Impressora não encontrada!!!')
    for i in range(5):
        _event, _values = win_.read(1)
        if _event == sg.WIN_CLOSED:
            break
    win_.close()


def progress_bar(location):
    bar_layout = [[sg.Text('Salvando no estoque...', font=("verdana", 14), justification='center')],
                  [sg.Column([[sg.Frame('', layout=[
                      [sg.ProgressBar(1000, orientation='h', size=(20, 20), key='progress_bar')]],
                                        element_justification='center')],
                              [sg.Frame('', layout=[[sg.Cancel(size=(8, 1.2))]], element_justification='center')]])]]
    win_ = sg.Window('Melinux', bar_layout, location=location, keep_on_top=True)
    for i in range(1000):
        _event, _values = win_.read(timeout=1)
        if _event == 'Cancel' or _event == sg.WIN_CLOSED:
            break
        win_['progress_bar'].update_bar(i + 1)
    win_.close()


def my_popup(location):
    global event_call
    button_left_frame = [
        [sg.Button("Individual", key='single', size=(8, 1.2), font=("verdana", 10),
                   button_color=('black', '#5f6d8c'))]
    ]
    button_right_frame = [
        [sg.Button("Totalizada", key='totalize', size=(8, 1.2), font=("verdana", 10),
                   button_color=('black', '#5f6d8c'))]
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


def event_manager():
    global disable_popup
    global text_toggle_button
    if values['selected'] != 'Selecione' and values['selected'] != '':
        window['product_selected'].update(values['selected'])
        if not disable_popup:
            window.disable()
            window['print'].update(disabled=False, button_color=('black', '#5f6d8c'))
            my_popup(location=(width // 2 + y - 150, height // 2 + x - 100))
            # print('OLHA AI O TIPO DE PESAGEM:', event_call)
            if event_call['event'] == 'totalize':
                text_toggle_button = 'Totalizada'
            if event_call['event'] == 'single':
                text_toggle_button = 'Individual'
            if event_call['check']:
                disable_popup = True
                window['print'].update(disabled=True, button_color=('black', 'grey'))
            window.enable()
    if values['selected'] == 'Selecione' and values['selected'] != '':
        window['product_selected'].update('')
    products_list.clear()
    window.Refresh()


def welcome_layout():
    global screen_size
    menu_def = [['File', ['Open', 'Save', 'Exit', 'Properties']],
                ['Edit', ['Paste', ['Special', 'Normal', ], 'Undo'], ],
                ['Help', 'About...'], ]

    weight_frame = [
        [sg.Text(f'{0 / 1000:.3f} KG', font=('digital-7', 78), background_color='lightgrey', pad=(0, 0),
                 size_px=(600, 120), key='weight', text_color='black', justification='center')]
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

        [sg.Frame('', layout=[[sg.Text('COM 1.000 KG', font=('verdana', 20))]], element_justification='left'),
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

    combo_frame = [
        [sg.Text('\n' * 3)],
        [sg.Combo(default_value='Selecione', values=products_list, visible_items=6, font=('', 18), text_color='black',
                  change_submits=True, size_px=(600, 60), key='selected', pad=(0, 0), enable_events=True,
                  auto_complete=True, background_color='lightgrey'),
         # sg.Text(' '), sg.Button('Individual', size=(10, 1.5), key='toggle',
         # enable_events=True, font=("verdana", 14)),
         # sg.Text(' '),
         ],
    ]

    buttons_frame = [
        [sg.Text('\n' * 3)],
        [sg.Text(' '), sg.Button('Imprimir', key='print', size=(12, 1.5), enable_events=True, font=("verdana", 14),
                                 button_color=('black', 'grey'), disabled=True),
         sg.Text(' '), sg.Button('Estocar', key='stock', size=(12, 1.5), enable_events=True, font=("verdana", 14),
                                 button_color=('black', 'grey'), disabled=True),
         sg.Text(' '), sg.Button('Sair', key='exit', size=(12, 1.5), font=("verdana", 14),
                                 button_color=('black', '#5f6d8c')), sg.Text(' ')]
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
        [sg.Column([[sg.Frame('', layout=combo_frame), sg.Frame('', layout=buttons_frame)]])],
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


class WeighingThread(Thread):

    def __init__(self, *args, **kwargs):
        super(WeighingThread, self).__init__(*args, **kwargs)
        self.ip = None
        self.port = 3333
        self.is_alive = True

    def stop(self):
        self.is_alive = False

    def run(self):
        global result_dict
        global current_weight
        cont = 0
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
                    if current_weight > 0:
                        result_dict = {
                            "result": True,
                            "value": f'{current_weight / 1000:.3f}',
                            "is_server": True
                        }
                    elif cont == 5:
                        result_dict = {
                            "result": False,
                            "value": f'{0 / 1000:.3f}',
                            "is_server": False
                        }
                except:
                    result_dict = {
                        "result": False,
                        "value": f'{0 / 1000:.3f}',
                    }
                    break
                time.sleep(0.1)
            cont += 1


if __name__ == '__main__':
    screen_size = sg.Window('', alpha_channel=0).get_screen_dimensions()
    result_dict = {}
    event_call = {}
    status_result = True
    host = 'localhost'  # '2.tcp.ngrok.io'  # 'localhost'  # '192.168.1.154'
    port = 3333
    # ngrok_session()
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
    acceptable_range = f'{min_weight} a {max_weight}'
    weight_thread = WeighingThread()
    weight_thread.ip = host
    weight_thread.port = port
    weight_thread.start()
    weight_task = Thread(target=long_operation_thread, args=(get_products,), daemon=True)
    weight_task.start()
    weight_type_task = Thread(target=long_operation_thread, args=(check_type_weighing,), daemon=True)
    weight_type_task.start()
    force_uppercase(True)
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
        elif event == 'About...':
            # window.disappear()
            sg.popup('Sobre o Programa', __version__,
                     'Melinux', __version__, location=(width // 2 + y - 100, height // 2 + x - 50),
                     grab_anywhere=True, keep_on_top=True, background_color="grey")
            window.reappear()
        elif event == 'Open':
            filename = sg.popup_get_file('file to open', no_window=True)
            print(filename)
        elif event == 'Properties':
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

        if event == QT_ENTER_KEY1:
            event_manager()
        elif event == 'selected':
            event_manager()
        if result_dict.get('result') and values['selected'] != 'Selecione':
            window['weight'].update(f"{result_dict['value']} KG")
            window.Refresh()
        if event_call.get('check') and values['selected'] != 'Selecione' and result_dict.get('value') and float(
                0.600) < float(result_dict['value']) < float(0.800) \
                and result_dict['value'] != last_weight:
            event = 'print'
        if event == 'print':
            product_dict = {
                "name": values['selected'],
                "creation_date": '31-08-2021',
                "validate": '31-08-2021',
                "weight": result_dict['value'],
                "weight_pack": '1g',
                "bar_code": '2006080000006'
            }
            label_make(product_dict)
            window.disable()
            printer(location=(width // 2 + y - 150, height // 2 + x - 100))
            window.enable()
            if status_result:
                window['stock'].update(disabled=False, button_color=('black', '#5f6d8c'))
            # print(result_dict['value'])
            # if len(window['selected'].Values) > 0:
            # window['selected'].update(set_to_index=0)
            # values['selected'] = 'Selecione'
            last_weight = result_dict.get('value')
            result_dict['value'] = f'{0 / 1000:.3f}'
            # window['product_selected'].update('')
            window['weight'].update(f"{result_dict['value']} KG")
            if text_toggle_button == 'Totalizada':
                window['selected'].update(disabled=False)
                # window['toggle'].update('Individual')
                # down = True
            window.Refresh()
            # time.sleep(5)
        if event == 'stock':
            window.disable()
            progress_bar(location=(width // 2 + y - 150, height // 2 + x - 100))
            window.enable()
            disable_popup = False
            window['selected'].update(set_to_index=0)
            window['product_selected'].update('')
            # window['print'].update(disabled=False)
            window['stock'].update(disabled=True, button_color=('black', 'grey'))
            window['print'].update(disabled=True, button_color=('black', 'grey'))
            window['weight'].update(f'{0 / 1000:.3f} KG')
        time.sleep(0.1)
        try:
            state = get_uppercase_state()
        except:
            state = 'off'
        if state == 'off':
            force_uppercase(True)
    window.close()
quit()
