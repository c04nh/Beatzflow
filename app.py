from flask import Flask, render_template, request, redirect, url_for, session, flash
from datetime import datetime
import json
import os

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 세션 관리용 비밀키
NOTICE_PATH = 'data/notices.json'

# 관리자 계정 (하드코딩)
users = {
    'admin': {'password': 'admin', 'role': 'admin'},
}

@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

# @app.route('/login', methods=['GET', 'POST'])
# def login():
#     if request.method == 'POST':
#         userid = request.form['username']
#         passwd = request.form['password']
#         if userid == ADMIN_ID and passwd == ADMIN_PW:
#             session['user'] = userid
#             return redirect(url_for('dashboard'))
#         return render_template('login.html', error="아이디 또는 비밀번호가 틀렸습니다.")
#     return render_template('login.html')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        role = request.form.get('role')
        if role == 'admin':
            username = request.form.get('username')
            password = request.form.get('password')
            user = users.get(username)

            if user and user['password'] == password and user['role'] == 'admin':
                session['username'] = username
                session['is_admin'] = True
                return redirect(url_for('dashboard'))
            else:
                flash('관리자 아이디 또는 비밀번호가 틀렸습니다.')
                return redirect(url_for('login'))

        else:  # 일반 멤버는 아이디 비번 없이 바로 로그인 처리 (원하는 방식에 따라 수정 가능)
            session['username'] = 'member_user'  # 여기 멤버 실제 ID를 넣어야 하면 추가 로직 필요
            session['is_admin'] = False
            return redirect(url_for('dashboard'))

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'is_admin' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', user=session['is_admin'])

@app.route('/logout')
def logout():
    session.pop('is_admin', None)
    return redirect(url_for('login'))

def load_data():
    if not os.path.exists("data/members.json"):
        return {"members": []}
    with open("data/members.json", "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open("data/members.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@app.route('/members', methods=['GET', 'POST'])
def manage_members():
    if 'is_admin' not in session:
        return redirect(url_for('login'))

    data = load_data()

    if request.method == 'POST':
        name = request.form['name']
        role = request.form['role']
        new_member = {"name": name, "role": role}
        data['members'].append(new_member)
        save_data(data)
        return redirect(url_for('manage_members'))

    return render_template('members.html', members = sorted(data['members'], key=lambda m: (m['role'] != '주체', m['name'])))

@app.route('/update_members', methods=['POST'])
def update_members():
    with open('data/members.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    members = data.get("members", [])

    for i in range(len(members)):
        name_key = f'name_{i}'
        role_key = f'role_{i}'

        if name_key in request.form and role_key in request.form:
            members[i]['name'] = request.form[name_key]
            members[i]['role'] = request.form[role_key]

    data["members"] = members

    with open('data/members.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    return redirect(url_for('manage_members'))

@app.route('/delete_member/<name>', methods=['POST'])
def delete_member(name):
    with open('data/members.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    data['members'] = [m for m in data['members'] if m['name'] != name]

    for date in data['attendance']:
        del data["attendance"][date][name]
        print(data["attendance"])

    with open('data/members.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    return '', 204  # No content, for fetch

@app.route('/attendance', methods=['GET', 'POST'])
def attendance():
    if 'is_admin' not in session:
        return redirect(url_for('login'))

    data = load_data()
    members = sorted(data['members'], key=lambda m: (m['role'] != '주체', m['name']))
    today = datetime.today().strftime('%Y-%m-%d')
    attendance_data = data.get('attendance', {})

    all_dates = sorted(attendance_data.keys())

    if request.method == 'POST':
        date = request.form['date']
        for member in members:
            status = request.form.get(member['name'])
            if date not in data['attendance']:
                data['attendance'][date] = {}
            data['attendance'][date][member['name']] = status
        save_data(data)
        return redirect(url_for('attendance', success=1))

    return render_template('attendance.html', members=members, today=today, dates=all_dates)


@app.route('/attendance/status')
def attendance_status():
    if 'is_admin' not in session:
        return redirect(url_for('login'))

    with open('data/members.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
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


@app.route('/attendance/edit', methods=['GET', 'POST'])
def attendance_edit():
    with open('data/members.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    attendance_data = data.get("attendance", {})
    member_list = data.get("members", [])
    dates = sorted(attendance_data.keys())

    role_dict = {member['name']: member['role'] for member in member_list}

    names = set()

    # 출결에 등장한 모든 이름 모으기
    for date in dates:
        names.update(attendance_data[date].keys())

    def sort_key(name):
        role_priority = 0 if role_dict.get(name) == '주체' else 1
        return (role_priority, name)

    sorted_names = sorted(names, key=sort_key)

    name_role_list = [(name, role_dict.get(name, "역할없음")) for name in sorted_names]

    if request.method == 'POST':
        # 폼으로부터 수정된 값 받아오기
        for name in names:
            for date in dates:
                key = f"{name}_{date}"
                new_status = request.form.get(key)
                if new_status:
                    if date not in attendance_data:
                        attendance_data[date] = {}
                    attendance_data[date][name] = new_status

        # 수정된 데이터 저장
        data["attendance"] = attendance_data
        with open('data/members.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        return redirect(url_for('attendance_status'))

    return render_template('attendance_edit.html', attendance_data=attendance_data, dates=dates, name_role_list=name_role_list)

def load_notices():
    with open(NOTICE_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_notices(notices):
    with open(NOTICE_PATH, 'w', encoding='utf-8') as f:
        json.dump(notices, f, indent=2, ensure_ascii=False)

@app.route('/notices')
def notice_list():
    notices = load_notices()
    sorted_notices = sorted(notices, key=lambda x: x['created_at'], reverse=True)
    return render_template('notice_list.html', notices=sorted_notices)

@app.route('/notices/<int:notice_id>')
def notice_detail(notice_id):
    notices = load_notices()
    notice = next((n for n in notices if n['id'] == notice_id), None)
    if not notice:
        os.abort(404)
    return render_template('notice_detail.html', notice=notice)

@app.route('/notices/<int:notice_id>/edit', methods=['GET', 'POST'])
def edit_notice(notice_id):
    notices = load_notices()
    notice = next((n for n in notices if n['id'] == notice_id), None)
    if not notice:
        os.abort(404)

    if request.method == 'POST':
        notice['title'] = request.form['title']
        notice['content'] = request.form['content']
        save_notices(notices)
        return redirect(url_for('notice_detail', notice_id=notice_id))

    return render_template('notice_edit.html', notice=notice)

@app.route('/notices/<int:notice_id>/delete', methods=['POST'])
def delete_notice(notice_id):
    notices = load_notices()
    updated_notices = [n for n in notices if n['id'] != notice_id]
    if len(updated_notices) == len(notices):
        os.abort(404)
    save_notices(updated_notices)
    return redirect(url_for('notice_list'))


@app.route('/notices/new', methods=['GET', 'POST'])
def new_notice():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        notices = load_notices()

        # 새 ID는 현재 최대 ID + 1 (혹은 1부터 시작)
        new_id = max([n['id'] for n in notices], default=0) + 1

        new_notice = {
            'id': new_id,
            'title': title,
            'content': content,
            'created_at': datetime.now().isoformat()
        }

        notices.append(new_notice)
        save_notices(notices)
        return redirect(url_for('notice_list'))

    return render_template('notice_new.html')

if __name__ == '__main__':
    app.run(debug=True)