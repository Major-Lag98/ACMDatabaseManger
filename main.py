import mysql.connector
import pyzbar.pyzbar as pyzbar  # Module to read QR codes

import qrcode  # Module for generating qr codes
import smtplib  # Default Python library for emails
import imghdr  # Module to determine file type
from email.message import EmailMessage

import cv2  # computer vision

from datetime import datetime

from decouple import config  # Module to read environment variables

SECONDS_IN_AN_HOUR = 3600

# Get credentials from .env
BOT_USER = config('BOT_USER')
BOT_PASS = config('BOT_PASS')
DB_HOST = config('DB_HOST')
DB_USER = config('DB_USER')
DB_PASS = config('DB_PASS')


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
    msg["From"] = BOT_USER  # bot usr
    msg["To"] = send_to
    msg.set_content(message)

    with open(image, "rb") as file:  # open image in ReadBytes mode
        file_data = file.read()
        file_type = imghdr.what(file.name)
        file_name = file.name

    msg.add_attachment(file_data, maintype="image", subtype=file_type, filename=file_name)

    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:  # Identifies us with the mail server & Encrypt traffic

        smtp.login(BOT_USER, BOT_PASS)  # Bot account login

        smtp.send_message(msg)

        print(f"Email sent to {send_to}")


def create_acc():
    nau_username = input("Enter our NAU username (ex: aaa123): ")
    first_name = input("Please enter your first name: ")

    qr_file_name = f"{nau_username}.jpg"

    img = qrcode.make(str(nau_username))  # create out qr code
    img.save(qr_file_name)  # Save it with its name

    db = connect_to_db()

    my_cursor = db.cursor()

    insert_statement = "INSERT INTO AcmMembers (Username, first_name, tickets, last_sign_in_date) VALUES (%s, %s, %s, %s)"
    data = (nau_username, first_name, 1, datetime.now())  # Grant 1 ticket for attending initial meeting

    my_cursor.execute(insert_statement, data)  # Use this to execute queries
    db.commit()
    send_mail(qr_file_name, nau_username)


def sign_in():
    cap = cv2.VideoCapture(0)
    cap.set(3, 1920)  # Width
    cap.set(4, 1080)  # Height

    nauid = ""

    db = connect_to_db()

    data_received = False

    while not data_received:  # make while data not received
        _, frame = cap.read()

        decoded_objects = pyzbar.decode(frame)

        for obj in decoded_objects:
            b = obj.data  # data in type bytes
            data = b.decode('utf-8')  # data now a string
            nauid += data
            data_received = True

        cv2.imshow("Frame", frame)

        key = cv2.waitKey(1)
        if key == 27:
            break
    my_cursor = db.cursor()

    # get date from last sign in
    # if the date > 20.0 from now allow sign in, else say you cant and leave

    my_cursor.execute(f"Select last_sign_in_date FROM acmmembers where username = '{nauid}'")

    result = my_cursor.fetchone()

    last_sign_in_date = ""

    for row in result:
        last_sign_in_date = row

    now = datetime.now()

    duration = now - last_sign_in_date
    duration_in_seconds = duration.total_seconds()
    hours_since_last_sign_in = duration_in_seconds / SECONDS_IN_AN_HOUR  # we only care about hours so drop the integer.

    hours_since_last_sign_in = float(format(hours_since_last_sign_in, ".2"))

    if hours_since_last_sign_in > 20.0:
        update_statement = "UPDATE acmmembers SET tickets = tickets + 1, last_sign_in_date = %s WHERE username = %s"
        statement_data = (now, nauid)

        my_cursor.execute(update_statement, statement_data)
        db.commit()

        print("Signed in, Earned 1 point for attending today!")
    else:
        print("You have signed in too recently.")
        print(f"Last sign in was {hours_since_last_sign_in} hours ago.")


def connect_to_db():
    db = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        passwd=DB_PASS,
        database="nauacm",
    )
    return db


main()
