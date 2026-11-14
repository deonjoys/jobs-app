import os
import uuid
import json
from datetime import date
from flask import Flask, abort, render_template, request, redirect, url_for, flash, jsonify, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
IS_VERCEL = os.getenv('VERCEL') == '1'
IS_PRODUCTION = IS_VERCEL or os.getenv('APP_ENV') == 'production'
SECRET_KEY = os.getenv('SECRET_KEY')
if IS_PRODUCTION and not SECRET_KEY:
    raise RuntimeError('Set SECRET_KEY in the production environment variables.')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')
if IS_PRODUCTION and not ADMIN_PASSWORD:
    raise RuntimeError('Set ADMIN_PASSWORD in the production environment variables.')
app.secret_key = SECRET_KEY or 'jobs_secret_key'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_ROOT = (
    os.getenv('UPLOAD_DIR')
    or (
        os.path.join('/tmp', 'jobs-app-uploads')
        if IS_VERCEL
        else os.path.join(BASE_DIR, 'static', 'uploads')
    )
)

DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASS = os.getenv('DB_PASS', 'postgres')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'jobs_db')

DEFAULT_DB_URI = os.getenv('DATABASE_URL') or os.getenv('DB_URL')
if IS_PRODUCTION and not DEFAULT_DB_URI:
    raise RuntimeError('Set DATABASE_URL to a hosted database connection string.')
if not DEFAULT_DB_URI:
    if any(os.getenv(key) for key in ('DB_USER', 'DB_PASS', 'DB_HOST', 'DB_PORT', 'DB_NAME')):
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
    return url_for('uploaded_file', folder=folder, filename=filename)


@app.route('/uploads/<folder>/<filename>')
def uploaded_file(folder, filename):
    directories = {'workers': WORKER_PHOTO_DIR, 'portfolio': PORTFOLIO_DIR}
    if folder not in directories:
        abort(404)
    return send_from_directory(directories[folder], filename)


ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'webp', 'gif', 'mp4', 'webm', 'mov'}
VIDEO_EXT = {'mp4', 'webm', 'mov'}
VIDEO_MIME_TYPES = {
    'mp4': 'video/mp4',
    'webm': 'video/webm',
    'mov': 'video/quicktime',
}
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024 * 1024  # 64MB uploads

TRADES = ['Electrician','Mason', 'Plumber', 'Painter', 'Carpenter', 'Interior Decorator', 'AC Installer']
AVAILABILITY_LABELS = {
    'Small jobs': 'Quick job',
    'Big contracts': 'Full contract',
}

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
    def phone_call_url(self):
        digits = ''.join(character for character in self.phone if character.isdigit())
        if not digits:
            return None
        prefix = '+' if self.phone.strip().startswith('+') else ''
        return f'tel:{prefix}{digits}'

    @property
    def initials(self):
        parts = self.name.split()
        return ''.join(p[0] for p in parts[:2]).upper()

    @property
    def availability_list(self):
        try:
            availability = json.loads(self.availability) if self.availability else []
            if not isinstance(availability, list):
                return []
            return [AVAILABILITY_LABELS.get(item, item) for item in availability]
        except (TypeError, ValueError):
            return []


class PortfolioImage(db.Model):
    __tablename__ = 'portfolio_images'
    id = db.Column(db.Integer, primary_key=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('workers.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    thumbnail_filename = db.Column(db.String(255), nullable=True)
    caption = db.Column(db.String(150), nullable=True)

    @property
    def url(self):
        return uploaded_file_url('portfolio', self.filename)

    @property
    def thumbnail_url(self):
        if self.thumbnail_filename:
            return uploaded_file_url('portfolio', self.thumbnail_filename)
        return None

    @property
    def file_type(self):
        ext = self.filename.rsplit('.', 1)[1].lower() if '.' in self.filename else ''
        return 'video' if ext in VIDEO_EXT else 'image'

    @property
    def mime_type(self):
        ext = self.filename.rsplit('.', 1)[1].lower() if '.' in self.filename else ''
        return VIDEO_MIME_TYPES.get(ext, 'application/octet-stream')


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
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT


def save_upload(file_storage, folder):
    if not file_storage or file_storage.filename == '':
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


def save_portfolio_thumbnail(file_storage):
    if not file_storage or not file_storage.filename:
        return None
    if file_storage.filename.rsplit('.', 1)[-1].lower() not in {'jpg', 'jpeg', 'png', 'webp'}:
        return None
    return save_upload(file_storage, PORTFOLIO_DIR)


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
    worker = db.get_or_404(Worker, worker_id)
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

        photo_filename = save_upload(request.files.get('photo'), WORKER_PHOTO_DIR)

        worker = Worker(
            name=name,
            trade=trade,
            phone=phone,
            location=request.form.get('location', '').strip(),
            hourly_rate=0,
            experience_years=experience_years,
            bio=request.form.get('bio', '').strip(),
            availability=json.dumps(request.form.getlist('availability')),
            status=request.form.get('status', 'Available'),
            photo_filename=photo_filename,
        )
        db.session.add(worker)
        db.session.flush()  # get worker.id before commit

        for index, f in enumerate(request.files.getlist('portfolio_images')):
            fname = save_upload(f, PORTFOLIO_DIR)
            if fname:
                thumbnail = (
                    save_portfolio_thumbnail(request.files.get(f'portfolio_thumbnail_{index}'))
                    if fname.rsplit('.', 1)[-1].lower() in VIDEO_EXT
                    else None
                )
                db.session.add(
                    PortfolioImage(
                        worker_id=worker.id,
                        filename=fname,
                        thumbnail_filename=thumbnail,
                    )
                )

        db.session.commit()
        flash(f"{worker.name} was added to the roster.", "success")
        return redirect(url_for('admin_dashboard'))

    return render_template('admin/worker_form.html', worker=None, trades=TRADES, selected_availability=[])


@app.route('/admin/workers/<int:worker_id>/edit', methods=['GET', 'POST'])
def edit_worker(worker_id):
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

        worker.name = name
        worker.trade = trade
        worker.phone = phone
        worker.location = request.form.get('location', '').strip()
        worker.experience_years = experience_years
        worker.bio = request.form.get('bio', '').strip()
        worker.availability = json.dumps(request.form.getlist('availability'))
        worker.status = request.form.get('status', 'Available')
        for image in worker.portfolio_images:
            caption = request.form.get(f'portfolio_caption_{image.id}', '').strip()
            image.caption = caption or None

        new_photo = save_upload(request.files.get('photo'), WORKER_PHOTO_DIR)
        if new_photo:
            delete_file(WORKER_PHOTO_DIR, worker.photo_filename)
            worker.photo_filename = new_photo

        for index, f in enumerate(request.files.getlist('portfolio_images')):
            fname = save_upload(f, PORTFOLIO_DIR)
            if fname:
                thumbnail = (
                    save_portfolio_thumbnail(request.files.get(f'portfolio_thumbnail_{index}'))
                    if fname.rsplit('.', 1)[-1].lower() in VIDEO_EXT
                    else None
                )
                db.session.add(
                    PortfolioImage(
                        worker_id=worker.id,
                        filename=fname,
                        thumbnail_filename=thumbnail,
                    )
                )

        db.session.commit()
        flash(f"{worker.name}'s profile was updated.", "success")
        return redirect(url_for('admin_dashboard'))

    selected_availability = worker.availability_list
    return render_template('admin/worker_form.html', worker=worker, trades=TRADES, selected_availability=selected_availability)


@app.route('/admin/workers/<int:worker_id>/delete', methods=['POST'])
def delete_worker(worker_id):
    worker = db.get_or_404(Worker, worker_id)
    delete_file(WORKER_PHOTO_DIR, worker.photo_filename)
    for img in worker.portfolio_images:
        delete_file(PORTFOLIO_DIR, img.filename)
        delete_file(PORTFOLIO_DIR, img.thumbnail_filename)
    name = worker.name
    db.session.delete(worker)
    db.session.commit()
    flash(f"{name} was removed from the roster.", "success")
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/portfolio/<int:image_id>/delete', methods=['POST'])
def delete_portfolio_image(image_id):
    image = db.get_or_404(PortfolioImage, image_id)
    worker_id = image.worker_id
    delete_file(PORTFOLIO_DIR, image.filename)
    delete_file(PORTFOLIO_DIR, image.thumbnail_filename)
    db.session.delete(image)
    db.session.commit()
    flash("Portfolio photo removed.", "success")
    return redirect(url_for('edit_worker', worker_id=worker_id))


@app.route('/admin/portfolio/<int:image_id>/edit', methods=['POST'])
def edit_portfolio_image(image_id):
    image = db.get_or_404(PortfolioImage, image_id)
    worker_id = image.worker_id
    caption = request.form.get('caption', '').strip()
    image.caption = caption if caption else None
    db.session.commit()
    flash('Portfolio item updated.', 'success')
    return redirect(url_for('edit_worker', worker_id=worker_id))


@app.route('/admin/workers/<int:worker_id>/upload', methods=['POST'])
def upload_portfolio_items(worker_id):
    worker = db.get_or_404(Worker, worker_id)
    files = request.files.getlist('files')
    created = []
    for index, f in enumerate(files):
        fname = save_upload(f, PORTFOLIO_DIR)
        if fname:
            thumbnail = (
                save_portfolio_thumbnail(request.files.get(f'thumbnail_{index}'))
                if fname.rsplit('.', 1)[-1].lower() in VIDEO_EXT
                else None
            )
            pi = PortfolioImage(
                worker_id=worker.id,
                filename=fname,
                thumbnail_filename=thumbnail,
            )
            db.session.add(pi)
            db.session.flush()
            created.append({
                'id': pi.id,
                'url': pi.url,
                'thumbnail_url': pi.thumbnail_url,
                'type': pi.file_type,
                'caption': pi.caption or '',
            })
    db.session.commit()
    return jsonify({'items': created})


@app.route('/admin/booking/<int:booking_id>/confirm', methods=['POST'])
def confirm_booking(booking_id):
    booking = db.get_or_404(Booking, booking_id)
    booking.status = 'Confirmed'
    db.session.commit()
    flash(f"Booking #{booking.id} confirmed.", "success")
    return redirect(url_for('admin_dashboard'))


# ---------- JSON API (used by the client-side portfolio modal) ----------
@app.route('/api/worker/<int:worker_id>/portfolio')
def worker_portfolio_json(worker_id):
    worker = db.get_or_404(Worker, worker_id)
    return jsonify({
        'name': worker.name,
        'trade': worker.trade,
        'images': [
            {
                'url': img.url,
                'thumbnail_url': img.thumbnail_url,
                'caption': img.caption,
                'type': img.file_type,
                'mime_type': img.mime_type,
            }
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


def ensure_portfolio_columns():
    with app.app_context():
        inspector = inspect(db.engine)
        if 'portfolio_images' not in inspector.get_table_names():
            return
        columns = {column['name'] for column in inspector.get_columns('portfolio_images')}
        if 'thumbnail_filename' not in columns:
            db.session.execute(
                text("ALTER TABLE portfolio_images ADD COLUMN thumbnail_filename VARCHAR(255)")
            )
        db.session.commit()


def init_db():
    with app.app_context():
        db.create_all()
        ensure_worker_columns()
        ensure_portfolio_columns()
        get_admin_config()


init_db()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=False)
