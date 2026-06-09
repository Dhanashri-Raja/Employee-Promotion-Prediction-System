from flask import Flask, render_template, request, redirect, url_for, session, make_response, jsonify
import pickle
import pandas as pd
import mysql.connector
from datetime import datetime

app = Flask(__name__)
app.secret_key = "YOUR_SECRET_KEY"

# Load ML model
with open("attr.pkl", "rb") as f:
    model = pickle.load(f)

# Database Connection
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="YOUR_MYSQL_PASSWORD",
    database="promotion_db1"
)
cursor = db.cursor(dictionary=True)


# ---------------- LOGIN PAGE ----------------
@app.route("/")
def login_page():
    if "hr_logged_in" in session:
        return redirect(url_for("dashboard"))
    return render_template("login.html")


# ---------------- LOGIN CHECK ----------------
@app.route("/login", methods=["POST"])
def login():
    email = request.form["email"]
    password = request.form["password"]

    sql = "SELECT * FROM hr_details WHERE email=%s AND password=%s"
    cursor.execute(sql, (email, password))
    hr = cursor.fetchone()

    if hr:
        session["hr_logged_in"] = True
        return redirect(url_for("dashboard"))
    else:
        return render_template("login.html", error="Invalid Email or Password")


# ---------------- FORGOT PASSWORD PAGE ----------------
@app.route("/forgot")
def forgot():
    if "hr_logged_in" in session:
        return redirect(url_for("dashboard"))
    return render_template("forgot.html")


# ---------------- VERIFY HR DETAILS ----------------
@app.route("/verify_hr", methods=["POST"])
def verify_hr():
    email = request.form["email"]
    emp_id = request.form["emp_id"]

    sql = "SELECT * FROM hr_details WHERE email=%s AND emp_id=%s"
    cursor.execute(sql, (email, emp_id))
    hr = cursor.fetchone()

    if hr:
        return render_template("reset_password.html", email=email)
    else:
        return render_template("forgot.html", error="Invalid Email or Employee ID")

# ---------------- RESET PASSWORD router ----------------

@app.route("/reset_password", methods=["POST"])
def reset_password():
    email = request.form["email"]
    new_password = request.form["new_password"]

    sql = "UPDATE hr_details SET password=%s WHERE email=%s"
    cursor.execute(sql, (new_password, email))
    db.commit()

    return redirect(url_for("login_page"))


# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
def dashboard():
    if "hr_logged_in" not in session:
        return redirect(url_for("login_page"))

    cursor.execute("SELECT COUNT(*) AS total FROM employee")
    total_emp = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM prediction_history")
    total_pred = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM prediction_history WHERE prediction='Eligible'")
    eligible = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) AS total FROM prediction_history WHERE prediction='Not Eligible'")
    not_eligible = cursor.fetchone()["total"]

    return render_template("dashboard.html",
                           total_emp=total_emp,
                           total_pred=total_pred,
                           eligible=eligible,
                           not_eligible=not_eligible)


@app.route("/home", methods=["GET", "POST"])
def home():
    if "hr_logged_in" not in session:
        return redirect(url_for("login_page"))

    prediction_text = None

    # Fetch employee list for datalist dropdown
    cursor.execute("SELECT emp_id, emp_name FROM employee ORDER BY emp_id")
    employee_list = cursor.fetchall()

    if request.method == "POST":
        try:
            emp_id = request.form.get("emp_id")  # Can be empty for external data
            emp_name = request.form.get("emp_name")

            # Default values from DB if emp_id exists
            emp = None
            performance = None
            if emp_id:
                cursor.execute("SELECT * FROM employee WHERE emp_id=%s", (emp_id,))
                emp = cursor.fetchone()

                cursor.execute("SELECT * FROM employee_performance WHERE emp_id=%s", (emp_id,))
                performance = cursor.fetchone()

            # Auto-fill missing fields if emp exists, else take manual input
            department = request.form.get("department") or (emp["department"] if emp else "")
            education = request.form.get("education") or (emp["education"] if emp else "")
            gender = request.form.get("gender") or (emp["gender"] if emp else "")
            age = request.form.get("age") or (emp["age"] if emp else 0)
            no_of_trainings = int(request.form.get("no_of_trainings") or (performance["no_of_trainings"] if performance else 0))
            previous_year_rating = int(request.form.get("previous_year_rating") or (performance["previous_year_rating"] if performance else 0))
            length_of_service = int(request.form.get("length_of_service") or (performance["length_of_service"] if performance else 0))
            awards_won = int(request.form.get("awards_won") or (performance["awards_won"] if performance else 0))
            avg_training_score = int(request.form.get("avg_training_score") or (performance["avg_training_score"] if performance else 0))

            # Create input dataframe for model
            input_df = pd.DataFrame([{
                "department": department,
                "education": education,
                "gender": gender,
                "no_of_trainings": no_of_trainings,
                "age": float(age),
                "previous_year_rating": previous_year_rating,
                "length_of_service": length_of_service,
                "awards_won": awards_won,
                "avg_training_score": avg_training_score
            }])

            # Predict
            pred = model.predict(input_df)[0]
            prediction_text = "Eligible" if pred == 1 else "Not Eligible"

            # Save prediction only if emp_id exists
            if emp_id:
                cursor.execute("""INSERT INTO prediction_history (emp_id, emp_name, prediction) 
                                  VALUES (%s, %s, %s)""", (emp_id, emp_name, prediction_text))
                db.commit()

            # Update or insert employee & performance only if emp_id exists
            if emp_id:
                if emp:
                    cursor.execute("UPDATE employee SET emp_name=%s, department=%s, education=%s, gender=%s, age=%s WHERE emp_id=%s",
                                   (emp_name, department, education, gender, age, emp_id))
                else:
                    cursor.execute("INSERT INTO employee (emp_id, emp_name, department, education, gender, age) VALUES (%s,%s,%s,%s,%s,%s)",
                                   (emp_id, emp_name, department, education, gender, age))

                if performance:
                    cursor.execute("""UPDATE employee_performance SET 
                                      no_of_trainings=%s, previous_year_rating=%s, length_of_service=%s,
                                      awards_won=%s, avg_training_score=%s, updated_at=%s
                                      WHERE emp_id=%s""",
                                   (no_of_trainings, previous_year_rating, length_of_service,
                                    awards_won, avg_training_score, datetime.now(), emp_id))
                else:
                    cursor.execute("""INSERT INTO employee_performance
                                      (emp_id, emp_name, no_of_trainings, previous_year_rating, length_of_service, awards_won, avg_training_score, created_at, updated_at)
                                      VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                                   (emp_id, emp_name, no_of_trainings, previous_year_rating, length_of_service, awards_won, avg_training_score, datetime.now(), datetime.now()))
                db.commit()

        except Exception as e:
            print("Error:", e)
            prediction_text = "Invalid input. Please check all values."

    # response = make_response(render_template("home.html",
    #                                          prediction=prediction_text,
    #                                          employee_list=employee_list))
    if request.method == "POST" and prediction_text:
        return render_template("result.html", result=prediction_text)

    response = make_response(render_template("home.html",
                                         prediction=None,
                                         employee_list=employee_list))
    response.headers["Cache-Control"] = "no-store"
    return response

# ---------------- AJAX ROUTE TO FETCH EMPLOYEE DATA ----------------
@app.route("/get_employee_details/<emp_id>")
def get_employee_details(emp_id):
    cursor.execute("SELECT * FROM employee WHERE emp_id=%s", (emp_id,))
    emp = cursor.fetchone()

    cursor.execute("SELECT * FROM employee_performance WHERE emp_id=%s", (emp_id,))
    performance = cursor.fetchone()

    result = {}
    if emp:
        result.update({
            "emp_name": emp["emp_name"],
            "department": emp["department"],
            "education": emp["education"],
            "gender": emp["gender"],
            "age": emp["age"]
        })
    if performance:
        result.update({
            "no_of_trainings": performance["no_of_trainings"],
            "previous_year_rating": performance["previous_year_rating"],
            "length_of_service": performance["length_of_service"],
            "awards_won": performance["awards_won"],
            "avg_training_score": performance["avg_training_score"]
        })
    return jsonify(result)


# ---------------- ADD EMPLOYEE ----------------
@app.route("/add_employee", methods=["GET","POST"])
def add_employee():
    if "hr_logged_in" not in session:
        return redirect(url_for("login_page"))
    error = None
    success = None

    if request.method == "POST":
        emp_id = request.form["emp_id"]
        emp_name = request.form.get("emp_name")
        department = request.form["department"]
        education = request.form["education"]
        gender = request.form["gender"]
        age = request.form["age"]

        cursor.execute("SELECT * FROM employee WHERE emp_id=%s", (emp_id,))
        existing = cursor.fetchone()

        if not existing:
            cursor.execute("INSERT INTO employee (emp_id,emp_name,department,education,gender,age) VALUES (%s,%s,%s,%s,%s,%s)",
                           (emp_id,emp_name,department,education,gender,age))
            db.commit()
            success = "Employee added successfully!"
        else:
            error = "Employee ID already exists"

    return render_template("add_employee.html", error=error, success=success)


# ---------------- ADD PERFORMANCE ----------------
@app.route("/add_performance", methods=["GET", "POST"])
def add_performance():
    if "hr_logged_in" not in session:
        return redirect(url_for("login_page"))

    error = None
    success = None

    cursor.execute("SELECT emp_id, emp_name FROM employee")
    employees = cursor.fetchall()
    employees = [{"emp_id": emp["emp_id"], "emp_name": emp["emp_name"]} for emp in employees]

    if request.method == "POST":
        try:
            emp_id = request.form["emp_id"]
            emp_name = request.form["emp_name"]
            no_of_trainings = int(request.form["no_of_trainings"])
            previous_year_rating = int(request.form["previous_year_rating"])
            length_of_service = int(request.form["length_of_service"])
            awards_won = int(request.form["awards_won"])
            avg_training_score = int(request.form["avg_training_score"])

            cursor.execute("SELECT * FROM employee_performance WHERE emp_id=%s", (emp_id,))
            existing = cursor.fetchone()

            if existing:
                error = "Performance details for this employee already exist."
            else:
                cursor.execute("""INSERT INTO employee_performance 
                                  (emp_id, emp_name, no_of_trainings, previous_year_rating, length_of_service, awards_won, avg_training_score)
                                  VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                               (emp_id, emp_name, no_of_trainings, previous_year_rating, length_of_service, awards_won, avg_training_score))
                db.commit()
                success = "Employee performance added successfully!"
        except Exception as e:
            error = f"Error: {str(e)}"

    return render_template("add_performance.html", employees=employees, error=error, success=success)


# ---------------- ABOUT & CONTACT ----------------
@app.route("/about")
def about():
    if "hr_logged_in" not in session:
        return redirect(url_for("login_page"))
    return render_template("about.html")

@app.route("/contact")
def contact():
    if "hr_logged_in" not in session:
        return redirect(url_for("login_page"))
    return render_template("contact.html")

#view employee 
@app.route('/view_employee')
def view_employee():

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
    SELECT e.emp_id, e.emp_name, e.department, e.education, e.gender, e.age,
           p.no_of_trainings, p.previous_year_rating,
           p.length_of_service, p.awards_won, p.avg_training_score
    FROM employee e
    JOIN employee_performance p
    ON e.emp_id = p.emp_id
    """)

    employees = cursor.fetchall()

    return render_template("view_employee.html", employees=employees)

#edit employee
@app.route('/edit_employee/<emp_id>', methods=['GET','POST'])
def edit_employee(emp_id):

    cursor = db.cursor(dictionary=True)

    if request.method == 'POST':

        department = request.form['department']
        education = request.form['education']
        gender = request.form['gender']
        age = request.form['age']

        no_of_trainings = request.form['no_of_trainings']
        previous_year_rating = request.form['previous_year_rating']
        length_of_service = request.form['length_of_service']
        awards_won = request.form['awards_won']
        avg_training_score = request.form['avg_training_score']

        # update employee table
        cursor.execute("""
        UPDATE employee
        SET department=%s, education=%s, gender=%s, age=%s
        WHERE emp_id=%s
        """,(department,education,gender,age,emp_id))

        # update performance table
        cursor.execute("""
        UPDATE employee_performance
        SET no_of_trainings=%s,
            previous_year_rating=%s,
            length_of_service=%s,
            awards_won=%s,
            avg_training_score=%s
        WHERE emp_id=%s
        """,(no_of_trainings,previous_year_rating,length_of_service,
             awards_won,avg_training_score,emp_id))

        db.commit()

        return redirect('/view_employee')


    # fetch employee + performance data
    cursor.execute("""
    SELECT e.emp_id, e.emp_name, e.department, e.education, e.gender, e.age,
           p.no_of_trainings, p.previous_year_rating,
           p.length_of_service, p.awards_won, p.avg_training_score
    FROM employee e
    JOIN employee_performance p
    ON e.emp_id = p.emp_id
    WHERE e.emp_id=%s
    """,(emp_id,))

    employee = cursor.fetchone()

    return render_template("edit_employee.html", employee=employee)


#delete router
@app.route('/delete_employee/<emp_id>')
def delete_employee(emp_id):

    cursor = db.cursor()

    # delete prediction history
    cursor.execute("DELETE FROM prediction_history WHERE emp_id=%s", (emp_id,))

    # delete employee performance
    cursor.execute("DELETE FROM employee_performance WHERE emp_id=%s",(emp_id,))

    # delete employee record
    cursor.execute("DELETE FROM employee WHERE emp_id=%s",(emp_id,))

    db.commit()

    return redirect('/view_employee')

#reports router
@app.route("/reports")
def reports():
    return render_template("report.html")
    

@app.route("/employee_reports")
def employee_reports():
    # Check session
    if "hr_logged_in" not in session:
        return redirect(url_for("login_page"))

    # Get sort value
    sort = request.args.get("sort")

    # JOIN query (IMPORTANT 🔥)
    query = """
    SELECT e.emp_id, e.emp_name, e.department, e.age,
           p.awards_won, p.avg_training_score,
           p.created_at
    FROM employee e
    LEFT JOIN employee_performance p
    ON e.emp_id = p.emp_id
    """

    # Sorting logic
    if sort == "name":
        query += " ORDER BY e.emp_name ASC"
    elif sort == "age":
        query += " ORDER BY e.age ASC"
    elif sort == "department":
        query += " ORDER BY e.department ASC"
    elif sort == "awards":
        query += " ORDER BY p.awards_won DESC"
    elif sort == "training":
        query += " ORDER BY p.avg_training_score DESC"
    elif sort == "latest":
        query += " ORDER BY p.created_at DESC"

    cursor = db.cursor(dictionary=True)
    cursor.execute(query)
    data = cursor.fetchall()

    return render_template(
        "employee_reports.html",
        data=data,
        current_sort=sort
    )

@app.route("/prediction_reports")
def prediction_reports():

    if "hr_logged_in" not in session:
        return redirect(url_for("login_page"))

    filter_type = request.args.get("filter")

    query = """
    SELECT 
        p.emp_id,
        p.emp_name,
        p.prediction,
        p.created_at,
        ep.avg_training_score,
        ep.previous_year_rating
    FROM prediction_history p
    JOIN employee_performance ep 
        ON p.emp_id = ep.emp_id
    """

    
    if filter_type == "promoted":
        query += " WHERE p.prediction = 'Eligible'"
    elif filter_type == "not_promoted":
        query += " WHERE p.prediction = 'Not Eligible'"
    elif filter_type == "latest":
        query += " ORDER BY p.created_at DESC"

    cursor.execute(query)
    data = cursor.fetchall()

    # ADD REASON LOGIC HERE
    for emp in data:
        if emp["prediction"] == "Not Eligible":

            if emp["avg_training_score"] < 50:
                emp["reason"] = "Low Training Performance"

            elif emp["previous_year_rating"] <= 2:
                emp["reason"] = "Low Performance Rating"

            else:
                emp["reason"] = "Overall Improvement Required"

        else:
            emp["reason"] = "Eligible for Promotion"

    return render_template(
        "prediction_reports.html",
        data=data,
        current_filter=filter_type
    )
    
    
# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.pop("hr_logged_in", None)
    return redirect(url_for("login_page"))


# ---------------- NO CACHE ----------------
@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, proxy-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


if __name__ == "__main__":
    app.run(debug=True)