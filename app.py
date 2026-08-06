import os
from datetime import timedelta
from flask import Flask, render_template, request, redirect, url_for, session, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.utils import secure_filename

# تحديد المسارات
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'templates')
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__, template_folder=TEMPLATE_DIR)
app.secret_key = 'easy_simple_school_key_mido_hub'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# 🔐 حفظ الجلسة لمدة 30 يوم من غير ما تخرج الطالب أو المعلم
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

socketio = SocketIO(app, cors_allowed_origins="*")

CLASSES_SCHEDULE = []
ATTACHMENTS = []
HOMEWORKS = []

# المواد الدراسية
SUBJECTS = [
    "اللغة العربية", 
    "اللغة الإنجليزية", 
    "الرياضيات", 
    "العلوم", 
    "الدراسات الاجتماعية", 
    "الفيزياء", 
    "الكيمياء", 
    "الأحياء", 
    "التاريخ", 
    "الجغرافيا"
]

# الصفوف الدراسية
GRADES = [
    "الرابع الابتدائي", 
    "الخامس الابتدائي", 
    "السادس الابتدائي", 
    "الصف الأول الإعدادي", 
    "الصف الثاني الإعدادي", 
    "الصف الثالث الإعدادي", 
    "الصف الأول الثانوي", 
    "الصف الثاني الثانوي", 
    "الصف الثالث الثانوي"
]

@app.route('/')
def home():
    return render_template('home.html')

# الدخول المباشر مع تثبيت الـ Session
@app.route('/login/<role>', methods=['GET', 'POST'])
def login(role):
    if request.method == 'POST':
        session.permanent = True  # 👈 تثبيت الجلسة
        session['user'] = {
            'name': request.form.get('name'),
            'phone': request.form.get('phone'),
            'role': role,
            'subject': request.form.get('subject', ''),
            'grade': request.form.get('grade', '')
        }
        return redirect(url_for('dashboard'))
    role_name = "المعلم" if role == 'teacher' else "الطالب"
    return render_template('login.html', role=role, role_name=role_name, subjects=SUBJECTS, grades=GRADES)

@app.route('/dashboard')
def dashboard():
    user = session.get('user')
    if not user:
        return redirect(url_for('home'))

    if user['role'] == 'student':
        filtered_classes = [c for c in CLASSES_SCHEDULE if c['grade'] == user['grade']]
        filtered_hw = [h for h in HOMEWORKS if h['grade'] == user['grade']]
    else:
        filtered_classes = CLASSES_SCHEDULE
        filtered_hw = HOMEWORKS

    return render_template('dashboard.html', user=user, classes=filtered_classes, homeworks=filtered_hw, grades=GRADES)

@app.route('/add_class', methods=['POST'])
def add_class():
    user = session.get('user')
    if user and user['role'] == 'teacher':
        new_class = {
            'id': len(CLASSES_SCHEDULE) + 1,
            'title': request.form.get('title'),
            'time_str': request.form.get('time_str'),
            'grade': request.form.get('grade'),
            'subject': user['subject'],
            'teacher_name': user['name']
        }
        CLASSES_SCHEDULE.append(new_class)
    return redirect(url_for('dashboard'))

@app.route('/add_homework', methods=['POST'])
def add_homework():
    user = session.get('user')
    if user and user['role'] == 'teacher':
        hw = {
            'id': len(HOMEWORKS) + 1,
            'title': request.form.get('title'),
            'grade': request.form.get('grade'),
            'question': request.form.get('question'),
            'opt1': request.form.get('opt1'),
            'opt2': request.form.get('opt2'),
            'opt3': request.form.get('opt3'),
            'correct': request.form.get('correct')
        }
        HOMEWORKS.append(hw)
    return redirect(url_for('dashboard'))

# رابط الحصة اللحظية
@app.route('/room/<int:room_id>')
def room(room_id):
    user = session.get('user')
    if not user:
        return redirect(url_for('home'))
    return render_template('room.html', room_id=room_id, user=user)

# ==========================================
# ⚡ أحداث Socket.IO للمزامنة اللحظية للسبورة
# ==========================================

@socketio.on('join')
def on_join(data):
    room = str(data.get('room'))
    join_room(room)

@socketio.on('draw_event')
def handle_draw(data):
    room = str(data.get('room'))
    emit('draw_event', data, to=room, include_self=False)

@socketio.on('share_image')
def handle_share_image(data):
    room = str(data.get('room'))
    emit('receive_image', data, to=room, include_self=False)

@socketio.on('clear_canvas')
def handle_clear(data):
    room = str(data.get('room'))
    emit('clear_canvas', to=room, include_self=False)

@socketio.on('toggle_pen')
def handle_toggle_pen(data):
    room = str(data.get('room'))
    emit('toggle_pen_status', data, to=room)

@socketio.on('raise_hand')
def handle_raise_hand(data):
    room = str(data.get('room'))
    emit('new_hand_raised', data, to=room)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    socketio.run(app, host='0.0.0.0', port=port)
