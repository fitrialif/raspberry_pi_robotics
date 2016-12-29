import config
import send_email
import netifaces

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
