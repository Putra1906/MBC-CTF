from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3, json, os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'rahasia-super-aman'
DB_NAME = 'leaderboard.db'

USERS = {
    'caas1': {'password': '123', 'name': 'CAAS 1', 'role': 'user'},
    'caas2': {'password': '123', 'name': 'CAAS 2', 'role': 'user'},
    'admin': {'password': 'capybarasolid2425', 'name': 'CAPYBARA ADMIN', 'role': 'admin'}
}

CORRECT_FLAGS = {
    'flag1': '192.168.1.10',
    'flag2': '5',
    'flag3': 'nmap',
    'flag4': '10.251.96.4',
    'flag5': '192.168.1.15',
    'flag6': 'root',
    'flag7': '14:35',
    'flag8': 'ya',
    'flag9': 'backdoor.php',
    'flag10': 'abc123def456ghi789xyz000'
}

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS leaderboard (
                username TEXT PRIMARY KEY,
                name TEXT,
                score INTEGER DEFAULT 0,
                last_submit TEXT,
                answers TEXT
            )
        ''')

@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = USERS.get(request.form['username'])
        if user and user['password'] == request.form['password']:
            session['username'] = request.form['username']
            session['name'] = user['name']
            session['role'] = user['role']
            return redirect(url_for('flags'))
        return render_template('login.html', error='Login gagal')
    return render_template('login.html')

@app.route('/flags')
def flags():
    if 'username' not in session:
        return redirect(url_for('login'))
    return render_template('flags.html', name=session['name'])

@app.route('/question/<int:number>', methods=['GET', 'POST'])
def question(number):
    if 'username' not in session:
        return redirect(url_for('login'))

    questions = [
        "IP mana yang bertanggung jawab melakukan aktivitas pemindaian port?",
        "Berapa jumlah port terbuka yang terdeteksi?",
        "Apa nama tools yang digunakan untuk scanning?",
        "IP mana yang bertanggung jawab melakukan aktivitas pemindaian port?",
        "IP mana yang mencoba login SSH berulang kali?",
        "Apa username yang digunakan untuk brute force SSH?",
        "Waktu (timestamp) serangan terjadi pada jam berapa?",
        "Apakah ada file mencurigakan yang di-upload? (jawab: ya/tidak)",
        "Apa nama file mencurigakan tersebut?",
        "Apa hash SHA256 dari file mencurigakan?"
    ]

    placeholders = {
        1: "Format: XXX.XXX.X.X (contoh: 192.168.1.10)",
        2: "Contoh: 5",
        3: "Contoh: nmap",
        4: "Format: XXX.XXX.X.X",
        5: "Format: XXX.XXX.X.X",
        6: "Contoh: root",
        7: "Format: HH:MM (contoh: 14:35)",
        8: "Jawaban: ya / tidak",
        9: "Contoh: backdoor.php",
        10: "Contoh: hash SHA256 (64 karakter)"
    }

    question_text = questions[number - 1]
    placeholder = placeholders.get(number, "Masukkan jawaban")
    flag_key = f"flag{number}"

    feedback = None
    correct = False

    if request.method == 'POST':
        user_flag = request.form['flag'].strip()
        correct_flag = CORRECT_FLAGS[flag_key]

        if user_flag == correct_flag:
            correct = True
            feedback = '✅ Jawaban benar! +10 poin'
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            with sqlite3.connect(DB_NAME) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT score, answers FROM leaderboard WHERE username = ?", (session['username'],))
                row = cursor.fetchone()

                if row:
                    score = row[0]
                    answers = json.loads(row[1]) if row[1] else {}
                    if flag_key not in answers or answers[flag_key] != correct_flag:
                        score += 10
                        answers[flag_key] = user_flag
                        cursor.execute("""
                            UPDATE leaderboard
                            SET score = ?, last_submit = ?, answers = ?
                            WHERE username = ?
                        """, (score, timestamp, json.dumps(answers), session['username']))
                else:
                    answers = {flag_key: user_flag}
                    cursor.execute("""
                        INSERT INTO leaderboard (username, name, score, last_submit, answers)
                        VALUES (?, ?, ?, ?, ?)
                    """, (session['username'], session['name'], 10, timestamp, json.dumps(answers)))
        else:
            feedback = '❌ Jawaban salah. Coba lagi!'

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT score FROM leaderboard WHERE username = ?", (session['username'],))
        row = cursor.fetchone()
        current_score = row[0] if row else 0

        cursor.execute("SELECT username FROM leaderboard ORDER BY score DESC, last_submit ASC")
        all_users = [r[0] for r in cursor.fetchall()]
        rank = all_users.index(session['username']) + 1 if session['username'] in all_users else '-'

    return render_template(
        'question.html',
        number=number,
        question_text=question_text,
        feedback=feedback,
        correct=correct,
        current_score=current_score,
        rank=rank,
        name=session['name'],
        placeholder=placeholder
    )


@app.route('/leaderboard')
def leaderboard():
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name, score, last_submit FROM leaderboard ORDER BY score DESC, last_submit ASC")
        data = cursor.fetchall()
    return render_template('leaderboard.html', data=data)

@app.route('/admin/responses')
def view_responses():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username, name, score, last_submit, answers FROM leaderboard ORDER BY last_submit DESC")
        responses = cursor.fetchall()
    return render_template('admin_responses.html', responses=responses)

@app.route('/reset_leaderboard')
def reset_leaderboard():
    if session.get('role') != 'admin':
        return redirect(url_for('login'))
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("DELETE FROM leaderboard")
    return redirect(url_for('leaderboard'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    if not os.path.exists(DB_NAME):
        init_db()
    app.run(debug=True)
