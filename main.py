from flask import Flask, request, jsonify
import face_recognition as fr
import mysql.connector
import numpy as np
from datetime import datetime
import pytz

def get_database():
    connection = mysql.connector.connect(
        host="rnbansos.db4free.net",
        port=3306,
        user="fauzan",
        password="fauzanazim220602",
        database="rnbansos"
    )
    return connection

def get_encodings(cursor):
    query = "SELECT * FROM encodings"
    cursor.execute(query)
    results = cursor.fetchall()

    known_images = []
    encodings = []
    person_ids = []
    NIKs = []

    for row in results:
        id, person_name, encoding_str, NIK = row
        known_images.append(person_name)
        person_ids.append(id)
        NIKs.append(NIK)
        encoding_list = list(map(float, encoding_str.split(b',')))
        encodings.append(np.array(encoding_list))

    return known_images, encodings, person_ids, NIKs

def update_face(cursor, person_name, NIK, add_img):
    add_image = fr.load_image_file(add_img)
    
    try:
        image_encoding = list(fr.face_encodings(add_image)[0])
    except IndexError as e:
        return False

    try:
        encoding_str = ','.join(map(str, image_encoding))
        query = f"INSERT INTO encodings (person_name, encoding_str, NIK) VALUES ('{person_name}', '{encoding_str}', '{NIK}')"
        cursor.execute(query)
        return True
    except Exception as e:
        return False

def compare_faces(cursor, base_img):
    known_images, encodings, person_ids, NIKs = get_encodings(cursor)
    test = fr.load_image_file(base_img)

    try:
        test_encoding = fr.face_encodings(test)[0]
    except IndexError as e:
        return False, None, None, None  # Return False and None for person_id, NIK, and status

    results = fr.compare_faces(encodings, test_encoding)

    if True in results:
        i = results.index(True)
        person_id = person_ids[i]
        NIK = NIKs[i]
        person_name = known_images[i].split(".")[0]
        return True, person_id, NIK, person_name

    return False, None, None, None  # Return False and None for person_id, NIK, and status

def update_attendance(cursor, person_id, NIK, person_name):
    WIB = pytz.timezone('Asia/Jakarta')
    now = datetime.now(WIB)
    moment_date = now.strftime("%Y-%m-%d")
    moment_time = now.strftime("%H:%M:%S")

    query = f"INSERT INTO person_data (person_id, NIK, person_name, date, time) VALUES ('{person_id}', '{NIK}', '{person_name}', '{moment_date}', '{moment_time}')"
        
    try:
        cursor.execute(query)
        return True
    except Exception as e:
        return False

app = Flask(__name__)

@app.route('/face_match', methods=['POST'])
def face_match():
    if request.method == 'POST':
        if 'file1' in request.files:
            file1 = request.files.get('file1')
            connection = get_database()
            cursor = connection.cursor()

            response, person_id, NIK, person_name = compare_faces(cursor, file1)
            if response:
                update_attendance(cursor, person_id, NIK, person_name)
            
            connection.commit()
            cursor.close()
            connection.close()

            return jsonify({"status": response, 'person_id': person_id, 'NIK': NIK, 'person_name': person_name})

        return "Not Handled"

@app.route('/add_face', methods=['POST'])
def add_face():
    if request.method == 'POST':
        if 'file1' in request.files:
            file1 = request.files.get('file1')
            person_name = file1.filename.split(".")[0]

            # Updated: Extract NIK and person_name from the request body
            data = request.form.to_dict()
            NIK = data.get('NIK')
            person_name = data.get('person_name')

            connection = get_database()
            cursor = connection.cursor()

            # Check if the face already exists in the database
            exists, existing_person_id, existing_NIK, existing_person_name = compare_faces(cursor, file1)
            
            if exists:
                cursor.close()
                connection.close()
                return jsonify({"status": False, "message": "Face already exists in the database.", "person_id": existing_person_id, "NIK": existing_NIK, "person_name": existing_person_name})

            # If face is not in the database, proceed to add it
            response = update_face(cursor, person_name, NIK, file1)
            
            connection.commit()
            cursor.close()
            connection.close()

            return jsonify({"status": response, "message": "Face added successfully.", "person_id": None, "NIK": None, "person_name": None})

    return "Not Handled"

@app.route('/', methods=['GET'])
def home():
    return 'WELCOME FACE RECOG APP API'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
