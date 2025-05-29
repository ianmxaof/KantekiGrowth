from flask import Flask, request, redirect
from storage import all_users, set_user

app = Flask(__name__)

@app.route("/admin")
def admin():
    users = all_users()
    html = "<h1>Admin Dashboard</h1><table border='1'><tr><th>User ID</th><th>Tier</th><th>Upgrade</th></tr>"
    for user in users:
        html += f"<tr><td>{user['user_id']}</td><td>{user['tier']}</td>"
        html += f"<td><form method='POST' action='/upgrade'><input type='hidden' name='user_id' value='{user['user_id']}'><select name='tier'><option value='free'>free</option><option value='premium'>premium</option><option value='admin'>admin</option></select><input type='submit' value='Upgrade'></form></td></tr>"
    html += "</table>"
    return html

@app.route("/upgrade", methods=["POST"])
def upgrade():
    user_id = int(request.form["user_id"])
    tier = request.form["tier"]
    set_user(user_id, tier)
    return redirect("/admin")

if __name__ == "__main__":
    app.run(port=5000) 