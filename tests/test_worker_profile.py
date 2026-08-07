import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db, Worker, PortfolioImage


class WorkerProfileTests(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.client = app.test_client()
        with app.app_context():
            db.drop_all()
            db.create_all()

    def test_worker_profile_page_shows_profile_details(self):
        with app.app_context():
            worker = Worker(
                name='Ava Moore',
                trade='Painter',
                phone='0712345678',
                location='Nairobi',
                hourly_rate=25,
                experience_years=7,
                bio='Detail-oriented painter with a knack for bold interiors.',
                status='Available',
            )
            db.session.add(worker)
            db.session.flush()
            db.session.add(PortfolioImage(worker_id=worker.id, filename='sample.jpg', caption='Kitchen refresh'))
            db.session.commit()
            worker_id = worker.id

        response = self.client.get(f'/worker/{worker_id}')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('Ava Moore', html)
        self.assertIn('Years of experience', html)
        self.assertIn('Detail-oriented painter', html)
        self.assertIn('Portfolio', html)


if __name__ == '__main__':
    unittest.main()
