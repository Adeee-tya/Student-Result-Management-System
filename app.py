from flask import Flask, render_template, request, redirect, url_for
import mysql.connector

app = Flask(__name__)

# Core MySQL Database Connection Bridge
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="YOUR_LOCAL_MYSQL_PASSWORD"
        database="student_management"
    )

# 1. ROUTE: Server Root Landing - Displays the Login Interface
@app.route('/')
def home():
    return render_template('login.html')

# 2. ROUTE: Form Handler - Authenticates users against the database
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    role = request.form['role']
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s AND role = %s", (username, password, role))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user:
            return redirect(url_for('dashboard'))
        else:
            return "<h3>Invalid Credentials.</h3><a href='/'>Try Again</a>"
    except Exception as e:
        return f"<h3>Database Connection Error during Login:</h3><p>{e}</p>"

# 3. ROUTE: Serves the central System Dashboard Hub with Real-Time Statistics
@app.route('/dashboard')
def dashboard():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Fetch total overall count of registered students
        cursor.execute("SELECT COUNT(*) as total FROM students")
        total_data = cursor.fetchone()
        total_students = total_data['total'] if total_data else 0
        
        # Fetch enrollment breakdown counts grouped neatly by semester numbers
        query = """
            SELECT current_semester, COUNT(*) as count 
            FROM students 
            GROUP BY current_semester 
            ORDER BY current_semester ASC
        """
        cursor.execute(query)
        semester_rows = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('dashboard.html', 
                               total_count=total_students, 
                               semesters_data=semester_rows)
    except Exception as e:
        return render_template('dashboard.html', total_count=0, semesters_data=[], error=str(e))

# 4. ROUTE: Serves the Student Registration Intake Form View
@app.route('/register-student')
def register_student_page():
    return render_template('register.html')

# 5. ROUTE: Form Handler - Adds new student records to MySQL and Redirects Cleanly
@app.route('/add-student', methods=['POST'])
def add_student_logic():
    roll_number = request.form['roll_number']
    admission_year = request.form['admission_year']
    current_semester = request.form['current_semester'] # <-- Perfect key link pairing
    full_name = request.form['full_name']
    email = request.form['email']
    gender = request.form['gender']
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "INSERT INTO students (roll_number, full_name, email, gender, admission_year, current_semester) VALUES (%s, %s, %s, %s, %s, %s)"
        cursor.execute(query, (roll_number, full_name, email, gender, admission_year, current_semester))
        conn.commit()
        cursor.close()
        conn.close()
        
        return redirect('/register-student?success=1')
    except Exception as e:
        return f"<h3>Registration Failed:</h3><p>{e}</p><a href='/register-student'>Try Again</a>"

# 6. ROUTE: Serves the combined Marks Entry & SQL Console panel
@app.route('/enter-marks')
def enter_marks_view():
    return render_template('marks.html')

# 7. ROUTE: Form Handler - Logs marks into the database
@app.route('/submit-marks', methods=['POST'])
def process_marks_logic():
    roll_no = request.form['roll_no']
    subject_id = int(request.form['subj_id'])
    semester_id = int(request.form['sem_id'])
    score = int(request.form['marks_val'])
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT student_id FROM students WHERE roll_number = %s", (roll_no,))
        student = cursor.fetchone()
        
        if not student:
            cursor.close()
            conn.close()
            return render_template('marks.html',error_msg=f"Error:Roll Number '{roll_no} was not found in the portal records.'")
            
        query = "INSERT INTO marks (student_id, subject_id, semester_id, obtained_marks) VALUES (%s, %s, %s, %s)"
        cursor.execute(query, (student['student_id'], subject_id, semester_id, score))
        conn.commit()
        cursor.close()
        conn.close()
        return render_template('marks.html', success_msg=f"✓ Score of {score} logged successfully for {roll_no}!")
    except Exception as e:
        return render_template('marks.html', error_msg=f"Database Execution Fault: {e}")

# 8. ROUTE: Core Terminal Handler - Runs ad-hoc SQL strings and renders data back
@app.route('/run-query', methods=['POST'])
def terminal_sql_executor():
    sql_command = request.form['sql_command']
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(sql_command)
        if cursor.description:
            rows = cursor.fetchall()
            headers = [desc[0] for desc in cursor.description]
            output_string = " | ".join(headers) + "\n" + "-"*60 + "\n"
            for row in rows:
                output_string += " | ".join(str(item) for item in row) + "\n"
        else:
            conn.commit()
            output_string = f"Success. Affected rows: {cursor.rowcount}"
        cursor.close()
        conn.close()
        return render_template('marks.html', query_result=output_string)
    except Exception as err:
        return render_template('marks.html', query_result=f"SQL Error:\n{err}")

# 9. ROUTE: Renders the initial Report Viewer Interface
@app.route('/reports')
def reports_view():
    return render_template('reports.html')

# 10. ROUTE: Core Logic Engine - Extracts values, joins tables, and calculates grading marks dynamically
@app.route('/generate-report', methods=['POST'])
def generate_report_logic():
    roll_no = request.form['search_roll']
    semester_id = int(request.form['search_sem'])
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT * FROM students WHERE roll_number = %s", (roll_no,))
        student_info = cursor.fetchone()
        
        if not student_info:
            cursor.close()
            conn.close()
            return render_template('reports.html', error_msg="Search Error: Student Roll Number not found.")
        
        query = """
            SELECT s.subject_code, s.subject_name, s.max_marks, m.obtained_marks 
            FROM marks m
            JOIN subjects s ON m.subject_id = s.subject_id
            WHERE m.student_id = %s AND m.semester_id = %s
        """
        cursor.execute(query, (student_info['student_id'], semester_id))
        marks_rows = cursor.fetchall()
        
        for row in marks_rows:
            score = row['obtained_marks']
            if score >= 90: row['grade'] = 'A+'
            elif score >= 80: row['grade'] = 'A'
            elif score >= 70: row['grade'] = 'B'
            elif score >= 60: row['grade'] = 'C'
            elif score >= 50: row['grade'] = 'D'
            else: row['grade'] = 'F'
            
        cursor.close()
        conn.close()
        return render_template('reports.html', student_info=student_info, marks_list=marks_rows, selected_sem=semester_id)
    except Exception as e:
        return render_template('reports.html', error_msg=f"System Error: {e}")

if __name__ == '__main__':
    app.run(debug=True)
