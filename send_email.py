# coding=utf-8
import smtplib
import traceback
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from smtplib import SMTPDataError, SMTPSenderRefused

from email.MIMEImage import MIMEImage

import config


class EmailHandler(object):
    def __init__(self, to=[config.master_email], subject='Raspi Startup IP',
                 use_header_text=False, from_=config.master_email, tpe='html',
                 user=config.gmail_user, pwd=config.gmail_pwd):
        self.subject = subject
        self.tpe = tpe
        self.user = user
        self.pwd = pwd
        self.saved_csv_loc = []
        self.strFrom = from_
        self.use_header_text = use_header_text
        self.header_text = '<a name ="top">'
        self.email_text = ''
        if type(to) != list:
            self.to = [to]  # must be a list
        else:
            self.to = to
        self._set_up_email_fields()

    def _set_up_email_fields(self):
        """
        Email setup
        :return:
        """
        self.strTo = self.to
        self.msgRoot = MIMEMultipart()
        self.msgRoot['Subject'] = self.subject
        self.msgRoot['From'] = self.strFrom
        # self.msgRoot['To'] = ",".join(str(v) for v in self.strTo)
        self.msgAlternative = MIMEMultipart('mixed')
        self.msgRoot.attach(self.msgAlternative)
        self.msgText = MIMEText('')
        self.msgAlternative.attach(self.msgText)

    def update_subject(self, subjectline):
        self.subject = subjectline
        self.msgRoot['Subject'] = self.subject

    def add_attachment(self, csv_loc, add_to_message=False):

        """
        Provide a full route/directory of a csv/excel file you have saved
        :param csv_loc: location of file
        :return: None
        """
        self.saved_csv_loc.append(csv_loc)
        part = MIMEBase('application', "octet-stream")
        part.set_payload(open(csv_loc, "rb").read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', 'attachment; filename="%s"' % (csv_loc.split('/')[-1]))
        self.msgAlternative.attach(part)
        if add_to_message:
            # Not working
            self.email_text += '<br><img src="cid:%s"><br>' % csv_loc.split('/')[-1]

    def add_plot_text(self, url_split, scale=1, breaks=True, return_text=False):
        """
        This will add an image of a plot with a clickable link to your email
        Need to give it url_split, which is returned via a call like below:
        url = df[['Daily Pct', col_title]].iplot(sharing='secret',
                                                 filename='%s %s %s' % (
                                                     'charge_off', self.locale, datetime.date.today()),
                                                 yTitle=y_title, xTitle=x_title, title=title)
        url_split = config.plotly_retries(url.resource)
        :param url_split:
        :param scale: Scale the image up or down
        :param breaks: Add breaks after the image
        :return:
        """
        url = url_split[0] + '.embed?' + url_split[1]
        url_img = url_split[0] + '.png?' + url_split[1] + '&scale=%s' % scale
        txt = '<center><a href=%s><img src="%s"></a></center>' % (url, url_img)
        if return_text:
            return txt
        else:
            self.email_text += txt
        if breaks:
            self.email_text += '<br><br>'

    def add_random_text(self, text, center=False):
        """
        Literally just add any text you want into the email
        :param text:
        :param center:
        :return:
        """
        if center:
            text = "<center>" + text + "</center>"
        self.email_text += text

    def add_image(self, image_loc):
        ### Not working
        # We reference the image in the IMG SRC attribute by the ID we give it below
        msgText = MIMEText('<center><br><img src="cid:%s"></center><br>' % image_loc)
        self.msgAlternative.attach(msgText)
        # This example assumes the image is in the current directory
        fp = open(image_loc, 'rb')
        msgImage = MIMEImage(fp.read())
        fp.close()
        # Define the image's ID as referenced above
        msgImage.add_header('Content-ID', '<image1>')
        # msgRoot.attach(msgImage)
        # self.email_text += '<center><img src="%s" /></center>' % image_loc

    def send_email(self):
        """
        # Send the email (this example assumes SMTP authentication is required)
        :return:
        """
        msgText = MIMEText(self.header_text + self.email_text, self.tpe, 'utf-8')
        self.msgAlternative.attach(msgText)
        try:
            server = self._internal_send()
        except (SMTPDataError, SMTPSenderRefused):
            print traceback.format_exc()
            print self.saved_csv_loc
            send_email(SUBJECT='File too large -- %s' % self.subject, TEXT=traceback.format_exc())
            # File is too large, add it to Dropbox
            self.msgRoot = MIMEMultipart('related')
            self.msgRoot['Subject'] = self.subject
            self.msgRoot['From'] = self.strFrom
            # self.msgRoot['To'] = ",".join(str(v) for v in self.strTo)
            self.msgAlternative = MIMEMultipart('alternative')
            self.msgRoot.attach(self.msgAlternative)
            self.msgAlternative.attach(self.msgText)
            self.email_text += '<br><b>File too large to attach to email</b><br>'
            for ix in self.saved_csv_loc:
                self.add_dropbox_attachment(ix, dropbox_loc='%s%s' % (config.random_dbox_folder, ix.split('/')[-1]))
            msgText = MIMEText(self.header_text + self.email_text, self.tpe, 'utf-8')
            self.msgAlternative.attach(msgText)
            server = self._internal_send()
        server.quit()

    def _internal_send(self):
        server = smtplib.SMTP("smtp.gmail.com", 587)  # or port 465 doesn't seem to work!
        server.ehlo()
        server.starttls()
        server.login(self.user, self.pwd)
        server.sendmail(self.strFrom, self.strTo, self.msgRoot.as_string())
        return server


def send_email(to_user=[config.master_email], SUBJECT="IP for Raspi",
               TEXT="Default Text, If this is here there is an error", csv_loc=None,
               filename=None, type_='html', dropbox_loc=None):
    """
    Wrapper for EmailHandler to send a quick email with one function call
    :param to_user:
    :param SUBJECT:
    :param TEXT:
    :param csv_loc:
    :param filename:
    :param type_:
    :return:
    """
    gmail_user = config.gmail_user
    gmail_pwd = config.gmail_pwd
    FROM = config.gmail_user
    eh = EmailHandler(to=to_user, subject=SUBJECT, tpe=type_, from_=FROM,
                      user=gmail_user, pwd=gmail_pwd)
    eh.add_random_text(TEXT)
    if csv_loc is not None:
        eh.add_attachment(csv_loc)
    eh.send_email()
    print 'successfully sent the mail to ', to_user


__author__ = "Chase Schwalbach"
__credits__ = ["Chase Schwalbach"]
__version__ = "1.0"
__maintainer__ = "Chase Schwalbach"
__email__ = "schwallie@gmail.com"
__status__ = "Production"
