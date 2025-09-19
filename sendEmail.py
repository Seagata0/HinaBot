from datetime import date
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
print("Process: Sending Email")

subject = f"Docs of {date.today()} Mission"
body = "Sensei, here is the file" #the body of the email
sender_email = "sorasakihina@gmail.com" #sender Email
recipient_email = "seagata0@gmail.com" #recipient Email
sender_password = "jnys vjqo XXXX XXXX" #the sender password, if using gmail you need to make an app password for the said email
smtp_server = 'smtp.gmail.com' #this is for gmail
smtp_port = 465
path_to_file = f'Mission Brief {date.today()}.pdf'

message = MIMEMultipart()
message['Subject'] = subject
message['From'] = sender_email
message['To'] = recipient_email
body_part = MIMEText(body)
message.attach(body_part)

with open(path_to_file,'rb') as file:
    message.attach(MIMEApplication(file.read(), Name=path_to_file))

with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
    server.login(sender_email, sender_password)
    server.sendmail(sender_email, recipient_email, message.as_string())
    print("Status: Email Sended")