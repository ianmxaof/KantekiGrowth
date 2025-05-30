from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, Response
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
from flasgger import Swagger
import json
import threading
import time
from flask_cors import CORS
from datetime import datetime, timedelta
from tinydb import TinyDB, Query

app = Flask(__name__)
app.secret_key = 'supersecretkey'
DB_PATH = 'db.sqlite3'
swagger = Swagger(app)
CORS(app)
USERS_DB = TinyDB('users.json')
ADMIN_COMMANDS_DB = TinyDB('admin_commands.json')

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
        c.execute('INSERT INTO jobs (file, status, result) VALUES (?, ?, ?)', (data['file'], data['status'], data['result']))
        conn.commit()
        notify({'type': 'info', 'message': f"Job {data['file']} added."})
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
        c.execute('INSERT INTO plugins (name, enabled) VALUES (?, ?)', (data['name'], int(data['enabled'])))
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

@app.route('/api/jobs/status', methods=['GET'])
def api_jobs_status():
    """Job status endpoint.
    ---
    get:
      description: Get job status
      parameters:
        - in: query
          name: id
          type: integer
      responses:
        200:
          description: Job status
    """
    job_id = request.args.get('id')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT status FROM jobs WHERE id=?', (job_id,))
    status = c.fetchone()
    conn.close()
    return jsonify({'status': status[0]})

@app.route('/api/jobs/result', methods=['GET'])
def api_jobs_result():
    """Job result endpoint.
    ---
    get:
      description: Get job result
      parameters:
        - in: query
          name: id
          type: integer
      responses:
        200:
          description: Job result
    """
    job_id = request.args.get('id')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT result FROM jobs WHERE id=?', (job_id,))
    result = c.fetchone()
    conn.close()
    return jsonify({'result': result[0]})

@app.route('/api/jobs/status_2', methods=['GET'])
def api_jobs_status_2():
    """Job status endpoint.
    ---
    get:
      description: Get job status
      parameters:
        - in: query
          name: id
          type: integer
      responses:
        200:
          description: Job status
    """
    job_id = request.args.get('id')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT status FROM jobs WHERE id=?', (job_id,))
    status = c.fetchone()
    conn.close()
    return jsonify({'status': status[0]})

@app.route('/api/jobs/result_2', methods=['GET'])
def api_jobs_result_2():
    """Job result endpoint.
    ---
    get:
      description: Get job result
      parameters:
        - in: query
          name: id
          type: integer
      responses:
        200:
          description: Job result
    """
    job_id = request.args.get('id')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT result FROM jobs WHERE id=?', (job_id,))
    result = c.fetchone()
    conn.close()
    return jsonify({'result': result[0]})

@app.route('/api/jobs/status_3', methods=['GET'])
def api_jobs_status_3():
    """Job status endpoint.
    ---
    get:
      description: Get job status
      parameters:
        - in: query
          name: id
          type: integer
      responses:
        200:
          description: Job status
    """
    job_id = request.args.get('id')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT status FROM jobs WHERE id=?', (job_id,))
    status = c.fetchone()
    conn.close()
    return jsonify({'status': status[0]})

@app.route('/api/jobs/result_3', methods=['GET'])
def api_jobs_result_3():
    """Job result endpoint.
    ---
    get:
      description: Get job result
      parameters:
        - in: query
          name: id
          type: integer
      responses:
        200:
          description: Job result
    """
    job_id = request.args.get('id')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT result FROM jobs WHERE id=?', (job_id,))
    result = c.fetchone()
    conn.close()
    return jsonify({'result': result[0]})

@app.route('/api/jobs/status_4', methods=['GET'])
def api_jobs_status_4():
    """Job status endpoint.
    ---
    get:
      description: Get job status
      parameters:
        - in: query
          name: id
          type: integer
      responses:
        200:
          description: Job status
    """
    job_id = request.args.get('id')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT status FROM jobs WHERE id=?', (job_id,))
    status = c.fetchone()
    conn.close()
    return jsonify({'status': status[0]})

@app.route('/api/jobs/result_4', methods=['GET'])
def api_jobs_result_4():
    """Job result endpoint.
    ---
    get:
      description: Get job result
      parameters:
        - in: query
          name: id
          type: integer
      responses:
        200:
          description: Job result
    """
    job_id = request.args.get('id')
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT result FROM jobs WHERE id=?', (job_id,))
    result = c.fetchone()
    conn.close()
    return jsonify({'result': result[0]})

@app.route('/api/referrals/leaderboard')
def api_referrals_leaderboard():
    users = USERS_DB.all()
    leaderboard = sorted([
        {'user_id': u['user_id'], 'referral_count': u.get('referral_count', 0)}
        for u in users if u.get('referral_count', 0) > 0
    ], key=lambda x: x['referral_count'], reverse=True)[:10]
    return jsonify({'leaderboard': leaderboard})

@app.route('/api/referrals/analytics')
def api_referrals_analytics():
    users = USERS_DB.all()
    total_referrals = sum(u.get('referral_count', 0) for u in users)
    total_upgrades = sum(1 for u in users if u.get('tier', 'basic') in ['premium', 'elite'])
    total_users = len(users)
    conversion_rate = (total_upgrades / total_users) * 100 if total_users else 0
    return jsonify({
        'total_referrals': total_referrals,
        'total_upgrades': total_upgrades,
        'total_users': total_users,
        'conversion_rate': conversion_rate
    })

@app.route('/api/bot/stats')
def api_bot_stats():
    users = USERS_DB.all()
    now = datetime.utcnow()
    active_24h = sum(1 for u in users if 'last_active' in u and datetime.fromisoformat(u['last_active']) > now - timedelta(days=1))
    total_users = len(users)
    total_payments = sum(u.get('payments', 0) for u in users)
    total_upgrades = sum(1 for u in users if u.get('tier', 'basic') in ['premium', 'elite'])
    return jsonify({
        'total_users': total_users,
        'active_24h': active_24h,
        'total_payments': total_payments,
        'total_upgrades': total_upgrades
    })

@app.route('/api/users', methods=['GET'])
def api_list_users():
    users = USERS_DB.all()
    return jsonify({'users': users})

@app.route('/api/users/upgrade', methods=['POST'])
def api_upgrade_user():
    data = request.json
    user_id = data.get('user_id')
    new_tier = data.get('new_tier')
    if not user_id or not new_tier:
        return jsonify({'error': 'user_id and new_tier required'}), 400
    ADMIN_COMMANDS_DB.insert({'type': 'upgrade', 'user_id': user_id, 'new_tier': new_tier, 'status': 'pending'})
    return jsonify({'status': 'queued'})

@app.route('/api/users/ban', methods=['POST'])
def api_ban_user():
    data = request.json
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'error': 'user_id required'}), 400
    ADMIN_COMMANDS_DB.insert({'type': 'ban', 'user_id': user_id, 'status': 'pending'})
    return jsonify({'status': 'queued'})

@app.route('/api/users/message', methods=['POST'])
def api_message_user():
    data = request.json
    user_id = data.get('user_id')
    message = data.get('message')
    if not user_id or not message:
        return jsonify({'error': 'user_id and message required'}), 400
    ADMIN_COMMANDS_DB.insert({'type': 'message', 'user_id': user_id, 'message': message, 'status': 'pending'})
    return jsonify({'status': 'queued'})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True) 