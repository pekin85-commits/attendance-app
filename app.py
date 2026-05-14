from flask import Flask, request, redirect, url_for, render_template_string, Response
from datetime import datetime
import zoneinfo
import random

app = Flask(__name__)

TZ = zoneinfo.ZoneInfo("America/New_York")

current_session = {
    "active": False,
    "code": None,
    "previous_code": None,
    "start_time": None,
    "checkins": [],
    "last_rotation": None
}

def generate_code():
    return str(random.randint(10000, 99999))

@app.route("/")
def dashboard():
    if current_session["active"] and current_session["last_rotation"] is not None:
        now = datetime.now(TZ)
        elapsed = (now - current_session["last_rotation"]).seconds

        if elapsed >= 30:
            current_session["previous_code"] = current_session["code"]
            current_session["code"] = generate_code()
            current_session["last_rotation"] = now

    return render_template_string("""
    <meta http-equiv="refresh" content="5">

    <style>
    body {
        font-family: Arial, sans-serif;
        text-align: center;
        background: linear-gradient(to right, #f5f7fa, #c3cfe2);
    }

    .container {
        margin: 30px auto;
        width: 80%;
    }

    .code {
        font-size: 100px;
        font-weight: bold;
        color: #0078D4;
        margin: 20px;
    }

    .button {
        padding: 15px 30px;
        font-size: 18px;
        border: none;
        border-radius: 10px;
        background-color: #0078D4;
        color: white;
        margin: 10px;
        cursor: pointer;
    }

    .button:hover {
        background-color: #005ea6;
    }

    .end-btn {
        background-color: #d9534f;
    }

    .card {
        background: white;
        padding: 20px;
        margin: 20px auto;
        border-radius: 15px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    }

    .count {
        font-size: 20px;
        margin-top: 10px;
    }
    </style>

    <div class="container">
        <h1>📊 Live Attendance</h1>

        {% if session.active %}
            <div class="card">
                <div class="code">{{ session.code }}</div>
                <p>Started: {{ session.start_time }}</p>

                <form action="/start" method="post" style="display:inline;">
                    <button class="button">🔄 Restart</button>
                </form>

                <form action="/end" method="post" style="display:inline;">
                    <button class="button end-btn">🛑 End Class</button>
                </form>

                <div class="count">
                    ✅ Checked in: {{ session.checkins|length }}
                </div>
            </div>

            <div class="card">
                <h3>Students</h3>
                {% for c in session.checkins %}
                    {{ c["name"] }} -
                    <span style="color:{{ 'red' if c['status']=='Late' else 'green' }}">
                        {{ c["status"] }}
                    </span>
                    <br>
                {% endfor %}
            </div>

            <div class="card">
                <a href="/export">
                    <button class="button">⬇️ Download CSV</button>
                </a>
            </div>

        {% else %}
            <div class="card">
                <h2>No active session</h2>
                <form action="/start" method="post">
                    <button class="button">✅ Start Class</button>
                </form>
            </div>
        {% endif %}
    </div>
    """, session=current_session)

@app.route("/start", methods=["POST"])
def start():
    current_session["active"] = True
    current_session["code"] = generate_code()
    current_session["previous_code"] = None
    current_session["start_time"] = datetime.now(TZ)
    current_session["last_rotation"] = datetime.now(TZ)
    current_session["checkins"] = []
    return redirect(url_for("dashboard"))

@app.route("/end", methods=["POST"])
def end():
    current_session["active"] = False
    return redirect(url_for("dashboard"))

@app.route("/checkin", methods=["GET", "POST"])
def checkin():
    if request.method == "POST":
        name = request.form["name"]
        code = request.form["code"]

        if not current_session["active"]:
            return """
            <h2>⛔ No active class session</h2>
            <p>Please wait for your instructor to start class.</p>
            """

        user_ip = request.remote_addr

        # Duplicate check
        for c in current_session["checkins"]:
            if c["name"] == name or c["ip"] == user_ip:
                return """
                <h2>⚠️ Already checked in</h2>
                <p>You have already submitted attendance.</p>
                """

        # Code validation
        if code != current_session["code"] and code != current_session["previous_code"]:
            return """
            <h2>❌ Invalid code</h2>
            <p>Please check the code and try again.</p>
            <br><a href="/checkin">Try again</a>
            """

        # Proper timezone-aware late calculation
        now = datetime.now(TZ)
        minutes_late = (now - current_session["start_time"]).seconds / 60
        status = "Late" if minutes_late > 10 else "Present"

        current_session["checkins"].append({
            "name": name,
            "status": status,
            "time": now.strftime("%H:%M:%S"),
            "ip": user_ip
        })

        return f"""
        <h2>✅ Check-in successful</h2>
        <p>Status: {status}</p>
        <a href="/checkin">Back</a>
        """

    return """
    <style>
    body {
        font-family: Arial;
        text-align: center;
        padding-top: 50px;
        background-color: #f5f5f5;
    }

    input {
        padding: 12px;
        margin: 10px;
        width: 220px;
        font-size: 16px;
        border-radius: 8px;
        border: 1px solid #ccc;
    }

    button {
        padding: 12px 25px;
        font-size: 16px;
        border-radius: 8px;
        background-color: #0078D4;
        color: white;
        border: none;
    }

    .card {
        background: white;
        padding: 25px;
        border-radius: 12px;
        width: 300px;
        margin: auto;
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    }
    </style>

    <div class="card">
    <h2>✅ Check In</h2>

    <form method="post">
        Email:<br>
        <input name="name" required><br>

        Code:<br>
        <input name="code" required><br><br>

        <button>Submit</button>
    </form>
    </div>
    """

@app.route("/export")
def export():
    def generate():
        data = [["Name", "Status", "Time"]]
        for c in current_session["checkins"]:
            data.append([c["name"], c["status"], c["time"]])

        output = ""
        for row in data:
            output += ",".join(row) + "\n"

        return output

    return Response(
        generate(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=attendance.csv"}
    )

if __name__ == "__main__":
    app.run(debug=True)
