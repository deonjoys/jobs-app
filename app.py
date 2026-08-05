import os
import uuid
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, text
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "jobs_secret_key")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_ROOT = os.path.join(BASE_DIR, 'static', 'uploads')

DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASS = os.getenv('DB_PASS', 'postgres')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'jobs_db')

DEFAULT_DB_URI = os.getenv('DATABASE_URL') or os.getenv('DB_URL')
if not DEFAULT_DB_URI:
    if any([os.getenv('DB_USER'), os.getenv('DB_PASS'), os.getenv('DB_HOST'), os.getenv('DB_PORT'), os.getenv('DB_NAME')]):
        DEFAULT_DB_URI = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    else:
        DEFAULT_DB_URI = f"sqlite:///{os.path.join(BASE_DIR, 'jobs.db')}"

app.config['SQLALCHEMY_DATABASE_URI'] = DEFAULT_DB_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
if DEFAULT_DB_URI.startswith('sqlite'):
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'connect_args': {'check_same_thread': False}}
WORKER_PHOTO_DIR = os.path.join(UPLOAD_ROOT, 'workers')
PORTFOLIO_DIR = os.path.join(UPLOAD_ROOT, 'portfolio')
os.makedirs(WORKER_PHOTO_DIR, exist_ok=True)
os.makedirs(PORTFOLIO_DIR, exist_ok=True)

ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'webp', 'gif'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB uploads

TRADES = ['Electrician','Mason', 'Plumber', 'Painter', 'Carpenter', 'Interior Decorator', 'AC Installer']

db = SQLAlchemy(app)


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
    status = db.Column(db.String(20), default='Available')
    photo_filename = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    portfolio_images = db.relationship(
        'PortfolioImage', backref='worker', cascade='all, delete-orphan', lazy=True
    )

    @property
    def photo_url(self):
        if self.photo_filename:
            return url_for('static', filename=f'uploads/workers/{self.photo_filename}')
        return None

    @property
    def initials(self):
        parts = self.name.split()
        return ''.join(p[0] for p in parts[:2]).upper()


class PortfolioImage(db.Model):
    __tablename__ = 'portfolio_images'
    id = db.Column(db.Integer, primary_key=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('workers.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    caption = db.Column(db.String(150), nullable=True)

    @property
    def url(self):
        return url_for('static', filename=f'uploads/portfolio/{self.filename}')


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
    ext = secure_filename(file_storage.filename).rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    file_storage.save(os.path.join(folder, filename))
    return filename


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
    new_booking = Booking(
        worker_id=request.form.get('worker_id'),
        client_name=request.form.get('client_name'),
        client_phone=request.form.get('client_phone'),
        service_address=request.form.get('service_address'),
        booking_date=request.form.get('booking_date'),
    )
    db.session.add(new_booking)
    db.session.commit()
    flash("Your booking request has been submitted. We'll confirm shortly.", "success")
    return redirect(url_for('client_home'))


# ---------- Admin routes ----------
@app.route('/admin')
def admin_dashboard():
    workers = Worker.query.order_by(Worker.id.desc()).all()
    bookings = Booking.query.order_by(Booking.id.desc()).all()
    return render_template('admin/dashboard.html', workers=workers, bookings=bookings)


@app.route('/admin/workers/new', methods=['GET', 'POST'])
def add_worker():
    if request.method == 'POST':
        photo_filename = save_upload(request.files.get('photo'), WORKER_PHOTO_DIR)

        worker = Worker(
            name=request.form.get('name'),
            trade=request.form.get('trade'),
            phone=request.form.get('phone'),
            location=request.form.get('location'),
            hourly_rate=0,
            experience_years=int(request.form.get('experience_years')),
            bio=request.form.get('bio'),
            status=request.form.get('status', 'Available'),
            photo_filename=photo_filename,
        )
        db.session.add(worker)
        db.session.flush()  # get worker.id before commit

        for f in request.files.getlist('portfolio_images'):
            fname = save_upload(f, PORTFOLIO_DIR)
            if fname:
                db.session.add(PortfolioImage(worker_id=worker.id, filename=fname))

        db.session.commit()
        flash(f"{worker.name} was added to the roster.", "success")
        return redirect(url_for('admin_dashboard'))

    return render_template('admin/worker_form.html', worker=None, trades=TRADES)


@app.route('/admin/workers/<int:worker_id>/edit', methods=['GET', 'POST'])
def edit_worker(worker_id):
    worker = Worker.query.get_or_404(worker_id)

    if request.method == 'POST':
        worker.name = request.form.get('name')
        worker.trade = request.form.get('trade')
        worker.phone = request.form.get('phone')
        worker.location = request.form.get('location')
        worker.experience_years = int(request.form.get('experience_years'))
        worker.bio = request.form.get('bio')
        worker.status = request.form.get('status', 'Available')

        new_photo = save_upload(request.files.get('photo'), WORKER_PHOTO_DIR)
        if new_photo:
            delete_file(WORKER_PHOTO_DIR, worker.photo_filename)
            worker.photo_filename = new_photo

        for f in request.files.getlist('portfolio_images'):
            fname = save_upload(f, PORTFOLIO_DIR)
            if fname:
                db.session.add(PortfolioImage(worker_id=worker.id, filename=fname))

        db.session.commit()
        flash(f"{worker.name}'s profile was updated.", "success")
        return redirect(url_for('admin_dashboard'))

    return render_template('admin/worker_form.html', worker=worker, trades=TRADES)


@app.route('/admin/workers/<int:worker_id>/delete', methods=['POST'])
def delete_worker(worker_id):
    worker = Worker.query.get_or_404(worker_id)
    delete_file(WORKER_PHOTO_DIR, worker.photo_filename)
    for img in worker.portfolio_images:
        delete_file(PORTFOLIO_DIR, img.filename)
    name = worker.name
    db.session.delete(worker)
    db.session.commit()
    flash(f"{name} was removed from the roster.", "success")
    return redirect(url_for('admin_dashboard'))


@app.route('/admin/portfolio/<int:image_id>/delete', methods=['POST'])
def delete_portfolio_image(image_id):
    image = PortfolioImage.query.get_or_404(image_id)
    worker_id = image.worker_id
    delete_file(PORTFOLIO_DIR, image.filename)
    db.session.delete(image)
    db.session.commit()
    flash("Portfolio photo removed.", "success")
    return redirect(url_for('edit_worker', worker_id=worker_id))


@app.route('/admin/booking/<int:booking_id>/confirm', methods=['POST'])
def confirm_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    booking.status = 'Confirmed'
    db.session.commit()
    flash(f"Booking #{booking.id} confirmed.", "success")
    return redirect(url_for('admin_dashboard'))


# ---------- JSON API (used by the client-side portfolio modal) ----------
@app.route('/api/worker/<int:worker_id>/portfolio')
def worker_portfolio_json(worker_id):
    worker = Worker.query.get_or_404(worker_id)
    return jsonify({
        'name': worker.name,
        'trade': worker.trade,
        'images': [{'url': img.url, 'caption': img.caption} for img in worker.portfolio_images],
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
        db.session.commit()


def init_db():
    with app.app_context():
        db.create_all()
        ensure_worker_columns()


init_db()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)), debug=False)
