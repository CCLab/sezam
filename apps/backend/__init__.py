#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Classes used all accross the modules in the project.
"""
import re
import os
import sys
import csv
import email
import codecs
import base64
import imaplib
import cStringIO
import mimetypes
from datetime import datetime

from django.db import models
from django.utils.timezone import utc
from django.core.mail import mail_managers
from django.utils.translation import ugettext as _

from apps.backend.html2text import html2text

"""
CountryField
"""
COUNTRIES = (
    ('000', ''),
    ('AFG', _('Afghanistan')),
    ('ALA', _('Aland Islands')),
    ('ALB', _('Albania')),
    ('DZA', _('Algeria')),
    ('ASM', _('American Samoa')),
    ('AND', _('Andorra')),
    ('AGO', _('Angola')),
    ('AIA', _('Anguilla')),
    ('ATG', _('Antigua and Barbuda')),
    ('ARG', _('Argentina')),
    ('ARM', _('Armenia')),
    ('ABW', _('Aruba')),
    ('AUS', _('Australia')),
    ('AUT', _('Austria')),
    ('AZE', _('Azerbaijan')),
    ('BHS', _('Bahamas')),
    ('BHR', _('Bahrain')),
    ('BGD', _('Bangladesh')),
    ('BRB', _('Barbados')),
    ('BLR', _('Belarus')),
    ('BEL', _('Belgium')),
    ('BLZ', _('Belize')),
    ('BEN', _('Benin')),
    ('BMU', _('Bermuda')),
    ('BTN', _('Bhutan')),
    ('BOL', _('Bolivia')),
    ('BIH', _('Bosnia and Herzegovina')),
    ('BWA', _('Botswana')),
    ('BRA', _('Brazil')),
    ('VGB', _('British Virgin Islands')),
    ('BRN', _('Brunei Darussalam')),
    ('BGR', _('Bulgaria')),
    ('BFA', _('Burkina Faso')),
    ('BDI', _('Burundi')),
    ('KHM', _('Cambodia')),
    ('CMR', _('Cameroon')),
    ('CAN', _('Canada')),
    ('CPV', _('Cape Verde')),
    ('CYM', _('Cayman Islands')),
    ('CAF', _('Central African Republic')),
    ('TCD', _('Chad')),
    ('CIL', _('Channel Islands')),
    ('CHL', _('Chile')),
    ('CHN', _('China')),
    ('HKG', _('China - Hong Kong')),
    ('MAC', _('China - Macao')),
    ('COL', _('Colombia')),
    ('COM', _('Comoros')),
    ('COG', _('Congo')),
    ('COK', _('Cook Islands')),
    ('CRI', _('Costa Rica')),
    ('CIV', _('Cote d\'Ivoire')),
    ('HRV', _('Croatia')),
    ('CUB', _('Cuba')),
    ('CYP', _('Cyprus')),
    ('CZE', _('Czech Republic')),
    ('PRK', _('Democratic People\'s Republic of Korea')),
    ('COD', _('Democratic Republic of the Congo')),
    ('DNK', _('Denmark')),
    ('DJI', _('Djibouti')),
    ('DMA', _('Dominica')),
    ('DOM', _('Dominican Republic')),
    ('ECU', _('Ecuador')),
    ('EGY', _('Egypt')),
    ('SLV', _('El Salvador')),
    ('GNQ', _('Equatorial Guinea')),
    ('ERI', _('Eritrea')),
    ('EST', _('Estonia')),
    ('ETH', _('Ethiopia')),
    ('FRO', _('Faeroe Islands')),
    ('FLK', _('Falkland Islands (Malvinas)')),
    ('FJI', _('Fiji')),
    ('FIN', _('Finland')),
    ('FRA', _('France')),
    ('GUF', _('French Guiana')),
    ('PYF', _('French Polynesia')),
    ('GAB', _('Gabon')),
    ('GMB', _('Gambia')),
    ('GEO', _('Georgia')),
    ('DEU', _('Germany')),
    ('GHA', _('Ghana')),
    ('GIB', _('Gibraltar')),
    ('GRC', _('Greece')),
    ('GRL', _('Greenland')),
    ('GRD', _('Grenada')),
    ('GLP', _('Guadeloupe')),
    ('GUM', _('Guam')),
    ('GTM', _('Guatemala')),
    ('GGY', _('Guernsey')),
    ('GIN', _('Guinea')),
    ('GNB', _('Guinea-Bissau')),
    ('GUY', _('Guyana')),
    ('HTI', _('Haiti')),
    ('VAT', _('Holy See (Vatican City)')),
    ('HND', _('Honduras')),
    ('HUN', _('Hungary')),
    ('ISL', _('Iceland')),
    ('IND', _('India')),
    ('IDN', _('Indonesia')),
    ('IRN', _('Iran')),
    ('IRQ', _('Iraq')),
    ('IRL', _('Ireland')),
    ('IMN', _('Isle of Man')),
    ('ISR', _('Israel')),
    ('ITA', _('Italy')),
    ('JAM', _('Jamaica')),
    ('JPN', _('Japan')),
    ('JEY', _('Jersey')),
    ('JOR', _('Jordan')),
    ('KAZ', _('Kazakhstan')),
    ('KEN', _('Kenya')),
    ('KIR', _('Kiribati')),
    ('KWT', _('Kuwait')),
    ('KGZ', _('Kyrgyzstan')),
    ('LAO', _('Lao People\'s Democratic Republic')),
    ('LVA', _('Latvia')),
    ('LBN', _('Lebanon')),
    ('LSO', _('Lesotho')),
    ('LBR', _('Liberia')),
    ('LBY', _('Libyan Arab Jamahiriya')),
    ('LIE', _('Liechtenstein')),
    ('LTU', _('Lithuania')),
    ('LUX', _('Luxembourg')),
    ('MKD', _('Macedonia')),
    ('MDG', _('Madagascar')),
    ('MWI', _('Malawi')),
    ('MYS', _('Malaysia')),
    ('MDV', _('Maldives')),
    ('MLI', _('Mali')),
    ('MLT', _('Malta')),
    ('MHL', _('Marshall Islands')),
    ('MTQ', _('Martinique')),
    ('MRT', _('Mauritania')),
    ('MUS', _('Mauritius')),
    ('MYT', _('Mayotte')),
    ('MEX', _('Mexico')),
    ('FSM', _('Micronesia, Federated States of')),
    ('MCO', _('Monaco')),
    ('MNG', _('Mongolia')),
    ('MNE', _('Montenegro')),
    ('MSR', _('Montserrat')),
    ('MAR', _('Morocco')),
    ('MOZ', _('Mozambique')),
    ('MMR', _('Myanmar')),
    ('NAM', _('Namibia')),
    ('NRU', _('Nauru')),
    ('NPL', _('Nepal')),
    ('NLD', _('Netherlands')),
    ('ANT', _('Netherlands Antilles')),
    ('NCL', _('New Caledonia')),
    ('NZL', _('New Zealand')),
    ('NIC', _('Nicaragua')),
    ('NER', _('Niger')),
    ('NGA', _('Nigeria')),
    ('NIU', _('Niue')),
    ('NFK', _('Norfolk Island')),
    ('MNP', _('Northern Mariana Islands')),
    ('NOR', _('Norway')),
    ('OMN', _('Oman')),
    ('PAK', _('Pakistan')),
    ('PLW', _('Palau')),
    ('PAN', _('Panama')),
    ('PNG', _('Papua New Guinea')),
    ('PRY', _('Paraguay')),
    ('PER', _('Peru')),
    ('PHL', _('Philippines')),
    ('PCN', _('Pitcairn')),
    ('POL', _('Poland')),
    ('PRT', _('Portugal')),
    ('PRI', _('Puerto Rico')),
    ('QAT', _('Qatar')),
    ('KOR', _('Republic of Korea')),
    ('MDA', _('Republic of Moldova')),
    ('REU', _('Reunion')),
    ('ROU', _('Romania')),
    ('RUS', _('Russian Federation')),
    ('RWA', _('Rwanda')),
    ('BLM', _('Saint-Barthelemy')),
    ('SHN', _('Saint Helena')),
    ('KNA', _('Saint Kitts and Nevis')),
    ('LCA', _('Saint Lucia')),
    ('MAF', _('Saint-Martin (French part)')),
    ('SPM', _('Saint Pierre and Miquelon')),
    ('VCT', _('Saint Vincent and the Grenadines')),
    ('WSM', _('Samoa')),
    ('SMR', _('San Marino')),
    ('STP', _('Sao Tome and Principe')),
    ('SAU', _('Saudi Arabia')),
    ('SEN', _('Senegal')),
    ('SRB', _('Serbia')),
    ('SYC', _('Seychelles')),
    ('SLE', _('Sierra Leone')),
    ('SGP', _('Singapore')),
    ('SVK', _('Slovakia')),
    ('SVN', _('Slovenia')),
    ('SLB', _('Solomon Islands')),
    ('SOM', _('Somalia')),
    ('ZAF', _('South Africa')),
    ('ESP', _('Spain')),
    ('LKA', _('Sri Lanka')),
    ('PSE', _('State of Palestine')),
    ('SDN', _('Sudan')),
    ('SUR', _('Suriname')),
    ('SJM', _('Svalbard and Jan Mayen Islands')),
    ('SWZ', _('Swaziland')),
    ('SWE', _('Sweden')),
    ('CHE', _('Switzerland')),
    ('SYR', _('Syrian Arab Republic')),
    ('TJK', _('Tajikistan')),
    ('THA', _('Thailand')),
    ('TLS', _('Timor-Leste')),
    ('TGO', _('Togo')),
    ('TKL', _('Tokelau')),
    ('TON', _('Tonga')),
    ('TTO', _('Trinidad and Tobago')),
    ('TUN', _('Tunisia')),
    ('TUR', _('Turkey')),
    ('TKM', _('Turkmenistan')),
    ('TCA', _('Turks and Caicos Islands')),
    ('TUV', _('Tuvalu')),
    ('UGA', _('Uganda')),
    ('UKR', _('Ukraine')),
    ('ARE', _('United Arab Emirates')),
    ('GBR', _('United Kingdom')),
    ('TZA', _('United Republic of Tanzania')),
    ('USA', _('United States of America')),
    ('VIR', _('United States Virgin Islands')),
    ('URY', _('Uruguay')),
    ('UZB', _('Uzbekistan')),
    ('VUT', _('Vanuatu')),
    ('VEN', _('Venezuela (Bolivarian Republic of)')),
    ('VNM', _('Viet Nam')),
    ('WLF', _('Wallis and Futuna Islands')),
    ('ESH', _('Western Sahara')),
    ('YEM', _('Yemen')),
    ('ZMB', _('Zambia')),
    ('ZWE', _('Zimbabwe')),
    )

class CountryField(models.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 3)
        kwargs.setdefault('choices', COUNTRIES)
        
        super(CountryField, self).__init__(*args, **kwargs)
    
    def get_internal_type(self):
        return "CharField"

"""
CountryField - end
"""



"""
MailImporter
"""
class MailImporter():
    """
    `attachment_dir` is the main directory where to save attachments. 
    `addr_template` is to create subdirectories in the `attachment_dir`.
    """
    def __init__(self, connection_opts, **kwargs):
        self.connection_opts= connection_opts
        self.attachment_dir= kwargs.get('attachment_dir', '.')
        self.addr_template= kwargs.get('addr_template', None)
        self.content_related= ['content-type', 'content-transfer-encoding', 'content-id', 'content-disposition']
        self.messages= []

    def imap_connect(self):
        """
        Establish imap connection.
        """
        host= self.connection_opts['host']
        port= self.connection_opts['port']
        login= self.connection_opts['login']
        password= self.connection_opts['password']

        if self.connection_opts['use_ssl']:
            connection= imaplib.IMAP4_SSL(host, port)
        else:
            connection= imaplib.IMAP4(host, port)

        connection.login(login, password)
        return connection

    def process_mails(self, connection, header_only=False):
        """
        Loop over unread emails, if callback call succeed,
        mark email as read.
        """
        def _get_message_dirname(to):
            """
            Extract from `to` field what is defined by `addr_template`
            """
            try:
                field_to= [t.strip() for t in to.split(',') if re.search(self.addr_template, t)][0]
            except:
                return ''
            return field_to.split('@')[0].replace('.', '_')
        
        connection.select()
        _u, data= connection.search(None, 'UNSEEN')

        for msg_num in data[0].split():
            header= None
            try:
                _u, msg_data= connection.fetch(msg_num, '(RFC822)')
                header= self.extract_mail_header(msg_data)
            except Exception as e:
                exception= sys.exc_info()[1]
                connection.store(msg_num, '-FLAGS', '\SEEN')
                print >> sys.stderr, '[%s] %s' % (datetime.now().isoformat(), exception)
                mail_managers(
                    str(self.__class__),
                    '[%s] %s' % (datetime.now().isoformat(), exception),
                    fail_silently=True)
            if header:
                content, attachments, dir_name= None, None, ''
                if self.addr_template:
                    if not re.search(self.addr_template, header['to']):
                        # Very important! If `addr_template` is given,
                        # then at this stage (reading mails), mail filtering
                        # happens: only those e-mails are being processed,
                        # whose `to` field satisfy the template's pattern.
                        # Otherwise - ignore the message.
                        continue
                if not header_only:
                    dir_name= _get_message_dirname(header['to']) + '/'
                    content, attachments= self.extract_mail_content(msg_data,
                        dir_name=dir_name)
                self.messages.append({'header': header, 'content': content,
                                      'attachments': attachments})
        return self.messages

    def extract_mail_header(self, message_data):
        """
        Returns message header.
        """
        messageHeader= {}
        for response_part in message_data:
            if isinstance(response_part, tuple):
                msg= email.message_from_string(response_part[1])
                for part in msg.walk():
                    for k, v in part.items():
                        if k.lower() not in self.content_related:
                            messageHeader.update({k.lower().strip(): self._clean_text_encoded(v)})
        return messageHeader

    def extract_mail_content(self, message_data, **kwargs):
        """
        Returns text message content.
        """
        msg_plain_text, msg_attachments= '', []
        for response_part in message_data:
            if isinstance(response_part, tuple):
                msg= email.message_from_string(response_part[1])
                for part in msg.walk():
                    if part.is_multipart():
                        continue
                    attachment_part= part.get_params(None, 'Content-Disposition')
                    if attachment_part:
                        attachment_size= len(part.get_payload(decode=True))
                        attachment_name= self._process_attachment(part, **kwargs)
                        if attachment_name:
                            msg_attachments.append({'filename': attachment_name,
                                                    'filesize': attachment_size})
                    else:
                        # Process message text.
                        # Update `msg_plain_text` only if it isn't updated yet.
                        if len(msg_plain_text) == 0:
                            if str(part.get_content_type()) == 'text/plain':
                                msg_plain_text= unicode(part.get_payload(decode=True),
                                                        part.get_content_charset(), 'ignore').encode('utf8','replace')
                            elif str(part.get_content_type()) == 'text/html':
                                msg_plain_text= unicode(html2text(part.get_payload(decode=True)),
                                                        part.get_content_charset(), 'ignore').encode('utf8','replace')
        return msg_plain_text, msg_attachments

    def _process_attachment(self, part, **kwargs):
        """
        Processes the Content-Disposition part of the current message.
        """
        dir_name= kwargs.get('dir_name', '')
        now= datetime.strftime(datetime.utcnow().replace(
            tzinfo=utc), '%d-%m-%Y_%H-%M')
        ext= mimetypes.guess_extension(part.get_content_type())
        filename= self._clean_text_encoded(part.get_filename())
        if not filename:
            if not ext: # Use a generic bag-of-bits extension.
                ext= '.bin'
            filename= 'part_%s%s' % (now, ext)
        else:
            if ext not in filename:
                filename= '.'.join([filename, ext])
        message_dir= self.ensure_directory(self.attachment_dir + dir_name + now)
        fp= open(os.path.join(message_dir, filename), 'wb')
        try:
            fp.write(part.get_payload(decode=True))
            fp.close()

            # Returns not the full path, but only what was created.
            # The full path is not necessary, the access URL will be
            # constructed with use of MEDIA_ROOT
            return dir_name + now + '/' + filename
        except Exception as e:
            print >> sys.stderr, '[%s] %s' % (
                datetime.now().isoformat(),
                AppMessage('CantSaveAttachmnt').message % {'filename': filename, 'error': e})
            return None

    def _clean_text_encoded(self, input_text):
        """
        Cleaning and decoding input_text.
        """
        if re.search(r'=\?', input_text):
            encoding= None
            try:
                input_text, encoding= email.Header.decode_header(input_text)[0]
            except Exception as e:
                input_text= None
            if encoding:
                try:
                    input_text= input_text.decode(encoding)
                except:
                    input_text= None
        return input_text

    def ensure_directory(self, dir_name):
        """
        Create a subdirectory related to the specific message
        in the directory designated for attachments.
        """
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
        return dir_name
"""
MailImporter - end
"""



"""
APP_MESSAGES is a dictionary of all possible messages, with which
any project module send a message to any other module or to front-end:

message_code: {
    message: <message verbose text>,
    response: <response_code>, (optional)
    <any additional key, value pair if necessary>
    }
"""
APP_MESSAGES = {
    'MailboxNotFound': {
        'message': _(u'Mailbox with the specified name not found! Check MAILBOXES dict in the main project settings!')
        },
    'ResponseNotFound': {
        'message': _(u'Message with no proper recipient e-mail address! Possible spam? Please, check the inbox.')
        },
    'RequestNotFound': {
        'message': _(u'Cannot find in the database the Request with given ID!')
        },
    'NewMsgFailed': {
        'message': _(u'Cannot create new Message in the Thread for the Request with given ID!')
        },
    'AuthEmailNotFound': {
        'message': _(u'We do not have an e-mail of this authority in our database')
        },
    'UserEmailNotFound': {
        'message': _(u'Cannot find e-mail address of this user in our database')
        },
    'MailSendFailed': {
        'message': _(u'Sending e-mail message failed: %s')
        },
    'MsgCreateFailed': {
        'message': _(u'Creating e-mail message failed: %s')
        },
    'CantSaveAttachmnt': {
        'message': _(u'Cannot save attachment %(filename)s: %(error)s')
        },
    'CheckMailComplete': {
        'message': _(u'Email check complete, received %s messages')
        },
    'CheckOverdueComplete': {
        'message': _(u'Complete checking overdue requests. Total number of overdue requests: %s')
        },
    'ClassifyRespUser': {
        'message': _(u'The response from the Authority has not been classified yet. If you are satisfied or unsatisfied with the response, set the appropriate status, please.')
        },
    'ClassifyRespAnonim': {
        'message': _("We don't know whether the most recent response to this request contains information or not. If you are <a href=\"/user/%(user_id)s/\">%(user_name)s</a>, please sign in and let everyone know."),
        },
    'ClassifyRespAlien': {
        'message': _("We don't know whether the most recent response to this request contains information or not."),
        },
    'DraftCreateFailed': {
        'message': _("Failed to create a Reqiest draft. System error is: %s"),
        },
    'DraftDiscardFailed': {
        'message': _("Failed to discard a Reqiest draft. System error is: %s"),
        },
    'DraftRemoveFailed': {
        'message': _("Failed to remove a draft, while sending Request. System error is: %s"),
        },
    'DraftSaveFailed': {
        'message': _("Failed to save a Request draft, while sending PIA Request. System error is: %s"),
        },
    'AttachFailed': {
        'message': _(u'Cannot process attachment! See the original message!')
        },
    'AttachSaveFailed': {
        'message': _(u'Failed to save attachments: %s')
        },        
    'AttachTooBig': {
        'message': _(u'Attachment %(filename)s exceeds maximum filesize %(maxsize)s!'),
        },
    'NotificFailed': {
        'message': _(u'Error sending notification: %s')
        },        
    'AuthSavedInactive': {
        'message': _(u'Athority <strong>%s</strong> successfully saved in the db! <br/>It will remain inactive until our moderator finish reviewing and confirming the record. We will notify you upon this by email. <p>Thanks a lot for your participation!</p>'),
        },
    'AddDetailsToThread': {
        'message': _(u"<h5>Status was updated successfully.</h5><p>If you have any additional information concerning this request (for example, an answer sent via snail mail), and feel like adding something would help users to find the right answer to their requests in the future, please, use <a href=\"%(url)s\">this form</a>.<br/>Thank you!</p>"),
        },
    'ReportRequest': {
        'message': _(u"<strong>You are going to report this request as offensive or unsuitable!</strong><br>An email will be sent to the managers of %s.<p>Are you sure you want to proceed?</p>"),
        },
    'AuthorCantFollow': {
        'message': _(u'You cannot follow your own request. As its author you are getting all updates anyway.'),
        },
    'DisclaimerManualReply': {
        'message': _(u"Warning! This answer or additional information from %(auth)s was obtained without use of the service %(domain)s and entered manually by the user, who originally asked the question.\n-------------\n"),
        },
    }

class AppMessage():
    """
    Returns messages. Used for alerts, errors and log items.
    """
    def __init__(self, message_code=None, **kwargs):
        self.message_code= message_code
        self.kwargs= kwargs
        if message_code is None:
            self.message= ''
        try:
            self.message= APP_MESSAGES[message_code]['message']
        except KeyError:
            self.message= 'ERROR: Message with code `%s` not found!' % message_code

    def __unicode__(self):
        if self.kwargs:
            return '%s\n%s' % (self.message, self.kwargs)
        return self.message
"""
AppMessage - end
"""


"""
StretchHighlighter - a subclass of haystack's Highlighter to highlight
the the text before and after the search phrase.
"""
from haystack.utils import Highlighter

class StretchHighlighter(Highlighter):
    def render_html(self, highlight_locations=None, start_offset=None, end_offset=None):
        # Shifting offset to 50 max symbols "back", so that the
        # highlighted chunk would appear in the middle of the result.
        window= end_offset - start_offset
        shifted_by= 50
        if max(start_offset - shifted_by, 0) == 0:
            shifted_by= start_offset
        start_offset -= shifted_by
        end_offset -= shifted_by

        # If there is some highlight_location beyond the shifted window,
        # extend the window to the length of the longest word with the limit
        # of 1.33 of the original window.
        try:
            max_location= max([max(v) for k, v in highlight_locations.iteritems()])
            max_word_len= max([len(k) for k in highlight_locations.keys()])
            if end_offset < (max_location + max_word_len):
                end_offset= min(max_location + max_word_len,
                                start_offset + int(window * 1.33))
        except: pass

        highlighted_chunk= self.text_block[start_offset:end_offset]

        if self.css_class:
            _css_class= self.css_class
        else:
            _css_class= 'highlighted'

        # Creating `query_words` manually, because haystack applies .lower()
        # to each word, which makes .replace() impossible.
        _query_words= set([word for word in self.query.split() if not word.startswith('-')])

        # Highlight should be case insensitive!
        for word in _query_words:
            p= re.compile(word, re.IGNORECASE)
            found= p.findall(highlighted_chunk)
            if found:
                for w in set(found):
                    highlighted_chunk= highlighted_chunk.replace(w,
                        '<%(tag)s class="%(css)s">%(word)s</%(tag)s>' % {
                            'tag': self.html_tag, 'css':_css_class, 'word': w})
        if start_offset > 0:
            highlighted_chunk= '...' + highlighted_chunk
        if end_offset < len(self.text_block):
            highlighted_chunk += '...'

        return highlighted_chunk
"""
StretchHighlighter - end
"""


"""
UnicodeWriter
"""
class UnicodeWriter:
    """
    A CSV writer. Writes rows to CSV file `f` encoded in the given encoding.
    """
    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwargs):
        """
        Redirect output to a queue
        """
        self.queue= cStringIO.StringIO()
        self.writer= csv.writer(self.queue, dialect=dialect,
                                delimiter=';', **kwargs)
        self.stream= f
        self.encoder= codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])
        data= self.queue.getvalue() # Fetch UTF-8 output from the queue.
        data= data.decode("utf-8")
        data= self.encoder.encode(data) # Re-encode it into the target encoding.
        self.stream.write(data) # Write to the target stream
        self.queue.truncate(0) # Clean the queue.

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)
"""
UnicodeWriter - end.
"""
