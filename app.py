import os
import json
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps

from keras.models import load_model
from PIL import Image, ImageOps
import numpy as np

app = Flask(__name__)
app.secret_key = 'kunci_rahasia_aman_123'
DB_FILE = 'users.json'

model = load_model("models/keras_Model.h5", compile=False)
class_names = open("models/labels.txt", "r").readlines()

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f: return json.load(f)
    return {"Wahyu": {"password": "B0vv0#1122334455#Mu5t#B0w0", "role": "owner"}}

def save_db(data):
    with open(DB_FILE, 'w') as f: json.dump(data, f, indent=4)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session: return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def owner_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'owner':
            flash("❌ Hanya Owner yang bisa akses!", "error")
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def home(): 
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
@login_required
def predict():
    if 'file' not in request.files:
        return jsonify({'label': 'Tidak ada file', 'tips': ''})
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'label': 'File kosong', 'tips': ''})

    image = Image.open(file).convert("RGB")
    size = (224, 224)
    image = ImageOps.fit(image, size, Image.Resampling.LANCZOS)
    image_array = np.asarray(image)
    normalized_image_array = (image_array.astype(np.float32) / 127.5) - 1
    data = np.ndarray(shape=(1, 224, 224, 3), dtype=np.float32)
    data[0] = normalized_image_array

    pred_data = model.predict(data)
    index = np.argmax(pred_data)
    label = class_names[index][2:].strip()

    tips_sampah = {
        "Organik": "Tips: Jika sudah tidak layak/Sudah menjadi sampah/Kotoran, Sampah ini bisa diolah menjadi kompos. Cukup kumpulkan di lubang biopori atau wadah komposter di rumah agar menjadi pupuk alami.",
        "Anorganik": "Tips: Jika sudah tidak layak/Sudah menjadi sampah, Bersihkan sisa kotoran pada sampah ini, lalu pisahkan berdasarkan jenisnya (plastik/kaca/logam) untuk disetorkan ke Bank Sampah terdekat.",
        "B3": "Tips: Jika benda sudah tidak memiliki penutup, hati-hati! Ini adalah Bahan Berbahaya dan Beracun. Bungkus dengan rapat dan serahkan ke tempat pengumpulan limbah B3 resmi, jangan dicampur dengan sampah biasa."
    }

    tips = tips_sampah.get(label, "Tips: Tetap jaga kebersihan lingkungan ya!")
    
    return jsonify({'label': label, 'tips': tips})

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        users_db = load_db()
        u = users_db.get(request.form.get('username'))
        if u and u['password'] == request.form.get('password'):
            session['user'] = request.form.get('username')
            session['role'] = u['role']
            return redirect(url_for('home'))
        flash("❌ Username/Password salah!", "error")
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        users_db = load_db()
        uname = request.form.get('username')
        if uname in users_db:
            flash(f"⚠️ Nama username <b>{uname}</b> sudah diambil.", "error")
            return redirect(url_for('signup'))
        users_db[uname] = {"password": request.form.get('password'), "role": "user"}
        save_db(users_db)
        flash("✅ Akun berhasil dibuat!", "success")
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/account_settings')
@login_required
def account_settings():
    if session.get('role') == 'owner':
        flash("❌ Owner tidak perlu mengelola akun di sini!", "error")
        return redirect(url_for('owner_panel'))
    return render_template('account_settings.html')

@app.route('/delete-account')
@login_required
def delete_account():
    users_db = load_db()
    uname = session.get('user')
    if uname and uname in users_db and uname != 'Wahyu':
        del users_db[uname]
        save_db(users_db)
    session.clear()
    flash("✅ Akun berhasil dihapus.", "success")
    return redirect(url_for('login'))

@app.route('/owner-panel')
@login_required
@owner_required
def owner_panel(): return render_template('owner_panel.html')

@app.route('/manage-users')
@login_required
@owner_required
def manage_users():
    return render_template('manage_users.html', users=load_db())

@app.route('/delete-all-users')
@login_required
@owner_required
def delete_all_users():
    users_db = load_db()
    new_db = {"Wahyu": users_db.get("Wahyu", {"password": "default", "role": "owner"})}
    save_db(new_db)
    return redirect(url_for('manage_users'))

@app.route('/delete-user/<username>')
@login_required
@owner_required
def delete_user(username):
    users_db = load_db()
    if username in users_db and username != 'Wahyu':
        del users_db[username]
        save_db(users_db)
    return redirect(url_for('manage_users'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__': app.run(debug=True)