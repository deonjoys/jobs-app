import io
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db, Booking, Worker, PortfolioImage
import app as app_module


def test_home_page_hides_admin_link_for_guests():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.test_client() as client:
        with app.app_context():
            db.drop_all()
            db.create_all()

        response = client.get('/')
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert 'Admin Portal' not in html


def test_admin_login_reveals_admin_portal():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.test_client() as client:
        with app.app_context():
            db.drop_all()
            db.create_all()

        response = client.post('/admin/login', follow_redirects=True)
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert 'JobX Admin' in html


def test_worker_profile_page_has_portfolio_lightbox_support():
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.test_client() as client:
        with app.app_context():
            db.drop_all()
            db.create_all()
            worker = Worker(
                name='Jane Smith',
                trade='Plumber',
                phone='+233200000000',
                location='Accra',
                experience_years=5,
                bio='Experienced plumber.',
            )
            db.session.add(worker)
            db.session.flush()
            worker_id = worker.id
            db.session.add(PortfolioImage(worker_id=worker_id, filename='sample.jpg', caption='Kitchen install'))
            db.session.commit()

        response = client.get(f'/worker/{worker_id}')
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert 'portfolio-lightbox' in html
        assert 'View' in html


def test_video_portfolio_uses_play_preview_and_browser_mime_type():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.test_client() as client:
        with app.app_context():
            db.drop_all()
            db.create_all()
            worker = Worker(
                name='Jane Smith',
                trade='Plumber',
                phone='+233200000000',
                experience_years=5,
            )
            db.session.add(worker)
            db.session.flush()
            db.session.add(
                PortfolioImage(
                    worker_id=worker.id,
                    filename='sample.mov',
                    thumbnail_filename='sample-thumbnail.jpg',
                )
            )
            worker_id = worker.id
            db.session.commit()

        response = client.get(f'/worker/{worker_id}')
        html = response.get_data(as_text=True)
        assert response.status_code == 200
        assert 'class="video-preview"' in html
        assert 'src="/uploads/portfolio/sample-thumbnail.jpg"' in html
        assert 'data-media-mime="video/quicktime"' in html
        assert 'preload="auto"' in html

        home = client.get('/')
        assert 'src="/uploads/portfolio/sample-thumbnail.jpg"' in home.get_data(as_text=True)

        portfolio = client.get(f'/api/worker/{worker_id}/portfolio')
        assert portfolio.json['images'][0]['mime_type'] == 'video/quicktime'
        assert portfolio.json['images'][0]['thumbnail_url'].endswith(
            '/uploads/portfolio/sample-thumbnail.jpg'
        )


def test_video_upload_saves_and_serves_generated_thumbnail(tmp_path, monkeypatch):
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    monkeypatch.setattr(app_module, 'PORTFOLIO_DIR', str(tmp_path))

    with app.test_client() as client:
        with app.app_context():
            db.drop_all()
            db.create_all()
            worker = Worker(
                name='Jane Smith',
                trade='Plumber',
                phone='+233200000000',
                experience_years=5,
            )
            db.session.add(worker)
            db.session.commit()
            worker_id = worker.id

        with client.session_transaction() as session:
            session['is_admin'] = True
        response = client.post(
            f'/admin/workers/{worker_id}/upload',
            data={
                'files': (io.BytesIO(b'video data'), 'clip.mp4'),
                'thumbnail_0': (io.BytesIO(b'thumbnail data'), 'clip.jpg'),
            },
            content_type='multipart/form-data',
        )
        assert response.status_code == 200
        item = response.json['items'][0]
        assert item['thumbnail_url']
        thumbnail_response = client.get(item['thumbnail_url'])
        assert thumbnail_response.status_code == 200
        assert thumbnail_response.data == b'thumbnail data'


def test_new_worker_upload_saves_video_thumbnail(tmp_path, monkeypatch):
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    monkeypatch.setattr(app_module, 'PORTFOLIO_DIR', str(tmp_path))

    with app.test_client() as client:
        with app.app_context():
            db.drop_all()
            db.create_all()

        with client.session_transaction() as session:
            session['is_admin'] = True
        response = client.post(
            '/admin/workers/new',
            data={
                'name': 'Jane Smith',
                'trade': 'Plumber',
                'phone': '+233200000000',
                'experience_years': '5',
                'status': 'Available',
                'portfolio_images': (io.BytesIO(b'video data'), 'clip.mp4'),
                'portfolio_thumbnail_0': (io.BytesIO(b'thumbnail data'), 'clip.jpg'),
            },
            content_type='multipart/form-data',
        )
        assert response.status_code == 302
        with app.app_context():
            item = PortfolioImage.query.one()
            assert item.thumbnail_filename
            assert item.thumbnail_filename.endswith('.jpg')


def test_legacy_availability_labels_use_updated_names():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.test_client() as client:
        with app.app_context():
            db.drop_all()
            db.create_all()
            worker = Worker(
                name='Jane Smith',
                trade='Plumber',
                phone='+233200000000',
                experience_years=5,
                availability='["Small jobs", "Big contracts"]',
            )
            db.session.add(worker)
            db.session.commit()
            worker_id = worker.id

        profile = client.get(f'/worker/{worker_id}')
        assert 'Quick job' in profile.get_data(as_text=True)
        assert 'Full contract' in profile.get_data(as_text=True)

        with client.session_transaction() as session:
            session['is_admin'] = True
        form = client.get(f'/admin/workers/{worker_id}/edit')
        html = form.get_data(as_text=True)
        assert 'value="Quick job" checked' in html
        assert 'value="Full contract" checked' in html


def test_home_page_calls_workers_directly_without_booking_form():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.test_client() as client:
        with app.app_context():
            db.drop_all()
            db.create_all()
            db.session.add(
                Worker(
                    name='John Doe',
                    trade='Mason',
                    phone='0200000000',
                    experience_years=3,
                )
            )
            db.session.commit()

        response = client.get('/')
        html = response.get_data(as_text=True)
        assert response.status_code == 200
        assert 'href="tel:0200000000"' in html
        assert 'Send booking request' not in html
        assert 'bookingModal' not in html
        assert 'openBookingModal' not in html


def test_call_links_normalize_formatted_worker_phone_numbers():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.test_client() as client:
        with app.app_context():
            db.drop_all()
            db.create_all()
            worker = Worker(
                name='Jane Smith',
                trade='Plumber',
                phone='+233 (20) 000-0000',
                experience_years=5,
            )
            db.session.add(worker)
            db.session.commit()
            worker_id = worker.id

        home = client.get('/')
        assert 'href="tel:+233200000000"' in home.get_data(as_text=True)
        profile = client.get(f'/worker/{worker_id}')
        assert 'href="tel:+233200000000"' in profile.get_data(as_text=True)


def test_invalid_booking_does_not_create_record():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.test_client() as client:
        with app.app_context():
            db.drop_all()
            db.create_all()

        response = client.post('/book', data={'worker_id': 'not-a-number'})
        assert response.status_code == 302
        with app.app_context():
            assert db.session.query(Booking).count() == 0


def test_invalid_worker_form_returns_validation_error_instead_of_500():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.test_client() as client:
        with app.app_context():
            db.drop_all()
            db.create_all()

        with client.session_transaction() as session:
            session['is_admin'] = True
        response = client.post(
            '/admin/workers/new',
            data={
                'name': 'Invalid Worker',
                'trade': 'Plumber',
                'phone': '0200000000',
                'experience_years': 'not-a-number',
            },
        )
        assert response.status_code == 400
