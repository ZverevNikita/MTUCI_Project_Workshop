from fastapi import FastAPI
from pywebio.platform.fastapi import webio_routes
import uvicorn
from ip_identifier import *
from routes import router
from chat import main
import builtins

app = FastAPI()
app.include_router(router)
app.routes.extend(webio_routes(main))

def ip_choice():
    local_ip = get_local_ip()
    print(f'''Какой Ip использовать для хостинга?
1 - Локальный - {local_ip}
2 - Ввести вручную''')
    while True:
        choice = builtins.input()
        if choice == '1':
            return local_ip
        elif choice == '2':
            print('Введите Ip(Например: 1.2.3.4)')
            while True:
                ip_input = builtins.input()
                if is_ipv4(ip_input):
                    return ip_input
                else:
                    print('Неверный ввод')
        else:
            print('Неверный ввод')

if __name__ == "__main__":
    ip = ip_choice()
    uvicorn.run(app, host=ip, port=8080)