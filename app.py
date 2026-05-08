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

    <h1>Attendance Dashboard</h1>

    {% if session.active %}
        <h2 style="font-size:60px;">{{ session.code }}</h2>
        <p>Started: {{ session.start_time }}</p>

        <form action="/start" method="post">
            <button>Start Class</button>
        </form>

        <form action="/end" method="post">
            <button>End Class</button>
        </form>

        <h3>Check-ins:</h3>
        {% for c in session.checkins %}
            {{ c["name"] }} - {{ c["status"] }}<br>
        {% endfor %}
    {% else %}
        <form action="/start" method="post">
            <button>Start Class</button>
        </form>
    {% endif %}
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
    <h2>Check In</h2>
    <form method="post">
        Name:<br>
        <input name="name"><br>
        Code:<br>
        <input name="code"><br><br>
        <button>Submit</button>
    </form>
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
``