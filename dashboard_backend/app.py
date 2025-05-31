from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, Response
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
from flasgger import Swagger
import json
import threading
import time

app = Flask(__name__)
app.secret_key = 'supersecretkey'
DB_PATH = 'dashboard_backend/db.sqlite3'
swagger = Swagger(app)

# --- Notification Queue for SSE ---
notifications = []

def notify(event):
    notifications.append(event)

# --- Database Setup ---
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, is_admin INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS agents (id INTEGER PRIMARY KEY, name TEXT, status TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY, file TEXT, status TEXT, result TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS plugins (id INTEGER PRIMARY KEY, name TEXT, enabled INTEGER)''')
    # Create default admin
    c.execute('INSERT OR IGNORE INTO users (username, password, is_admin) VALUES (?, ?, ?)', ('admin', generate_password_hash('adminpass'), 1))
    conn.commit()
    conn.close()

init_db()

# --- Auth ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login endpoint."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT id, password, is_admin FROM users WHERE username=?', (username,))
        user = c.fetchone()
        conn.close()
        if user and check_password_hash(user[1], password):
            session['user'] = username
            session['is_admin'] = bool(user[2])
            return redirect(url_for('admin_dashboard'))
        flash('Invalid credentials')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# --- Admin Dashboard ---
@app.route('/admin')
def admin_dashboard():
    if 'user' not in session or not session.get('is_admin'):
        return redirect(url_for('login'))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, username, is_admin FROM users')
    users = c.fetchall()
    c.execute('SELECT id, name, status FROM agents')
    agents = c.fetchall()
    c.execute('SELECT id, file, status FROM jobs')
    jobs = c.fetchall()
    c.execute('SELECT id, name, enabled FROM plugins')
    plugins = c.fetchall()
    conn.close()
    return render_template('admin.html', users=users, agents=agents, jobs=jobs, plugins=plugins)

# --- REST API Documentation ---
@app.route('/apidocs')
def apidocs():
    return redirect('/apidocs/')

# --- REST Endpoints ---
@app.route('/api/users', methods=['GET', 'POST', 'DELETE'])
def api_users():
    """User management endpoint.
    ---
    get:
      description: Get all users
      responses:
        200:
          description: List of users
    post:
      description: Add a new user
      parameters:
        - in: body
          name: user
          schema:
            type: object
            properties:
              username:
                type: string
              password:
                type: string
              is_admin:
                type: boolean
      responses:
        200:
          description: User added
    delete:
      description: Delete a user
      parameters:
        - in: query
          name: id
          type: integer
      responses:
        200:
          description: User deleted
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if request.method == 'POST':
        data = request.json
        c.execute('INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)', (data['username'], generate_password_hash(data['password']), int(data.get('is_admin', 0))))
        conn.commit()
        notify({'type': 'info', 'message': f"User {data['username']} added."})
    if request.method == 'DELETE':
        user_id = request.args.get('id')
        c.execute('DELETE FROM users WHERE id=?', (user_id,))
        conn.commit()
        notify({'type': 'warning', 'message': f"User {user_id} deleted."})
    c.execute('SELECT id, username, is_admin FROM users')
    users = [{'id': u[0], 'username': u[1], 'is_admin': bool(u[2])} for u in c.fetchall()]
    conn.close()
    return jsonify(users)

@app.route('/api/agents', methods=['GET', 'POST', 'DELETE'])
def api_agents():
    """Agent management endpoint.
    ---
    get:
      description: Get all agents
      responses:
        200:
          description: List of agents
    post:
      description: Add a new agent
      parameters:
        - in: body
          name: agent
          schema:
            type: object
            properties:
              name:
                type: string
              status:
                type: string
      responses:
        200:
          description: Agent added
    delete:
      description: Delete an agent
      parameters:
        - in: query
          name: id
          type: integer
      responses:
        200:
          description: Agent deleted
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if request.method == 'POST':
        data = request.json
        c.execute('INSERT INTO agents (name, status) VALUES (?, ?)', (data['name'], data.get('status', 'idle')))
        conn.commit()
        notify({'type': 'info', 'message': f"Agent {data['name']} added."})
    if request.method == 'DELETE':
        agent_id = request.args.get('id')
        c.execute('DELETE FROM agents WHERE id=?', (agent_id,))
        conn.commit()
        notify({'type': 'warning', 'message': f"Agent {agent_id} deleted."})
    c.execute('SELECT id, name, status FROM agents')
    agents = [{'id': a[0], 'name': a[1], 'status': a[2]} for a in c.fetchall()]
    conn.close()
    return jsonify(agents)

@app.route('/api/jobs', methods=['GET', 'POST', 'DELETE'])
def api_jobs():
    """Job management endpoint.
    ---
    get:
      description: Get all jobs
      responses:
        200:
          description: List of jobs
    post:
      description: Add a new job
      parameters:
        - in: body
          name: job
          schema:
            type: object
            properties:
              file:
                type: string
              status:
                type: string
              result:
                type: string
      responses:
        200:
          description: Job added
    delete:
      description: Delete a job
      parameters:
        - in: query
          name: id
          type: integer
      responses:
        200:
          description: Job deleted
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if request.method == 'POST':
        data = request.json
        c.execute('INSERT INTO jobs (file, status, result) VALUES (?, ?, ?)', (data['file'], data.get('status', 'pending'), data.get('result', '')))
        conn.commit()
        notify({'type': 'success', 'message': f"Job for {data['file']} added."})
    if request.method == 'DELETE':
        job_id = request.args.get('id')
        c.execute('DELETE FROM jobs WHERE id=?', (job_id,))
        conn.commit()
        notify({'type': 'warning', 'message': f"Job {job_id} deleted."})
    c.execute('SELECT id, file, status, result FROM jobs')
    jobs = [{'id': j[0], 'file': j[1], 'status': j[2], 'result': j[3]} for j in c.fetchall()]
    conn.close()
    return jsonify(jobs)

@app.route('/api/plugins', methods=['GET', 'POST', 'DELETE'])
def api_plugins():
    """Plugin management endpoint.
    ---
    get:
      description: Get all plugins
      responses:
        200:
          description: List of plugins
    post:
      description: Add a new plugin
      parameters:
        - in: body
          name: plugin
          schema:
            type: object
            properties:
              name:
                type: string
              enabled:
                type: boolean
      responses:
        200:
          description: Plugin added
    delete:
      description: Delete a plugin
      parameters:
        - in: query
          name: id
          type: integer
      responses:
        200:
          description: Plugin deleted
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if request.method == 'POST':
        data = request.json
        c.execute('INSERT INTO plugins (name, enabled) VALUES (?, ?)', (data['name'], int(data.get('enabled', 1))))
        conn.commit()
        notify({'type': 'info', 'message': f"Plugin {data['name']} added."})
    if request.method == 'DELETE':
        plugin_id = request.args.get('id')
        c.execute('DELETE FROM plugins WHERE id=?', (plugin_id,))
        conn.commit()
        notify({'type': 'warning', 'message': f"Plugin {plugin_id} deleted."})
    c.execute('SELECT id, name, enabled FROM plugins')
    plugins = [{'id': p[0], 'name': p[1], 'enabled': bool(p[2])} for p in c.fetchall()]
    conn.close()
    return jsonify(plugins)

# --- Toast Notification Endpoint (for JS polling) ---
@app.route('/api/toasts')
def api_toasts():
    # Return and clear notifications
    global notifications
    toasts = notifications[:]
    notifications.clear()
    return jsonify(toasts)

# --- SSE Endpoint for Instant Notifications ---
@app.route('/api/stream')
def stream():
    def event_stream():
        last_idx = 0
        while True:
            if len(notifications) > last_idx:
                for event in notifications[last_idx:]:
                    yield f'data: {json.dumps(event)}\n\n'
                last_idx = len(notifications)
            time.sleep(1)
    return Response(event_stream(), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(debug=True, port=5000) 