import dbf
from datetime import datetime


class DataBaseController(object):

    def __init__(self, filename=None):
        self.filename = filename
        self.mode = dbf.READ_ONLY
        self.table = None
        self.is_connected = None
        self.record = None

    def connect(self, filename=None, total_permission=False):
        if total_permission:
            self.mode = dbf.READ_WRITE
        if filename:
            self.filename = filename
        with dbf.Table(self.filename, codepage='cp1250') as self.table:
            if self.table:
                self.is_connected = True
        return self.table.open(mode=self.mode)

    def get_record(self, data):
        rec = False
        for _idx, item in enumerate(self.record):
            field_name = self.table.field_names[_idx].strip()
            with self.record as rec:
                if 'date' in str(self.table.field_info(field_name)[3]) and data[field_name]:
                    data[field_name] = datetime.strptime(data[field_name].replace('-', ''),
                                                         "%Y%m%d").date()
                rec[field_name] = data[field_name]
        return rec

    def filter_apply(self, field, _id, data):
        result = False
        for index, record in enumerate(self.table):
            if int(_id) == self.table[index][field]:
                self.record = record
                result = self.get_record(data)
        return result

    def get_index_by_id(self, _id):
        result = False
        for index, record in enumerate(self.table):
            if int(_id) == self.table[index]['PRONCOD']:
                result = index
        return result

    def create(self, query):
        last_id = len(self.table) - 1
        try:
            for datum in query:
                datum['PRONCOD'] = self.table[last_id]['PRONCOD'] + 1
                self.table.append(datum)
            result = {'result': True, 'object': self.table, 'message': 'Registro criado com sucesso!!!'}
        except Exception as e:
            result = {'result': False, 'object': [e], 'message': 'Erro ao criar registro.'}

        return result

    def update(self, filter_name, query, extra_fields=None):
        result_list = []
        if extra_fields:
            self.table.add_fields(extra_fields)
        for code in query:
            proncod = code[filter_name]
            if self.filter_apply(filter_name, proncod, code):
                result = {'result': True, 'object': self.table, 'message': 'Item atualizado com sucesso!!!'}
            else:
                result = {'result': False, 'object': [], 'message': 'O objeto informado não existe!!!'}
            result_list.append(result)
        return result_list

    def delete(self, _id, _idx=None):
        result = {'result': False, 'object': [], 'message': 'O objeto informado não existe!!!'}
        if not _idx:
            _idx = self.get_index_by_id(_id)
        if _idx and len(self.table) > _idx:
            rec = self.table[_idx]
            dbf.delete(rec)
            self.table.pack()
            result = {'result': True, 'object': rec, 'message': 'Item deletado com sucesso!!!'}
        return result

    def get_items(self, name=None, startwith=None):
        data = []
        for record in self.table:
            self.record = record
            if name and name.upper() == str(self.record[1]).strip():
                data.append(self.get_data())
            elif startwith and str(self.record[1]).strip().startswith(startwith.upper()):
                data.append(self.get_data())
            elif not name and not startwith:
                data.append(self.get_data())
        return data

    def get_data(self):
        dict_items = {}
        for index, item in enumerate(self.record):
            dict_items[self.table.field_names[index]] = str(item).strip()
        return dict_items

    def close_connection(self):
        self.table.close()
        self.is_connected = False
