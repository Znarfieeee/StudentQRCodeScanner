from flask import Flask, render_template, redirect, request, flash, url_for, session, send_file
from dbhelper import *
import qrcode
from io import BytesIO
from base64 import b64encode
import os, sqlite3

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = "static/images"
app.config['SECRET_KEY'] = "qwerty12345"

@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, private"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route('/login', methods=['GET', 'POST'])
def login():
    if session.get('logged_in'):
        return redirect(url_for('scanner'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            flash('Username and Password are required!', 'error')
            return redirect(url_for('login'))
        
        sql = "SELECT * FROM users WHERE username = ? AND password = ?"
        user = getallprocess(sql, (username, password))
        
        if user:
            session['logged_in'] = True
            session['user'] = username 
            flash('Login successful!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Login failed!', 'error')
            return redirect(url_for('login'))
        
    return render_template('login.html', pagetitle="Login")

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('scanner'))

@app.route("/")
def index():
    
    students = getall_records('students')
    return render_template("index.html", pagetitle="Student Information Management", students=students)

@app.route('/saveinformation', methods=['POST'])
def saveinformation():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    idno = request.form.get('idno')
    lastname = request.form.get('lastname')
    firstname = request.form.get('firstname')
    course = request.form.get('course')
    level = request.form.get('level')
    
    data_uri = request.files.get('webcam')
    qode_file = request.files.get('qr_Image')

    if idno and data_uri:
        image_filename = f"{idno}.jpeg"
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
        
        # Save student photo
        try:
            data_uri.save(image_path)
        except Exception as e:
            return redirect(url_for('index'))
        
        # Save QR code if uploaded
        if qode_file and qode_file.filename:
            qode_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{idno}_qr.png")
            try:
                qode_file.save(qode_path)
            except Exception as e:
                return redirect(url_for('index'))
        else:
            flash("QR code file not provided or invalid", "error")
            return redirect(url_for('index'))
        
        # Add student record to the database
        success = add_record(
            'students', 
            idno=idno, 
            lastname=lastname, 
            firstname=firstname, 
            course=course, 
            level=level, 
            image=image_filename, 
            qode=f"{idno}_qr.png" if qode_file else None
        )
        flash("Student added" if success else "Error adding student", "success" if success else "error")
    else:
        flash("Incomplete data provided", "error")
    
    return redirect(url_for('index'))

@app.route('/delete_student/<idno>', methods=['POST'])
def delete_student(idno):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    image_filename = f"{idno}.jpeg"
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
    sql:str = "DELETE FROM students WHERE idno = ?"
    success = postprocess(sql, (idno,))

    if success:
        flash(f"Student with ID {idno} has been deleted.", 'success')
        try:
            os.remove(image_path)
        except FileNotFoundError:
            flash("Image file not found, but student record deleted.", 'warning')
    else:
        flash(f"Error deleting student with ID {idno}.", 'error')
    
    return redirect(url_for('index'))

@app.route('/updatestudent/<idno>', methods=['POST'])
def updatestudent(idno):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    
    lastname = request.form.get('lastname')
    firstname = request.form.get('firstname')
    course = request.form.get('course')
    level = request.form.get('level')
    
    image = request.files.get('webcam')
    image_filename = f"{idno}.jpeg" if image else None
    if image:
        image_path = os.path.join(app.config['UPLOAD_FOLDER'], image_filename)
        image.save(image_path)
        
    sql = "UPDATE students SET lastname = ?, firstname = ?, course = ?, level = ?"
    params = [lastname, firstname, course, level]
    if image_filename:
        sql += ", image = ?"
        params.append(image_filename)
        
    sql += " WHERE idno = ?"
    params.append(idno)
    
    success = postprocess(sql, tuple(params))
    
    flash("Student Updated Successfully!" if success else "Error updating student.", "success" if success else "error")
    return redirect(url_for('index'))

@app.route('/checkidno/<idno>', methods=['GET'])
def checkidno(idno):
    sql = "SELECT 1 FROM students WHERE idno = ?"
    student = getallprocess(sql, (idno,))
    return {"exists": bool(student)}

@app.route('/generate_qrcode', methods=['POST'])
def generate_qrcode():
    try:
        idno:str = request.form.get('idno')
        
        if not idno:
            return {"error": "ID number is required."}, 400
        
        #mao ni sa pag buhat sa QR
        qr = qrcode.QRCode(
            version= 1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(idno)
        qr.make(fit=True)
        img = qr.make_image(fill='black', back_color='white')
        
        
        qr_filename = f"{idno}_qr.png"
        qr_filepath = os.path.join(app.config['UPLOAD_FOLDER'], qr_filename)
        
        #Pagsave sa QR
        img.save(qr_filepath)

        return qr_filename

    except Exception as e:
        print(f"Error generating QR code: {e}")
        return None 

@app.route('/scanner')
def scanner():
    students = getall_records('students')
    return render_template('scanner.html', pagetitle='Parsing QR Code', students=students)

@app.route('/getstudent/<idno>', methods=['GET'])
def getstudent(idno):
    sql = "SELECT idno, lastname, firstname, course, level, image FROM students WHERE idno = ?"
    student = getallprocess(sql, (idno,))
    if student:
        return {
            "idno": student[0]['idno'],
            "lastname": student[0]['lastname'],
            "firstname": student[0]['firstname'],
            "course": student[0]['course'],
            "level": student[0]['level'],
            "image": student[0]['image']
        }
    return {"error": "Student not found"}, 404

@app.route('/log_attendance/<idno>', methods=['POST'])
def log_attendance(idno):
    sql_fetch = "SELECT idno, lastname, firstname, course, level FROM students WHERE idno = ?"
    student = getallprocess(sql_fetch, (idno,))

    if not student:
        return {"success": False, "message": "Student not found"}, 404

    student_details = (
        student[0]['idno'], 
        student[0]['lastname'], 
        student[0]['firstname'], 
        student[0]['course'], 
        student[0]['level']
    )

    try:
        conn = sqlite3.connect('attendance.db', timeout=10)
        cursor = conn.cursor()
        
        sql_insert = """
            INSERT INTO checker (idno, lastname, firstname, course, level)
            VALUES (?, ?, ?, ?, ?)
        """
        cursor.execute(sql_insert, student_details)
        conn.commit()
        conn.close()

        return {"success": True}
    except Exception as e:
        print(f"Error logging attendance: {e}")
        return {"success": False, "message": "Failed to log attendance"}, 500
    
@app.route('/view_attendance')
def view_attendance():
    try:
        conn = sqlite3.connect('attendance.db', timeout=10) 
        cursor = conn.cursor()
        
        sql_fetch = "SELECT idno, lastname, firstname, course, level, time_logged FROM checker ORDER BY time_logged DESC"
        cursor.execute(sql_fetch)
        attendance_records = cursor.fetchall()
        conn.close()

        return render_template('viewAttendance.html', students=attendance_records, pagetitle='View Attendance')
    except Exception as e:
        print(f"Error fetching attendance records: {e}")
        flash("Error loading attendance records.", "error")
        return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(debug=True)