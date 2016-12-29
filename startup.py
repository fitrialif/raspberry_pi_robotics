import socket

import config
import send_email

ip = socket.gethostbyname(socket.gethostname())
hostname = socket.gethostname()

send_email.send_email(to_user=config.master_email, SUBJECT='IP on startup',
                      TEXT='IP: {0}, Hostname: {1}'.format(ip, hostname))
