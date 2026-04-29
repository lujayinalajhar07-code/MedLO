from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'medluj_secret_lujayn_2024')

# ===== Users (single manual login) =====
USERS = {
    'عبادة': {
        'password_hash': generate_password_hash('1234'),
        'display_name': 'د. عبادة',
        'avatar': '🩺'
    }
}

# ===== Notes storage =====
NOTE_FILE_PATH = os.path.join(app.root_path, 'user_notes.txt')
MAX_NOTES_CHARS = 20000


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user' not in session:
            # إذا كان الطلب من الواجهة كـ API، نرجع رسالة خطأ بدلاً من التوجيه لصفحة تسجيل الدخول
            if request.path.startswith('/api/'):
                return jsonify({'success': False, 'message': 'انتهت الجلسة، يرجى إعادة تسجيل الدخول.'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated


def _sanitize_notes(notes_text: str) -> str:
    safe_notes = (notes_text or '').replace('\r', '\n').strip()
    if len(safe_notes) > MAX_NOTES_CHARS:
        safe_notes = safe_notes[:MAX_NOTES_CHARS] + '\n…(تم اختصار النص)'
    return safe_notes


def write_user_notes_to_file(username: str, notes_text: str) -> None:
    safe_username = (username or 'user').replace('\n', ' ').replace('\r', ' ')
    safe_notes = _sanitize_notes(notes_text)

    timestamp = datetime.utcnow().isoformat(timespec='seconds') + 'Z'
    header = f'==== {timestamp} | {safe_username} ====\n'
    with open(NOTE_FILE_PATH, 'a', encoding='utf-8') as f:
        f.write(header)
        f.write(safe_notes)
        f.write('\n\n') # إضافة مسافة إضافية بين الملاحظات لترتيبها


def read_user_notes_from_file() -> str:
    if not os.path.exists(NOTE_FILE_PATH):
        return ''
    with open(NOTE_FILE_PATH, 'r', encoding='utf-8') as f:
        return f.read().strip()


@app.route('/')
@login_required
def index():
    return render_template('index.html', user=session['user'])


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({'success': False, 'message': 'اسم المستخدم أو كلمة المرور غير صحيحة 💔'})

        username = (data.get('username') or '').strip()
        password = (data.get('password') or '').strip()

        user = USERS.get(username)
        ok = False
        if user:
            ok = check_password_hash(user['password_hash'], password)

        if ok:
            session['user'] = {
                'username': username,
                'display_name': user['display_name'],
                'avatar': user['avatar']
            }
            return jsonify({'success': True, 'redirect': '/'})

        return jsonify({'success': False, 'message': 'اسم المستخدم أو كلمة المرور غير صحيحة 💔'})

    if 'user' in session:
        return redirect(url_for('index'))
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


@app.route('/api/user')
@login_required
def get_user():
    return jsonify(session['user'])


@app.route('/api/save-notes', methods=['POST'])
@login_required
def save_notes():
    data = request.get_json(silent=True)
    # استخدام force=True لضمان قراءة البيانات حتى لو نسينا إضافة Content-Type في الجافاسكربت
    data = request.get_json(silent=True, force=True)
    if not data: # محاولة قراءتها كبيانات نموذج (Form Data) إذا فشل قراءتها كـ JSON
        data = request.form.to_dict()
        
    if not isinstance(data, dict):
        return jsonify({'success': False, 'message': 'Invalid payload'}), 400

    notes = data.get('notes', '')
    # قراءة الرسالة سواء تم تسميتها notes أو note في الجافاسكربت
    notes = data.get('notes') or data.get('note') or ''
    if not isinstance(notes, str):
        return jsonify({'success': False, 'message': 'Notes must be a string'}), 400

    username = session['user']['username']
    write_user_notes_to_file(username=username, notes_text=notes)
    return jsonify({'success': True})
    try:
        write_user_notes_to_file(username=username, notes_text=notes)
        return jsonify({'success': True})
    except Exception as e:
        # إذا فشل الحفظ بسبب مشكلة في الملفات، سيرسل لك السيرفر سبب المشكلة بدلاً من التعطل
        return jsonify({'success': False, 'message': f'خطأ أثناء الحفظ: {str(e)}'}), 500


@app.route('/api/notes', methods=['GET'])
@login_required
def get_notes():
    return jsonify({'notes': read_user_notes_from_file()})


if __name__ == '__main__':
    app.run(debug=True, port=5000)
