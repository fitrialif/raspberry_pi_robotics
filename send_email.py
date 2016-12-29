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
        self.go_back_to_top = '<center><br><a href="#top">Go Back to top</a></center><br><br>'
        self.add_chart_disclaimer = '<br> <small>(Click the chart to view details and an interactive version)</small><br>'
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

    def add_header(self, name, description):
        """
        Adds a line item to create an index
        :param name:
        :param description:
        :return:
        """
        full_txt = "<li><a href='#%s'>%s</a></li>" % (name, description)
        if self.use_header_text:
            self.header_text += full_txt
        else:
            self.email_text += full_txt

    def add_dropbox_attachment(self, read_loc, dropbox_loc, overwrite=False, remove=False):
        """
        Adds a link to a dropbox attachment. Links not always working, but path is correct. Have to look
        more into it.
        Path:
        http://www.dropbox.com/home/Avant-Finance/Automation/Cash%20Reconciliations/US/ACH/ACH%20Reconciliation%202016-02-23%20(1).xlsx
        Needs to be turned into:
        https://www.dropbox.com/home/Avant-Finance/Automation/Cash%20Reconciliations/US/ACH?preview=ACH+Reconciliation+2015-01-02+(1).xlsx#
        :param read_loc: where to read your dataframe
        :param dropbox_loc: where to put the file
        :param overwrite: overwrite files with name
        :param remove: remove old file
        :return:
        """
        response = config.put_dropbox(read_loc, dropbox_loc, overwrite=overwrite, remove=remove)
        # Have to edit the path response to match the correct path convention:
        path = response['path']
        path_split = path.split('/')
        end_path = path_split[-1].replace('%20', '+')
        end_path = '?preview=%s' % end_path
        begin_path = '/'.join(str(e) for e in path_split[:-1])
        path = '%s%s' % (begin_path, end_path)
        self.email_text += '<br><a href="http://www.dropbox.com/home%s"> Download %s on Dropbox </a><br>' % (
            path, dropbox_loc.split('/')[-1])

    def add_df_to_google_sheets(self, df, wkb_name, wks_name, include_index=True, include_cols=True,
                                include_link_in_email=True):
        """
        Add your DataFrame to Google Sheets, and optionally add that link to the email
        :param df: dataFrame to write
        :param wkb_name: the workbook name (must share with email in secret.py first)
        :param wks_name: worksheet name in workbook
        :param include_index: bool, write index in the sheet
        :param include_cols: bool, write column names in the sheet
        :return:
        """
        link = config.df_to_google_doc(df, workbook_name=wkb_name, wks_name=wks_name, include_index=include_index,
                                       include_col_names=include_cols,
                                       return_link=include_link_in_email)
        if include_link_in_email:
            self.email_text += '<br><a href="{}"> Data is saved on Google Docs. Click to view </a><br>'.format(link)

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

    def add_closing_text_hr(self):
        """
        If you have "sections," this will add
        a Horizontal Rule and some breaklines
        :return:
        """
        self.email_text += '<br><hr><br><br><br>'

    def add_section_header(self, a_name=None, title=None, chart=True):
        """
        Add a section header to the document
        a_name is for building an index at the top
        that points to this header
        :param a_name: building an index at the top
                        that points to this header
        :param title: Header to be displayed
        :param chart: Bool. We have a chart disclaimer saying to click on them
                    if you have plots, you can make this True
        :return:
        """
        if self.use_header_text:
            self.add_header(a_name, title)
        if chart:
            self.email_text += '<center><a name="%s"></a><h2>%s</h2>%s %s</center>' % (
                a_name, title, self.add_chart_disclaimer, self.go_back_to_top)
        else:
            self.email_text += '<center><a name="%s"></a><h2>%s</h2>%s</center>' % (a_name, title, self.go_back_to_top)

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

    def add_two_plots(self, url_splits=[], scale=.5):
        """
        Mimics add_plot_text, except it does more than one plot
        Can do 2+
        TODO: Need to collapse these two methods into one
        and need to rename to add_x_plots
        :param url_splits:
        :param scale:
        :return:
        """
        self.email_text += '<center>'
        text = ''
        for url_split in url_splits:
            text += '<a href=%s><img src="%s"></a>' % (
                url_split[0] + '.embed?' + url_split[1], url_split[0] + '.png?' + url_split[1] + '&scale=%s' % scale)
        self.email_text += text
        self.email_text += '</center><br><br>'

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

    def html_table_formatting(self, html):
        """
        This takes a pandas DataFrame output (df.to_html()) and styles it
        Usage: self.email_handler = send_email.EmailHandler()
        self.email_handler.html_table_formatting(df.to_html())
        :param html:
        :return:
        """
        html = html.replace('<table border="1" class="dataframe">',
                            '<center><table border="1" style="border-collapse: collapse;padding: 3px 7px 2px 7px;">')
        html = html.replace('<tr style="text-align: left;">',
                            '<tr style="text-align: center; background-color:#25333f; color: #ffffff;">')
        html = html.replace('<tr style="text-align: right;">',
                            '<tr style="text-align: center; background-color:#25333f; color: #ffffff;">')
        html = html.replace('<th>', '<th style="text-align: left;">')
        html = html.replace('Total', '<b>Total &nbsp;&nbsp;</b>')
        html = html.replace('&lt;=48 Month Term', '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&lt;=48 Month Term')
        html = html.replace('&gt;48 Month Term', '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&gt;48 Month Term')
        return html

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
