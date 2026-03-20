import re
import random
import sqlite3
import bcrypt

def symbol_limit(s,pattern):
    if pattern == 'login':
        pattern = r'^[a-zA-Z0-9]+$'
        return re.fullmatch(pattern, s) is not None
    if pattern == 'password':
        return s.isascii()


def login_limit(login):
    if symbol_limit(login,'login') == False:
        return 'В логине используются запрещённые символы. Используйте только латинские буквы и цифры.'
    elif len(login) < 3:
        return 'Длина логина должна быть из 3 или более символов'
    else:
        return None

def login_exist(login):
    database_logins = sqlite3.connect('tables.db').cursor()
    database_logins.execute("SELECT login FROM Users WHERE login = ?", (login,))
    users_list = database_logins.fetchall()
    database_logins.close()
    return len(users_list) != 0

def password_limit(password):
    if password == '123456':
        return '123456... у меня даже слов нет... почитайте эту статью в свободное время - https://www.kaspersky.ru/resource-center/threats/how-to-create-a-strong-password'
    elif symbol_limit(password,'password') == False:
        return 'В пароле испольются запрещённые символы. Используйте латинские буквы, цифры и основные символы (ASCII)'
    elif len(password) < 6:
        random_message = random.randint(1, 5)
        if random_message == 1:
            return 'Этот пароль взломает даже ваша бабушка, угадав с трёх раз. Напишите что-то посложнее (минимум 6 символов)'
        return 'Пароль должен быть минимум из 6 символов'
    else:
        return None

def password_check(login, password):
    database = sqlite3.connect('tables.db').cursor()
    database.execute("SELECT password_hash FROM Users WHERE login = ?", (login,))
    check = database.fetchall()
    database.close()
    return (bcrypt.checkpw(password.encode(), check[0][0].encode()))

def get_username(login):
    database = sqlite3.connect('tables.db').cursor()
    database.execute("SELECT visible_name FROM Users WHERE login = ?", (login,))
    check = database.fetchall()
    database.close()
    return check[0][0]