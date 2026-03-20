import socket
import ipaddress

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip

def is_ipv4(ip_str):
    try:
        return type(ipaddress.ip_address(ip_str)) is ipaddress.IPv4Address
    except ValueError:
        return False