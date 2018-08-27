import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from common import config


class Gmail:
    def __init__(self, acc, pwd):
        self.acc = acc
        self.pwd = pwd
        self.msg = MIMEMultipart('alternative')

        self.mail = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        self.mail.ehlo()
        self.mail.login(acc, pwd)

    def format_schedule_body(self, farefinder):
        fares = farefinder.results

        self.msg['Subject'] = "{} BoltBus Schedules Found Between {} and {}" \
            .format(len(fares),
                    farefinder._format_date(farefinder.initial_date),
                    farefinder._format_date(farefinder.search_date))
        self.msg['From'] = self.acc
        self.msg['To'] = ", ".join(config.props["dest_emails"])

        msg_body = "<html><body>"

        msg_body += """
                    <div style="text-align:center">
                        <b>{}</b>
                        <br/>to<br/>
                        <b>{}</b>
                        <br/><div>==============================================</div><br/>
                    </div>
                    """.format(farefinder.start.get("name"), farefinder.end.get("name"))

        for fare in fares:
            msg_body += \
                """
                <div style="text-align:center">
                    <div style="display:inline-block; width:180px;text-align:left;">Date: <b>{}</b></div>
                    <div style="display:inline-block; width:180px;text-align:left;">Departure: {}</div>
                    <br/>
                    <div style="display:inline-block; width:180px;text-align:left;">Price: <b>{}</b></div>
                    <div style="display:inline-block; width:180px;text-align:left;">Arrival: {}</div>
                </div>
                <br/>
                """.format(fare.get("date"), fare.get("departure"), fare.get("price"), fare.get("arrival"))
        msg_body += "</body></html>"

        self.msg.attach(MIMEText(msg_body, 'html'))

        return self.msg

    def send_schedule_alert(self):
        if self.msg:
            self.mail.sendmail(from_addr=self.acc, to_addrs=config.props["dest_emails"], msg=self.msg.as_string())
