import os
import uuid
import json
<<<<<<< HEAD
import base64
=======
from datetime import date
>>>>>>> 86c53add6e0b1d04d26fc79ae77ad75faa519e93
from flask import Flask, abort, render_template, request, redirect, url_for, flash, jsonify, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
IS_VERCEL = os.getenv('VERCEL') == '1'
SECRET_KEY = os.getenv('SECRET_KEY')
if IS_VERCEL and not SECRET_KEY:
    raise RuntimeError('Set SECRET_KEY in the Vercel project environment variables.')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')
if IS_VERCEL and not ADMIN_PASSWORD:
    raise RuntimeError('Set ADMIN_PASSWORD in the Vercel project environment variables.')
app.secret_key = SECRET_KEY or 'jobs_secret_key'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_ROOT = (
    os.path.join('/tmp', 'jobs-app-uploads')
    if IS_VERCEL
    else os.path.join(BASE_DIR, 'static', 'uploads')
)

DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASS = os.getenv('DB_PASS', 'postgres')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'jobs_db')

DEFAULT_DB_URI = os.getenv('DATABASE_URL') or os.getenv('DB_URL')
if IS_VERCEL and not DEFAULT_DB_URI:
    raise RuntimeError('Set DATABASE_URL to a hosted PostgreSQL connection string in Vercel.')
if not DEFAULT_DB_URI:
    if any([os.getenv('DB_USER'), os.getenv('DB_PASS'), os.getenv('DB_HOST'), os.getenv('DB_PORT'), os.getenv('DB_NAME')]):
        DEFAULT_DB_URI = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    else:
        DEFAULT_DB_URI = f"sqlite:///{os.path.join(BASE_DIR, 'jobs.db')}"
if DEFAULT_DB_URI.startswith('postgres://'):
    DEFAULT_DB_URI = DEFAULT_DB_URI.replace('postgres://', 'postgresql+psycopg://', 1)
elif DEFAULT_DB_URI.startswith('postgresql://'):
    DEFAULT_DB_URI = DEFAULT_DB_URI.replace('postgresql://', 'postgresql+psycopg://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DEFAULT_DB_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_pre_ping': True}
if DEFAULT_DB_URI.startswith('sqlite'):
    app.config['SQLALCHEMY_ENGINE_OPTIONS'].update(
        {'connect_args': {'check_same_thread': False}}
    )
WORKER_PHOTO_DIR = os.path.join(UPLOAD_ROOT, 'workers')
PORTFOLIO_DIR = os.path.join(UPLOAD_ROOT, 'portfolio')
os.makedirs(WORKER_PHOTO_DIR, exist_ok=True)
os.makedirs(PORTFOLIO_DIR, exist_ok=True)


def uploaded_file_url(folder, filename):
    if IS_VERCEL:
        return url_for('uploaded_file', folder=folder, filename=filename)
    return url_for('static', filename=f'uploads/{folder}/{filename}')


@app.route('/uploads/<folder>/<filename>')
def uploaded_file(folder, filename):
    directories = {'workers': WORKER_PHOTO_DIR, 'portfolio': PORTFOLIO_DIR}
    if folder not in directories:
        abort(404)
    return send_from_directory(directories[folder], filename)


ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'webp', 'gif', 'mp4', 'webm', 'mov'}
VIDEO_EXT = {'mp4', 'webm', 'mov'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB uploads

TRADES = ['Electrician','Mason', 'Plumber', 'Painter', 'Carpenter', 'Interior Decorator', 'AC Installer']

db = SQLAlchemy(app)


@app.context_processor
def inject_user_context():
    return {'is_admin': session.get('is_admin', False)}


@app.before_request
def protect_admin_routes():
    if request.path.startswith('/admin') and request.path not in ['/admin/login', '/admin/logout'] and not session.get('is_admin'):
        flash('Please sign in to access the admin portal.', 'error')
        return redirect(url_for('admin_login'))


# ---------- Models ----------
class Worker(db.Model):
    __tablename__ = 'workers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    trade = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    location = db.Column(db.String(120), nullable=True)
    hourly_rate = db.Column(db.Float, nullable=True, default=0)
    experience_years = db.Column(db.Integer, nullable=False)
    bio = db.Column(db.Text, nullable=True)
    availability = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='Available')
    photo_filename = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    portfolio_images = db.relationship(
        'PortfolioImage', backref='worker', cascade='all, delete-orphan', lazy=True
    )

    @property
    def photo_url(self):
        if self.photo_filename:
            return uploaded_file_url('workers', self.photo_filename)
        return None

    @property
    def initials(self):
        parts = self.name.split()
        return ''.join(p[0] for p in parts[:2]).upper()

    @property
    def availability_list(self):
        try:
            availability = json.loads(self.availability) if self.availability else []
            return availability if isinstance(availability, list) else []
        except (TypeError, ValueError):
            return []


class PortfolioImage(db.Model):
    __tablename__ = 'portfolio_images'
    id = db.Column(db.Integer, primary_key=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('workers.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    caption = db.Column(db.String(150), nullable=True)
    data_url = db.Column(db.Text, nullable=True)

    @property
    def url(self):
        if self.data_url:
            return self.data_url
        return uploaded_file_url('portfolio', self.filename)

    @property
    def file_type(self):
        ext = self.filename.rsplit('.', 1)[1].lower() if '.' in self.filename else ''
        return 'video' if ext in VIDEO_EXT else 'image'


class AdminConfig(db.Model):
    __tablename__ = 'admin_config'
    id = db.Column(db.Integer, primary_key=True)
    password_hash = db.Column(db.String(255), nullable=False)


class Booking(db.Model):
    __tablename__ = 'bookings'
    id = db.Column(db.Integer, primary_key=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('workers.id'), nullable=False)
    client_name = db.Column(db.String(100), nullable=False)
    client_phone = db.Column(db.String(20), nullable=False)
    service_address = db.Column(db.Text, nullable=False)
    booking_date = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='Pending')

    worker = db.relationship('Worker', backref=db.backref('bookings', lazy=True))


# ---------- Helpers ----------
def allowed_file(filename):
    if not filename:
        return False
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT


def save_upload(file_storage, folder):
    if not file_storage or not getattr(file_storage, 'filename', ''):
        return None
    if not allowed_file(file_storage.filename):
        return None
    safe_name = secure_filename(file_storage.filename)
    if '.' not in safe_name:
        return None
    ext = safe_name.rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    file_storage.save(os.path.join(folder, filename))
    return filename


def build_portfolio_media(file_storage):
    if not file_storage or not getattr(file_storage, 'filename', ''):
        return None
    safe_name = secure_filename(file_storage.filename)
    if not allowed_file(safe_name):
        raise ValueError(f"Unsupported portfolio file: {file_storage.filename}")

    extension = safe_name.rsplit('.', 1)[1].lower()
    mime_types = {
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg',
        'webp': 'image/webp',
        'gif': 'image/gif',
        'mp4': 'video/mp4',
        'webm': 'video/webm',
        'mov': 'video/quicktime',
    }
    content = file_storage.read()
    if not content:
        raise ValueError(f"Portfolio file is empty: {file_storage.filename}")
    file_storage.seek(0)
    filename = f"{uuid.uuid4().hex}.{extension}"
    data_url = f"data:{mime_types[extension]};base64,{base64.b64encode(content).decode('ascii')}"
    return {'filename': filename, 'data_url': data_url}


def parse_required_int(value, field_name):
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be a valid whole number.") from None
    if parsed < 0:
        raise ValueError(f"{field_name} must not be negative.")
    return parsed


def delete_file(folder, filename):
    if not filename:
        return
    path = os.path.join(folder, filename)
    if os.path.exists(path):
        os.remove(path)


# ---------- Client routes ----------
@app.route('/')
def client_home():
    trade_filter = request.args.get('trade')
    search_query = request.args.get('q', '').strip()

    query = Worker.query
    if trade_filter and trade_filter != 'All':
        query = query.filter_by(trade=trade_filter)
    if search_query:
        query = query.filter(Worker.name.ilike(f"%{search_query}%"))

    workers = query.order_by(Worker.name).all()
    return render_template(
        'index.html',
        workers=workers,
        selected_trade=trade_filter,
        search_query=search_query,
        trades=TRADES,
    )


@app.route('/book', methods=['POST'])
def create_booking():
<<<<<<< HEAD
    worker_id = request.form.get('worker_id')
    try:
        worker_id_int = int(worker_id) if worker_id not in (None, '') else None
    except (TypeError, ValueError):
        flash('Please select a valid worker.', 'error')
        return redirect(url_for('client_home'))

    if worker_id_int is None or not db.session.get(Worker, worker_id_int):
        flash('Please select a valid worker.', 'error')
        return redirect(url_for('client_home'))

    client_name = (request.form.get('client_name') or '').strip()
    client_phone = (request.form.get('client_phone') or '').strip()
    service_address = (request.form.get('service_address') or '').strip()
    booking_date = (request.form.get('booking_date') or '').strip()

    if not client_name or not client_phone or not service_address or not booking_date:
        flash('Please complete all booking details.', 'error')
        return redirect(url_for('client_home'))

    new_booking = Booking(
        worker_id=worker_id_int,
=======
    worker_id = request.form.get('worker_id', type=int)
    client_name = request.form.get('client_name', '').strip()
    client_phone = request.form.get('client_phone', '').strip()
    service_address = request.form.get('service_address', '').strip()
    booking_date = request.form.get('booking_date', '').strip()
    worker = db.session.get(Worker, worker_id) if worker_id else None
    try:
        date.fromisoformat(booking_date)
    except ValueError:
        booking_date = ''
    if not worker or not client_name or not client_phone or not service_address or not booking_date:
        flash('Please complete all booking details and choose a valid worker.', 'error')
        return redirect(url_for('client_home'))

    new_booking = Booking(
        worker_id=worker.id,
>>>>>>> 86c53add6e0b1d04d26fc79ae77ad75faa519e93
        client_name=client_name,
        client_phone=client_phone,
        service_address=service_address,
        booking_date=booking_date,
    )
    db.session.add(new_booking)
    db.session.commit()
    flash("Your booking request has been submitted. We'll confirm shortly.", "success")
    return redirect(url_for('client_home'))


@app.route('/worker/<int:worker_id>')
def worker_profile(worker_id):
<<<<<<< HEAD
    worker = db.session.get(Worker, worker_id)
    if worker is None:
        abort(404)
=======
    worker = db.get_or_404(Worker, worker_id)
>>>>>>> 86c53add6e0b1d04d26fc79ae77ad75faa519e93
    return render_template('worker_profile.html', worker=worker)


# ---------- Admin routes ----------
def get_admin_config():
    config = AdminConfig.query.first()
    if not config:
        default_password = ADMIN_PASSWORD or 'admin123'
        config = AdminConfig(password_hash=generate_password_hash(default_password))
        db.session.add(config)
        db.session.commit()
    return config


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        password = request.form.get('password', '')
        config = get_admin_config()
        if check_password_hash(config.password_hash, password):
            session['is_admin'] = True
            flash('Welcome back, admin.', 'success')
            return redirect(url_for('admin_dashboard'))
        flash('Invalid admin password.', 'error')
    return render_template('admin/login.html')


@app.route('/admin/change-password', methods=['GET', 'POST'])
def change_password():
    if request.method == 'POST':
        current = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        config = get_admin_config()
        if not check_password_hash(config.password_hash, current):
            flash('Current password is incorrect.', 'error')
        elif not new_password:
            flash('Enter a new password.', 'error')
        elif new_password != confirm_password:
            flash('New passwords do not match.', 'error')
        else:
            config.password_hash = generate_password_hash(new_password)
            db.session.commit()
            flash('Admin password changed successfully.', 'success')
            return redirect(url_for('admin_dashboard'))
    return render_template('admin/change_password.html')


@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    flash('You have been signed out.', 'success')
    return redirect(url_for('client_home'))


@app.route('/admin')
def admin_dashboard():
    workers = Worker.query.order_by(Worker.id.desc()).all()
    bookings = Booking.query.order_by(Booking.id.desc()).all()
    return render_template('admin/dashboard.html', workers=workers, bookings=bookings)


@app.route('/admin/workers/new', methods=['GET', 'POST'])
def add_worker():
    if request.method == 'POST':
<<<<<<< HEAD
        try:
            portfolio_media = [
                media for media in
                (build_portfolio_media(f) for f in request.files.getlist('portfolio_images'))
                if media
            ]
        except ValueError as error:
            flash(str(error), 'error')
            return redirect(url_for('add_worker'))

        try:
            experience_years = parse_required_int(request.form.get('experience_years'), 'Experience years')
        except ValueError as error:
            flash(str(error), 'error')
            return redirect(url_for('add_worker'))

        name = (request.form.get('name') or '').strip()
        trade = (request.form.get('trade') or '').strip()
        phone = (request.form.get('phone') or '').strip()
        if not name or not trade or not phone:
            flash('Name, trade, and phone are required.', 'error')
            return redirect(url_for('add_worker'))
=======
        experience_years = request.form.get('experience_years', type=int)
        name = request.form.get('name', '').strip()
        trade = request.form.get('trade', '').strip()
        phone = request.form.get('phone', '').strip()
        if (
            not name
            or trade not in TRADES
            or not phone
            or experience_years is None
            or experience_years < 0
            or request.form.get('status', 'Available') not in {'Available', 'Booked'}
        ):
            flash('Enter a valid name, trade, phone number, and experience value.', 'error')
            return render_template(
                'admin/worker_form.html',
                worker=None,
                trades=TRADES,
                selected_availability=request.form.getlist('availability'),
            ), 400
>>>>>>> 86c53add6e0b1d04d26fc79ae77ad75faa519e93

        photo_filename = save_upload(request.files.get('photo'), WORKER_PHOTO_DIR)

        worker = Worker(
            name=name,
            trade=trade,
            phone=phone,
<<<<<<< HEAD
            location=(request.form.get('location') or '').strip() or None,
            hourly_rate=0,
            experience_years=experience_years,
            bio=(request.form.get('bio') or '').strip() or None,
=======
            location=request.form.get('location', '').strip(),
            hourly_rate=0,
            experience_years=experience_years,
            bio=request.form.get('bio', '').strip(),
>>>>>>> 86c53add6e0b1d04d26fc79ae77ad75faa519e93
            availability=json.dumps(request.form.getlist('availability')),
            status=request.form.get('status', 'Available'),
            photo_filename=photo_filename,
        )
        db.session.add(worker)
        db.session.flush()  # get worker.id before commit

        for media in portfolio_media:
            db.session.add(PortfolioImage(worker_id=worker.id, **media))

        db.session.commit()
        flash(f"{worker.name} was added to the roster.", "success")
        return redirect(url_for('admin_dashboard'))

    return render_template('admin/worker_form.html', worker=None, trades=TRADES, selected_availability=[])


@app.route('/admin/workers/<int:worker_id>/edit', methods=['GET', 'POST'])
def edit_worker(worker_id):
<<<<<<< HEAD
    worker = db.session.get(Worker, worker_id)
    if worker is None:
        abort(404)

    if request.method == 'POST':
        try:
            portfolio_media = [
                media for media in
                (build_portfolio_media(f) for f in request.files.getlist('portfolio_images'))
                if media
            ]
        except ValueError as error:
            flash(str(error), 'error')
            return redirect(url_for('edit_worker', worker_id=worker.id))

        try:
            experience_years = parse_required_int(request.form.get('experience_years'), 'Experience years')
        except ValueError as error:
            flash(str(error), 'error')
            return redirect(url_for('edit_worker', worker_id=worker.id))

        name = (request.form.get('name') or '').strip()
        trade = (request.form.get('trade') or '').strip()
        phone = (request.form.get('phone') or '').strip()
        if not name or not trade or not phone:
            flash('Name, trade, and phone are required.', 'error')
            return redirect(url_for('edit_worker', worker_id=worker.id))
=======
    worker = db.get_or_404(Worker, worker_id)

    if request.method == 'POST':
        experience_years = request.form.get('experience_years', type=int)
        name = request.form.get('name', '').strip()
        trade = request.form.get('trade', '').strip()
        phone = request.form.get('phone', '').strip()
        if (
            not name
            or trade not in TRADES
            or not phone
            or experience_years is None
            or experience_years < 0
            or request.form.get('status', 'Available') not in {'Available', 'Booked'}
        ):
            flash('Enter a valid name, trade, phone number, and experience value.', 'error')
            return render_template(
                'admin/worker_form.html',
                worker=worker,
                trades=TRADES,
                selected_availability=request.form.getlist('availability'),
            ), 400
>>>>>>> 86c53add6e0b1d04d26fc79ae77ad75faa519e93

        worker.name = name
        worker.trade = trade
        worker.phone = phone
<<<<<<< HEAD
        worker.location = (request.form.get('location') or '').strip() or None
        worker.experience_years = experience_years
        worker.bio = (request.form.get('bio') or '').strip() or None
=======
        worker.location = request.form.get('location', '').strip()
        worker.experience_years = experience_years
        worker.bio = request.form.get('bio', '').strip()
>>>>>>> 86c53add6e0b1d04d26fc79ae77ad75faa519e93
        worker.availability = json.dumps(request.form.getlist('availability'))
        worker.status = request.form.get('status', 'Available')

        new_photo = save_upload(request.files.get('photo'), WORKER_PHOTO_DIR)
        if new_photo:
            delete_file(WORKER_PHOTO_DIR, worker.photo_filename)
            worker.photo_filename = new_photo

        for media in portfolio_media:
            db.session.add(PortfolioImage(worker_id=worker.id, **media))

        db.session.commit()
        flash(f"{worker.name}'s profile was updated.", "success")
        return redirect(url_for('admin_dashboard'))

    try:
        selected_availability = json.loads(worker.availability) if worker.availability else []
    except (TypeError, ValueError):
        selected_availability = []
    return render_template('admin/worker_form.html', worker=worker, trades=TRADES, selected_availability=selected_availability)


@app.route('/admin/workers/<int:worker_id>/delete', methods=['POST'])
def delete_worker(worker_id):
<<<<<<< HEAD
    worker = db.session.get(Worker, worker_id)
    if worker is None:
        abort(404)
=======
    worker = db.get_or_404(Worker, worker_id)
>>>>>>> 86c53add6e0b1d04d26fc79ae77ad75faa519e93
    delete_file(WORKER_PHOTO_DIR, worker.photo_filename)
    for img in worker.portfolio_images:
        if not img.data_url:
            delete_file(PORTFOLIO_DIR, img.filename)
    name = worker.name
    db.session.delete(worker)
    db.session.commit()
    flash(f"{name} was removed from the roster.", "success")
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/portfolio/<int:image_id>/delete', methods=['POST'])
def delete_portfolio_image(image_id):
<<<<<<< HEAD
    image = db.session.get(PortfolioImage, image_id)
    if image is None:
        abort(404)
=======
    image = db.get_or_404(PortfolioImage, image_id)
>>>>>>> 86c53add6e0b1d04d26fc79ae77ad75faa519e93
    worker_id = image.worker_id
    if not image.data_url:
        delete_file(PORTFOLIO_DIR, image.filename)
    db.session.delete(image)
    db.session.commit()
    flash("Portfolio photo removed.", "success")
    return redirect(url_for('edit_worker', worker_id=worker_id))


@app.route('/admin/portfolio/<int:image_id>/edit', methods=['POST'])
def edit_portfolio_image(image_id):
<<<<<<< HEAD
    image = db.session.get(PortfolioImage, image_id)
    if image is None:
        abort(404)
=======
    image = db.get_or_404(PortfolioImage, image_id)
>>>>>>> 86c53add6e0b1d04d26fc79ae77ad75faa519e93
    worker_id = image.worker_id
    caption = request.form.get('caption', '').strip()
    image.caption = caption if caption else None
    db.session.commit()
    flash('Portfolio item updated.', 'success')
    return redirect(url_for('edit_worker', worker_id=worker_id))


@app.route('/admin/workers/<int:worker_id>/upload', methods=['POST'])
def upload_portfolio_items(worker_id):
<<<<<<< HEAD
    worker = db.session.get(Worker, worker_id)
    if worker is None:
        abort(404)
=======
    worker = db.get_or_404(Worker, worker_id)
>>>>>>> 86c53add6e0b1d04d26fc79ae77ad75faa519e93
    files = request.files.getlist('files')
    try:
        portfolio_media = [
            media for media in (build_portfolio_media(f) for f in files) if media
        ]
    except ValueError as error:
        return jsonify({'error': str(error)}), 400

    created = []
    for media in portfolio_media:
        item = PortfolioImage(worker_id=worker.id, **media)
        db.session.add(item)
        db.session.flush()
        created.append({
            'id': item.id,
            'url': item.url,
            'type': item.file_type,
            'caption': item.caption or '',
        })
    db.session.commit()
    return jsonify({'items': created})


@app.route('/admin/booking/<int:booking_id>/confirm', methods=['POST'])
def confirm_booking(booking_id):
<<<<<<< HEAD
    booking = db.session.get(Booking, booking_id)
    if booking is None:
        abort(404)
=======
    booking = db.get_or_404(Booking, booking_id)
>>>>>>> 86c53add6e0b1d04d26fc79ae77ad75faa519e93
    booking.status = 'Confirmed'
    db.session.commit()
    flash(f"Booking #{booking.id} confirmed.", "success")
    return redirect(url_for('admin_dashboard'))


# ---------- JSON API (used by the client-side portfolio modal) ----------
@app.route('/api/worker/<int:worker_id>/portfolio')
def worker_portfolio_json(worker_id):
<<<<<<< HEAD
    worker = db.session.get(Worker, worker_id)
    if worker is None:
        abort(404)
=======
    worker = db.get_or_404(Worker, worker_id)
>>>>>>> 86c53add6e0b1d04d26fc79ae77ad75faa519e93
    return jsonify({
        'name': worker.name,
        'trade': worker.trade,
        'phone': worker.phone,
        'location': worker.location or '',
        'bio': worker.bio or '',
        'availability': worker.availability_list,
        'images': [
            {'url': img.url, 'caption': img.caption or '', 'type': img.file_type}
            for img in worker.portfolio_images
        ],
    })


def ensure_worker_columns():
    with app.app_context():
        inspector = inspect(db.engine)
        if 'workers' not in inspector.get_table_names():
            return
        columns = {column['name'] for column in inspector.get_columns('workers')}
        if 'location' not in columns:
            db.session.execute(text("ALTER TABLE workers ADD COLUMN location VARCHAR(120)"))
        if 'hourly_rate' not in columns:
            db.session.execute(text("ALTER TABLE workers ADD COLUMN hourly_rate REAL DEFAULT 0"))
        db.session.execute(text("UPDATE workers SET hourly_rate = 0 WHERE hourly_rate IS NULL"))
        if 'availability' not in columns:
            db.session.execute(text("ALTER TABLE workers ADD COLUMN availability TEXT"))
        db.session.commit()


def ensure_portfolio_media_column():
    with app.app_context():
        inspector = inspect(db.engine)
        if 'portfolio_images' not in inspector.get_table_names():
            return
        columns = {column['name'] for column in inspector.get_columns('portfolio_images')}
        if 'data_url' not in columns:
            db.session.execute(text("ALTER TABLE portfolio_images ADD COLUMN data_url TEXT"))
            db.session.commit()


def init_db():
    with app.app_context():
        db.create_all()
        ensure_worker_columns()
        ensure_portfolio_media_column()
        get_admin_config()


init_db()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=False)
