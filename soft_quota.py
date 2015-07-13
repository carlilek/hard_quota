#!/usr/bin/env python
# Copyright (c) 2013 Qumulo, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not
# use this file except in compliance with the License. You may obtain a copy of
# the License at http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations under
# the License.


# Import python libraries
import argparse
import os
import sys
import smtplib
from email.mime.text import MIMEText

# Import Qumulo REST libraries
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import qumulo.lib.auth
import qumulo.lib.opts
import qumulo.lib.request
import qumulo.rest
qumulo.lib.opts.import_rest()

KILOBYTE = 1000
MEGABYTE = 1000 * KILOBYTE
GIGABYTE = 1000 * MEGABYTE

def login(host, user, passwd, port):
    '''Obtain credentials from the REST server'''
    conninfo = None
    creds = None

    try:
        # Create a connection to the REST server
        conninfo = qumulo.lib.request.Connection(host, int(port))

        # Provide username and password to retreive authentication tokens
        # used by the credentials object
        login_results, _ = qumulo.rest.auth.login(
                conninfo, None, user, passwd)

        # Create the credentials object which will be used for
        # authenticating rest calls
        creds = qumulo.lib.auth.Credentials.from_login_response(login_results)
    except Exception, excpt:
        print "Error connecting to the REST server: %s" % excpt
        print __doc__
        sys.exit(1)

    return (conninfo, creds)

def send_mail(smtp_server, sender, recipient, subject, body):
    mmsg = MIMEText(body, 'html')
    mmsg['Subject'] = subject
    mmsg['From'] = sender
    mmsg['To'] = recipient

    session = smtplib.SMTP(smtp_server)
    session.sendmail(sender, [recipient], mmsg.as_string())
    session.quit()

def monitor_path(path, quota, conninfo, creds, smtp_server, sender, recipient):
    node = qumulo.rest.fs.read_dir_aggregates(conninfo, creds, path)
    quota = int(quota) * GIGABYTE
    subject = "Quota exceeded"
    body = ""

    current_usage = int(node[0]['total_capacity'])
    if current_usage > quota:
        excess_usage = abs(quota - current_usage)
        body += "Your usage on " + path + " exceeded your quota. "
        body += "Current usage is " + str(current_usage) + \
               ", while the quota specified is " + str(quota)
        body += ". You exceeded the quota by: " + str("{:.2f}".format(excess_usage) + " bytes.")
        body += "<br>"

    for n in node[0]['files']:
        if n['type'] == 'FS_FILE_TYPE_DIRECTORY':
            current_usage = int(n['capacity_usage'])
            print n['name']
            if current_usage >= quota:
                excess_usage = abs(quota - current_usage)
                body += "Your usage on " + path + "/" + n['name'].encode('utf-8') + " exceeded your quota. "
                body += "Current usage is " + str(current_usage) + \
                       ", while the quota specified is " + str(quota)
                body += ". You exceeded the quota by: " + str("{:.2f}".format(excess_usage) + " bytes.")
                body += "<br>"

    if body:
        send_mail(smtp_server, sender, recipient,  subject, body)

### Main subroutine
def main(argv):

    parser = argparse.ArgumentParser()
    parser.add_argument('--host', dest='host', required=True)
    parser.add_argument('--user', dest='user', required=True)
    parser.add_argument('--password', dest='password', required=True)
    parser.add_argument('--port', dest='port', default=8000, type=int)
    parser.add_argument('--path', dest='path', default='/')
    parser.add_argument('--quota', dest='quota', required=True, type=float)
    parser.add_argument('--smtp', dest='smtp', default='mail.corp.qumulo.com')
    parser.add_argument('--sender', dest='sender', default='qdf@qumulo.com')
    parser.add_argument('--recipient', dest='recipient', default='karim@qumulo.com')

    opts = parser.parse_args(argv)
    (conninfo, creds) = login(opts.host, opts.user, opts.password, opts.port)
    monitor_path(opts.path, opts.quota, conninfo, creds, opts.smtp,
                 opts.sender, opts.recipient)

# Main
if __name__ == '__main__':
    main(sys.argv[1:])
