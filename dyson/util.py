"""
   Copyright 2020 InfAI (CC SES)

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""


__all__ = ('LockingDict', 'unpad', 'decrypt_password')


from Crypto.Cipher import AES
import threading, collections.abc, json, base64


def unpad(string):
    """
    From: https://github.com/CharlesBlonde/libpurecoollink

    Copyright 2017 Charles Blonde

    Licensed under the Apache License

    Un pad string."""
    return string[:-ord(string[len(string) - 1:])]


def decrypt_password(encrypted_password):
    """
    From: https://github.com/CharlesBlonde/libpurecoollink

    Copyright 2017 Charles Blonde

    Licensed under the Apache License

    Decrypt password.
    :param encrypted_password: Encrypted password
    """
    key = b'\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\x0c\r\x0e\x0f\x10' \
          b'\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1b\x1c\x1d\x1e\x1f '
    init_vector = b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' \
                  b'\x00\x00\x00\x00'
    cipher = AES.new(key, AES.MODE_CBC, init_vector)
    json_password = json.loads(unpad(cipher.decrypt(base64.b64decode(encrypted_password)).decode('utf-8')))
    return json_password["apPasswordHash"]


class LockingDict(dict):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__lock = threading.Lock()

    def __getitem__(self, item):
        with self.__lock:
            return super().__getitem__(item)

    def __setitem__(self, key, value):
        with self.__lock:
            super().__setitem__(key, value)

    def __delitem__(self, key):
        with self.__lock:
            super().__delitem__(key)

    def __contains__(self, item):
        with self.__lock:
            return super().__contains__(item)

    def __eq__(self, other):
        with self.__lock:
            return super().__eq__(other)

    def __len__(self):
        with self.__lock:
            return super().__len__()

    def items(self) -> collections.abc.ItemsView:
        with self.__lock:
            return super().items()

    def keys(self) -> collections.abc.KeysView:
        with self.__lock:
            return super().keys()

    def values(self) -> collections.abc.ValuesView:
        with self.__lock:
            return super().values()

    def copy(self) -> dict:
        with self.__lock:
            return super().copy()

    def clear(self):
        with self.__lock:
            super().clear()

    def get(self, key):
        with self.__lock:
            return super().get(key)

    def pop(self, key):
        with self.__lock:
            return super().pop(key)

    def popitem(self) -> tuple:
        with self.__lock:
            return super().popitem()

    def setdefault(self, key, default=...):
        print(123)
        with self.__lock:
            return super().setdefault(key, default)

    def update(self, __m, **kwargs) -> None:
        with self.__lock:
            super().update(__m, **kwargs)
