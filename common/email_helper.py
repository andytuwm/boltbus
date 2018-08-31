import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from common import config


class Gmail:
    def __init__(self):
        self.sender = config.props["sender_address"]
        self.msg = MIMEMultipart('alternative')

        self.mail = smtplib.SMTP("email-smtp.us-west-2.amazonaws.com", 587)
        self.mail.starttls()
        self.mail.login(config.props["ses"]["access_key"], config.props["ses"]["secret"])

    def format_schedule_body(self, farefinder):
        fares = farefinder.results

        self.msg['Subject'] = "{} BoltBus Schedules Found Between {} and {}" \
            .format(len(fares),
                    farefinder._format_date(farefinder.initial_date),
                    farefinder._format_date(farefinder.search_date))
        self.msg['From'] = self.sender
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
            self.mail.sendmail(from_addr=self.sender, to_addrs=config.props["dest_emails"], msg=self.msg.as_string())
