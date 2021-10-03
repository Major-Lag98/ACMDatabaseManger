import mysql.connector

import qrcode  # pip python library for generating qr codes
import smtplib  # Default Python library for emails
import imghdr
from email.message import EmailMessage

import cv2


def main():
    running = True

    while running:

        print("What would you like to do? Type (1 or 2)")
        choice = int(input("(1: Create account, 2: Sign in) "))

        if choice == 1:
            create_acc()
        else:
            sign_in()

        running = should_continue()


def should_continue():
    answer = " "
    while answer[0].lower() != 'y' and answer[0].lower() != 'n':
        answer = input("Continue running? Enter (y/n): ")

    if answer.lower() == 'y':
        return True
    else:
        return False


def send_mail(image, nau_username):

    send_to = f"{nau_username}@nau.edu"

    message = "This is your personal QR code. You will use this in the future to sign into the acm meetings and earn " \
              "points! It is recommended to save this image to your phone or print it. Be sure to bring it to every " \
              "meeting."

    msg = EmailMessage()
    msg["Subject"] = "Welcome to ACM"
    msg["From"] = "aldensbotalerts@gmail.com"
    msg["To"] = send_to
    msg.set_content(message)

    with open(image, "rb") as file:  # open image in ReadBytes mode
        file_data = file.read()
        file_type = imghdr.what(file.name)
        file_name = file.name

    msg.add_attachment(file_data, maintype="image", subtype=file_type, filename=file_name)

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:  # Identifies us with the mail server & Encrypt traffic

        smtp.login("", "") # Bot account login

        smtp.send_message(msg)

        print(f"Email sent to {send_to}")


def create_acc():
    nau_username = input("Enter our NAU username (ex: aaa123): ")
    first_name = input("Please enter your first name: ")

    qr_file_name = f"{nau_username}.jpg"

    img = qrcode.make(str(nau_username))  # create out qr code
    img.save(qr_file_name)  # Save it with its name

    db = mysql.connector.connect(
        host="acmmembers.mysql.database.azure.com",
        user="acmadmin@acmmembers",
        passwd="ACMst@rtsNOW!",
        database="nauacm",
    )

    my_cursor = db.cursor()

    insert_statement = "INSERT INTO AcmMembers (Username, first_name, tickets) VALUES (%s, %s, %s)"
    data = (nau_username, first_name, 1)  # Grant 1 ticket for attending initial meeting

    my_cursor.execute(insert_statement, data)  # Use this to execute queries
    db.commit()
    send_mail(qr_file_name, nau_username)

def sign_in():
    print("test")

main()
