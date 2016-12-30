import config
import send_email
import netifaces

"""
Get IP and send it to my e-mail, so that I can SSH in to the car
"""
msg = ''
interfaces = netifaces.interfaces()
for i in interfaces:
    if i == 'lo':
        continue
    iface = netifaces.ifaddresses(i).get(netifaces.AF_INET)
    if iface != None:
        for j in iface:
            msg += ', {0}'.format(j['addr'])

send_email.send_email(to_user=config.master_email, SUBJECT='IP on startup',
                      TEXT='IP: {0}'.format(msg))
