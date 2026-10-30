import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db, Booking, Worker, PortfolioImage


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
        assert 'JobS Admin' in html


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


def test_home_page_has_booking_form_for_each_worker():
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
        assert 'Send booking request' in html
        assert 'name="worker_id"' in html


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
