import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db


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
        assert 'Admin Portal' in html
