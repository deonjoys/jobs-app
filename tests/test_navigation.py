from io import BytesIO
import os
import sys

import pytest
from sqlalchemy import create_engine

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db, Booking, Worker, PortfolioImage


@pytest.fixture(autouse=True)
def isolated_database(tmp_path):
    with app.app_context():
        original_engine = db.engines[None]
        test_engine = create_engine(
            f"sqlite:///{tmp_path / 'jobs-test.db'}",
            connect_args={'check_same_thread': False},
        )
        db.engines[None] = test_engine
        db.create_all()

    try:
        yield
    finally:
        with app.app_context():
            db.session.remove()
            db.drop_all()
            db.engines[None] = original_engine
        test_engine.dispose()


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
<<<<<<< HEAD
        assert 'Open media' in html


def test_admin_can_upload_multiple_data_url_media_for_info_modal():
=======
        assert 'View' in html


def test_home_page_has_booking_form_for_each_worker():
>>>>>>> 86c53add6e0b1d04d26fc79ae77ad75faa519e93
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.test_client() as client:
        with app.app_context():
            db.drop_all()
            db.create_all()
<<<<<<< HEAD
            worker = Worker(
                name='Alex Builder',
                trade='Mason',
                phone='+233200000001',
                location='Accra',
                experience_years=8,
                bio='Stone and brick work.',
            )
            db.session.add(worker)
            db.session.commit()
            worker_id = worker.id

        with client.session_transaction() as session:
            session['is_admin'] = True

        response = client.post(
            f'/admin/workers/{worker_id}/upload',
            data={
                'files': [
                    (BytesIO(b'photo-bytes'), 'wall.jpg'),
                    (BytesIO(b'video-bytes'), 'walkthrough.mp4'),
                ]
            },
        )
        assert response.status_code == 200
        uploaded = response.get_json()['items']
        assert [item['type'] for item in uploaded] == ['image', 'video']
        assert uploaded[0]['url'].startswith('data:image/jpeg;base64,')
        assert uploaded[1]['url'].startswith('data:video/mp4;base64,')

        portfolio_response = client.get(f'/api/worker/{worker_id}/portfolio')
        portfolio = portfolio_response.get_json()
        assert portfolio['name'] == 'Alex Builder'
        assert portfolio['location'] == 'Accra'
        assert len(portfolio['images']) == 2
        assert portfolio['images'][0]['url'] == uploaded[0]['url']

        home_response = client.get('/')
        html = home_response.get_data(as_text=True)
        assert 'openWorkerInfo' in html
        assert 'portfolioLightbox' in html


def test_new_worker_form_stores_multiple_portfolio_data_urls():
    app.config['TESTING'] = True

    with app.test_client() as client:
        with client.session_transaction() as session:
            session['is_admin'] = True

        response = client.post(
            '/admin/workers/new',
            data={
                'name': 'Taylor Painter',
                'trade': 'Painter',
                'phone': '+233200000002',
                'experience_years': '4',
                'portfolio_images': [
                    (BytesIO(b'first-photo'), 'room.png'),
                    (BytesIO(b'second-photo'), 'finish.webp'),
                ],
            },
        )
        assert response.status_code == 302

        with app.app_context():
            worker = Worker.query.filter_by(name='Taylor Painter').one()
            assert len(worker.portfolio_images) == 2
            assert all(item.data_url.startswith('data:image/') for item in worker.portfolio_images)
=======
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
>>>>>>> 86c53add6e0b1d04d26fc79ae77ad75faa519e93
