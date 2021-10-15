import time
import tkinter

import mysql.connector
import pyzbar.pyzbar as pyzbar  # Module to read QR codes

import qrcode  # Module for generating qr codes
import smtplib  # Default Python library for emails
import imghdr  # Module to determine image file type, needed for emails
from email.message import EmailMessage

import cv2  # computer vision

from datetime import datetime, timedelta

from decouple import config  # Module to read environment variables

from tkinter import *
from PIL import Image, ImageTk

WINDOW_WIDTH = 1500
WINDOW_HEIGHT = 821

SECONDS_IN_AN_HOUR = 3600

# Get credentials from .env
BOT_USER = config('BOT_USER')
BOT_PASS = config('BOT_PASS')
DB_HOST = config('DB_HOST')
DB_USER = config('DB_USER')
DB_PASS = config('DB_PASS')


def main():
    # Create window
    window, label, output = setup_window()

    running = True
    while running:
        read_image(label, window, output)


def setup_window():
    window = Tk()
    window.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}+131+83")

    # Create instruction Label and put it at the top of screen
    instructions_label = Label(window, text="Scan your QR code to sign in or create an account.", font=("Arial", 45))
    instructions_label.pack()
    instructions_label.place(anchor=N, x=WINDOW_WIDTH / 2)

    # Create LabelFrame for label which holds captured frame.
    frame = LabelFrame(window)
    frame.pack()
    frame.place(anchor=NW, y=100)  # Where we place the frame the label, parented will follow. like a real picture on a wall
    frame_label = Label(frame)
    frame_label.pack()

    # Create account label and entries
    nau_id_label = Label(window, text="Nau ID", font=("Arial", 35))  # NauID label
    nau_id_label.pack()
    nau_id_label.place(anchor=N, x=WINDOW_WIDTH - 325, y=100)

    nau_id = tkinter.StringVar(window)
    enter_nauid = Entry(window, font=("Arial", 35), textvariable=nau_id)  # NauID entry
    enter_nauid.pack()
    enter_nauid.place(anchor=NE, x=WINDOW_WIDTH - 50, y=170)

    first_name_label = Label(window, text="First Name", font=("Arial", 35))  # First name label
    first_name_label.pack()
    first_name_label.place(anchor=N, x=WINDOW_WIDTH - 325, y=235)

    first_name = tkinter.StringVar(window)
    enter_first_name = Entry(window, font=("Arial", 35), textvariable=first_name)  # First name entry
    enter_first_name.pack()
    enter_first_name.place(anchor=NE, x=WINDOW_WIDTH - 50, y=305)

    # Create account button
    btn_create_acc = Button(window,
                            text='Create Account.',
                            command=lambda: create_acc(enter_nauid.get(), enter_first_name.get(), output_label, window, enter_first_name, enter_nauid),
                            font=("Arial", 35))
    btn_create_acc.pack()
    btn_create_acc.place(anchor=N, x=WINDOW_WIDTH - 325, y=400)

    # Label for output, bottom of window
    output_label = Label(window,
                         text="Waiting for input...",
                         font=("Arial Bold", 35),
                         wraplength=WINDOW_WIDTH - 100,
                         fg="#00c400")  # green
    output_label.pack()
    output_label.place(anchor=S, x=WINDOW_WIDTH / 2, y=WINDOW_HEIGHT - 90)
    return window, frame_label, output_label


def read_image(label, window, output):
    nau_id = ""
    db = connect_to_db()

    # Capture video
    cap = cv2.VideoCapture(0)  # 0 = first cam
    # resolution of capture
    cap.set(3, 720)  # Height
    cap.set(4, 720)  # Width

    data_received = False

    while not data_received:

        img = cap.read()[1]

        decoded_objects = pyzbar.decode(img)

        for obj in decoded_objects:
            obj_data_bytes = obj.data  # Data in bytes
            data = obj_data_bytes.decode('utf-8')
            nau_id += data
            data_received = True

        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = ImageTk.PhotoImage(Image.fromarray(img))
        label['image'] = img
        window.update()

    my_curser = db.cursor()

    # get date from last sign in
    # if the date is < 20 hours ago, don't allow sign in

    my_curser.execute(f"SELECT last_sign_in_date FROM acmmembers where username = '{nau_id}'")

    result = my_curser.fetchone()

    last_sign_in_date = ""

    for row in result:
        last_sign_in_date = row

    now = datetime.now()

    duration = now - last_sign_in_date
    duration_in_seconds = duration.total_seconds()
    hours_since_last_sign_in = duration_in_seconds / SECONDS_IN_AN_HOUR

    hours_since_last_sign_in = float(format(hours_since_last_sign_in, ".2"))

    if hours_since_last_sign_in > 20:
        update_statement = "UPDATE acmmembers SET tickets = tickets + 1, last_sign_in_date = %s WHERE username = %s"
        statement_data = (now, nau_id)

        my_curser.execute(update_statement, statement_data)
        db.commit()

        output.config("Signed in, Earned 1 point for today.")
    else:
        output.config(text=f"You have signed in too recently. Last sign in was {hours_since_last_sign_in} hours ago.")
        window.update()
        time.sleep(1)
    time.sleep(2)  # Once we processed everything, give some leeway time before we try to get next QR code
    output.config(text="Waiting for input...")


def send_mail(image, nau_username, output, window, enter_nau_id, enter_first_name):
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

        output.config(text=f"Email sent to {send_to}")
        enter_nau_id.config(textvariable=StringVar(""))
        enter_first_name.config(textvariable=StringVar(""))
        window.update()
        time.sleep(3)
        output.config(text="Waiting for input...")


def create_acc(nau_id, first_name, output, window, enter_nau_id, enter_first_name):

    qr_file_name = f"{nau_id}.jpg"

    img = qrcode.make(str(nau_id))  # create out qr code
    img.save(qr_file_name)  # Save it with its name

    db = connect_to_db()

    my_cursor = db.cursor()

    insert_statement = "INSERT INTO AcmMembers (Username, first_name, tickets, last_sign_in_date) VALUES (%s, %s, %s, %s)"
    data = (nau_id, first_name, 1, datetime.now())  # Grant 1 ticket for attending initial meeting

    my_cursor.execute(insert_statement, data)  # Use this to execute queries
    db.commit()
    send_mail(qr_file_name, nau_id, output, window, enter_nau_id, enter_first_name)


def connect_to_db():
    db = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        passwd=DB_PASS,
        database="nauacm",
    )
    return db


main()
