import os
import json


class FDB:
    def __init__(self, fname, model):
        # Путь к файлу базы данных
        self.fname = fname

        # Модель базы данных
        model.update(
            {
                "id": {"length": 10},
            }
        )
        self.model = model

        # Фиксированная длина поля в байтах по умолчанию
        self.default_fixed_length = 255

        # Определить длину записи в байтах
        self.record_length = sum(
            [
                # длина ключа (название поля)
                len(str(key))
                # максимальная длина
                + value.get("length", self.default_fixed_length)
                + 4  # кавычки для ключей и значений
                + 2  # двоеточие и пробел после него
                + 2  # запятая и пробел после неё
                for key, value in self.model.items()
            ]
            + [
                -2,  # минус последняя запятая и пробел после неё
                +2,  # фигурные скобки
                +1,  # перевод строки
            ],
        )

        # Индексы
        self.index = {
            field: {}
            for field, params in self.model.items()
            if params.get("index", False)
        }

        # Если файл базы данных не существует, создать его
        if not os.path.exists(self.fname):
            open(self.fname, "w", encoding="utf-8").close()
        # Если файл базы данных существует, перестроить индексы
        else:
            self._rebuild_indexes()

    def _normalize_string_to_bytes(self, str, byte_limit):
        """Нормализует строку до нужной длины в байтах."""
        # Кодировать строку в UTF-8 и обрезать до нужной длины
        encoded_str = str.encode("utf-8")[:byte_limit]
        # Декодировать обратно в строку
        decoded_str = encoded_str.decode("utf-8", errors="ignore")
        # Добавить пробелами до нужной длины
        padding = " " * (byte_limit - len(decoded_str.encode("utf-8")))
        return decoded_str + padding

    def _serialize(self, obj_record):
        """Сериализует запись."""
        # Проверить, что все поля записи определены в модели
        for field, value in obj_record.items():
            if field not in self.model:
                raise ValueError(f"Field {field} is not defined in the model.")
        # Добавить недостающие поля из модели с пустыми значениями
        empty_template = dict.fromkeys(self.model, "")
        # Добавить значения по умолчанию
        template = {
            key: self.model[key].get("default", value)
            for key, value in empty_template.items()
        }
        template.update(obj_record)
        # Нормализировать значения полей записи
        result = {
            key: self._normalize_string_to_bytes(
                value, self.model[key].get("length", self.default_fixed_length)
            )
            for key, value in template.items()
        }
        # Сериализовать в JSON, добавить перевод строки и закодировать в UTF-8
        return (json.dumps(result, ensure_ascii=False) + "\n").encode("utf-8")

    def _deserialize(self, str_record):
        """Десериализует запись."""
        result = {key: value.strip() for key, value in json.loads(str_record).items()}
        return result

    def _get_words(self, value):
        """Разбивает строку на слова."""
        return str(value).lower().split()

    def _index_record(self, id, record):
        """Индексирует запись: добавляет слова в индекс."""
        for field, value in record.items():
            # Индексировать только те поля, которые указаны в модели
            if field in self.index:
                words = self._get_words(value)
                for word in words:
                    if word not in self.index[field]:
                        self.index[field][word] = []
                    self.index[field][word].append(id)

    def _remove_from_index(self, id, record):
        """Удаляет слова из индекса для указанной записи."""
        for field, value in record.items():
            # Удалить индексы только тех полей, которые указаны в модели
            if field in self.index:
                words = self._get_words(value)
                for word in words:
                    if word in self.index[field] and id in self.index[field][word]:
                        self.index[field][word].remove(id)
                        # Если список пуст, можно удалить саму запись из индекса
                        if not self.index[field][word]:
                            del self.index[field][word]

    def _rebuild_indexes(self):
        """Перестраивает индексы из файла."""
        # Очистить индексы
        self.index = {field: {} for field in self.index}
        # Перестроить индексы
        with open(self.fname, "rb") as file:
            for id in range(self._get_next_id()):
                file.seek(id * self.record_length)
                data = (
                    file.read(self.record_length)
                    .decode("utf-8", errors="ignore")
                    .strip()
                )
                if data:
                    record = self._deserialize(data)
                    self._index_record(id, record)

    def _get_next_id(self):
        """Возвращает следующий доступный ID."""
        with open(self.fname, "r", encoding="utf-8") as file:
            return sum(1 for _ in file)

    def set(self, obj_record):
        """Добавляет запись в конец файла."""
        id = self._get_next_id()
        obj_record["id"] = str(id)
        with open(self.fname, "ab") as file:
            file.write(self._serialize(obj_record))
        # Добавить запись в индекс
        self._index_record(id, obj_record)
        return id

    def get(self, id):
        """Читает запись по id."""
        with open(self.fname, "rb") as file:
            file.seek(id * self.record_length)
            data = (
                file.read(self.record_length).decode("utf-8", errors="ignore").strip()
            )
        return self._deserialize(data) if data else None

    def delete(self, id):
        """Удаляет запись по id, заполняя её пустой строкой."""
        record = self.get(id)
        if not record:
            raise ValueError(f"Record with ID {id} does not exist.")
        # Записать пустую строку (-1 - символ перевода стороки)
        empty_record = self._normalize_string_to_bytes("", self.record_length - 1)
        with open(self.fname, "rb+") as file:
            file.seek(id * self.record_length)
            file.write((empty_record + "\n").encode("utf-8"))
        # Удалить старые индексы для записи
        self._remove_from_index(id, record)

    def update(self, id, values):
        """Обновляет указанные поля записи по id."""
        if "id" in values:
            del values["id"]
        record = self.get(id)
        if not record:
            raise ValueError(f"Record with ID {id} does not exist.")
        # Удалить старые индексы для записи
        self._remove_from_index(id, record)
        # Обновить только указанные поля
        for field, value in values.items():
            if field not in self.model:
                raise ValueError(f"Field {field} is not defined in the model.")
            record[field] = value
        # Перезаписать обновлённую запись
        with open(self.fname, "rb+") as file:
            file.seek(id * self.record_length)
            file.write(self._serialize(record))
        # Добавить новые индексы для обновленной записи
        self._index_record(id, record)

    def all(self):
        """Возвращает все записи из базы данных."""
        all_records = []
        with open(self.fname, "rb") as file:
            for id in range(self._get_next_id()):
                file.seek(id * self.record_length)
                data = (
                    file.read(self.record_length)
                    .decode("utf-8", errors="ignore")
                    .strip()
                )
                if data:
                    record = self._deserialize(data)
                    all_records.append(record)
        return all_records

    def filter(self, field, query):
        """Возвращает отфильтрованный список записей."""
        if field not in self.index:
            raise ValueError(f"Field {field} is not indexed.")
        query_words = self._get_words(query)
        candidates = {}
        # Делать поиск по всем словам запроса
        for word in query_words:
            # Проверить наличие слова в индексе
            if word in self.index[field]:
                # Добавить id книги в кандидаты
                for id in self.index[field][word]:
                    if id not in candidates:
                        candidates[id] = 0
                    # Увеличить рейтинг для id книги
                    candidates[id] += 1
        # Сортировать результаты по рейтингу
        sorted_candidates = sorted(candidates.items(), key=lambda x: -x[1])
        # Получить записи по их id
        results = []
        for id, _ in sorted_candidates:
            record = self.get(id)
            if record:
                results.append(record)
        return results


if __name__ == "__main__":
    # Пример использования

    # Определить модель
    book_model = {
        "title": {"length": 100, "index": True},
        "author": {"length": 25, "index": True},
        "year": {"length": 4, "index": True},
        "status": {
            "length": 1,
            "default": "1",
        },
    }

    # Создать базу данных
    fdb = FDB("library.txt", book_model)

    # Добавить книги
    id_1 = fdb.set(
        {
            "title": "Приключения Тома Сойера",
            "author": "Марк Твен",
            "year": "1876",
            "status": "1",
        }
    )

    id_2 = fdb.set(
        {
            "title": "Adwentures of Tom Sawyer",
            "author": "Mark Twain",
            "year": "1876",
            "status": "1",
        }
    )

    id_3 = fdb.set(
        {
            "title": "Приключения Незнайки",
            "author": "Николай Носов",
            "year": "1953",
            "status": "1",
        }
    )

    print("Получить все книги:")
    for record in fdb.all():
        print(record)
    print("")

    print("Получить книгу по id:")
    print(fdb.get(id_1))
    print(fdb.get(2))
    print("")

    print("Найти книги по наименованию:")
    for record in fdb.filter("title", "Приключения Тома"):
        print(record)
    print("")

    print("Изменить книгу по id:")
    fdb.update(2, {"title": "Сказки"})
    print(fdb.get(2))
    fdb.update(0, {"status": "0"})
    print(fdb.get(0))
    print("")

    print("Удалить книгу по id:")
    print(fdb.get(1))
    try:
        fdb.delete(1)
        print(fdb.get(1))  # -> None
        fdb.delete(100)  # -> ValueError
    except Exception as e:
        print(e)
