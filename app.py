from flask import Flask, render_template, request, redirect, url_for, session
from datetime import datetime
import json
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 세션 관리용 비밀키

# 관리자 계정 (하드코딩)
ADMIN_ID = "admin"
ADMIN_PW = "admin"

@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        userid = request.form['username']
        passwd = request.form['password']
        if userid == ADMIN_ID and passwd == ADMIN_PW:
            session['user'] = userid
            return redirect(url_for('dashboard'))
        return render_template('login.html', error="아이디 또는 비밀번호가 틀렸습니다.")
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', user=session['user'])

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('login'))

def load_data():
    if not os.path.exists("data.json"):
        return {"members": []}
    with open("data.json", "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.route('/members', methods=['GET', 'POST'])
def manage_members():
    if 'user' not in session:
        return redirect(url_for('login'))

    data = load_data()

    if request.method == 'POST':
        name = request.form['name']
        role = request.form['role']
        new_member = {"name": name, "role": role}
        data['members'].append(new_member)
        save_data(data)
        return redirect(url_for('manage_members'))

    return render_template('members.html', members=data['members'])

@app.route('/attendance', methods=['GET', 'POST'])
def attendance():
    if 'user' not in session:
        return redirect(url_for('login'))

    data = load_data()
    members = sorted(data['members'], key=lambda m: (m['role'] != '주체', m['name']))
    today = datetime.today().strftime('%Y-%m-%d')

    if request.method == 'POST':
        date = request.form['date']
        for member in members:
            status = request.form.get(member['name'])
            if date not in data['attendance']:
                data['attendance'][date] = {}
            data['attendance'][date][member['name']] = status
        save_data(data)
        return redirect(url_for('attendance'))

    return render_template('attendance.html', members=members, today=today)


@app.route('/attendance/status')
def attendance_status():
    if 'user' not in session:
        return redirect(url_for('login'))

    data = load_data()
    members = sorted(data['members'], key=lambda m: (m['role'] != '주체', m['name']))
    attendance_data = data.get('attendance', {})

    # 날짜 정렬
    all_dates = sorted(attendance_data.keys())

    # 출결표 만들기: {이름: [출결상태1, 출결상태2, ...]}
    table = {}
    for member in members:
        row = []
        for date in all_dates:
            status = attendance_data.get(date, {}).get(member['name'], '')
            row.append(status)
        table[member['name']+'('+member['role']+')'] = row

    return render_template('attendance_status.html', dates=all_dates, table=table)


if __name__ == '__main__':
    app.run(debug=True)