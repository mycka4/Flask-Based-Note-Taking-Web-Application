import unittest
import json
import os
import tempfile
from unittest.mock import patch
from werkzeug.security import generate_password_hash

# Import your application modules
import sys
sys.path.append('.')
from website import create_app, db
from website.models import User, Note


class BaseTestCase(unittest.TestCase):
    """Base test case with common setup and teardown"""
    
    def setUp(self):
        """Set up test fixtures before each test method."""
        self.db_fd, self.db_path = tempfile.mkstemp()
        self.app = create_app()
        self.app.config.update({
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': f'sqlite:///{self.db_path}',
            'WTF_CSRF_ENABLED': False,
            'SECRET_KEY': 'test-secret-key'
        })
        
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        db.create_all()
        
        # Create test users
        self.test_user = User(
            email='test@example.com',
            first_name='Test',
            password=generate_password_hash('testpass123', method='pbkdf2:sha256')
        )
        self.test_user2 = User(
            email='test2@example.com',
            first_name='Test2',
            password=generate_password_hash('testpass456', method='pbkdf2:sha256')
        )
        db.session.add_all([self.test_user, self.test_user2])
        db.session.commit()

    def tearDown(self):
        """Clean up after each test method."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def login_user(self, email='test@example.com', password='testpass123'):
        """Helper method to log in a user"""
        return self.client.post('/login', data={'email': email, 'password': password}, follow_redirects=True)


class TestModels(BaseTestCase):
    """Test database models"""
    
    def test_user_model_creation(self):
        """Test User model creation and attributes"""
        user = User.query.filter_by(email='test@example.com').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.email, 'test@example.com')
        self.assertEqual(user.first_name, 'Test')
        self.assertTrue(user.password)
        self.assertEqual(user.id, 1)

    def test_note_model_creation(self):
        """Test Note model creation and relationships"""
        note = Note(data='Test note content', user_id=self.test_user.id)
        db.session.add(note)
        db.session.commit()
        
        self.assertIsNotNone(note.id)
        self.assertEqual(note.data, 'Test note content')
        self.assertEqual(note.user_id, self.test_user.id)
        self.assertIsNotNone(note.date)

    def test_user_note_relationship(self):
        """Test relationship between User and Note models"""
        note1 = Note(data='First note', user_id=self.test_user.id)
        note2 = Note(data='Second note', user_id=self.test_user.id)
        db.session.add_all([note1, note2])
        db.session.commit()
        
        user = User.query.get(self.test_user.id)
        self.assertEqual(len(user.notes), 2)
        self.assertIn(note1, user.notes)
        self.assertIn(note2, user.notes)


class TestAuth(BaseTestCase):
    """Test authentication routes"""
    
    def test_login_get(self):
        """Test GET request to login page"""
        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)

    def test_login_post_valid_credentials(self):
        """Test POST request with valid credentials"""
        response = self.client.post('/login', data={'email': 'test@example.com', 'password': 'testpass123'})
        self.assertEqual(response.status_code, 200)

    def test_login_post_invalid_email(self):
        """Test POST request with non-existent email"""
        response = self.client.post('/login', data={'email': 'nonexistent@example.com', 'password': 'testpass123'})
        self.assertEqual(response.status_code, 200)

    def test_login_post_invalid_password(self):
        """Test POST request with wrong password"""
        response = self.client.post('/login', data={'email': 'test@example.com', 'password': 'wrongpassword'})
        self.assertEqual(response.status_code, 200)

    def test_logout_requires_login(self):
        """Test logout without being logged in"""
        response = self.client.get('/logout')
        self.assertEqual(response.status_code, 302)

    def test_logout_when_logged_in(self):
        """Test logout when logged in"""
        self.login_user()
        response = self.client.get('/logout')
        self.assertEqual(response.status_code, 302)

    def test_signup_get(self):
        """Test GET request to signup page"""
        response = self.client.get('/sign-up')
        self.assertEqual(response.status_code, 200)

    def test_signup_post_valid_data(self):
        """Test POST request with valid signup data"""
        response = self.client.post('/sign-up', data={
            'email': 'newuser@example.com', 'firstName': 'NewUser',
            'password1': 'newpass123', 'password2': 'newpass123'
        })
        self.assertEqual(response.status_code, 302)
        new_user = User.query.filter_by(email='newuser@example.com').first()
        self.assertIsNotNone(new_user)

    def test_signup_post_existing_email(self):
        """Test signup with already existing email"""
        response = self.client.post('/sign-up', data={
            'email': 'test@example.com', 'firstName': 'NewUser',
            'password1': 'newpass123', 'password2': 'newpass123'
        })
        self.assertEqual(response.status_code, 200)

    def test_signup_validation_errors(self):
        """Test signup validation scenarios"""
        test_cases = [
            {'email': 'a@b', 'firstName': 'User', 'password1': 'pass', 'password2': 'pass'},  # Short email
            {'email': 'new@example.com', 'firstName': 'A', 'password1': 'pass', 'password2': 'pass'},  # Short name
            {'email': 'new@example.com', 'firstName': 'User', 'password1': 'p1', 'password2': 'p2'},  # Mismatch
            {'email': 'new@example.com', 'firstName': 'User', 'password1': '12', 'password2': '12'},  # Short pass
        ]
        for data in test_cases:
            response = self.client.post('/sign-up', data=data)
            self.assertEqual(response.status_code, 200)


class TestViews(BaseTestCase):
    """Test main views"""
    
    def test_home_requires_login(self):
        """Test that home page requires login"""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)

    def test_home_get_when_logged_in(self):
        """Test GET request to home page when logged in"""
        self.login_user()
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_home_post_valid_note(self):
        """Test POST request to create a valid note"""
        self.login_user()
        response = self.client.post('/', data={'note': 'This is a test note'}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        note = Note.query.filter_by(data='This is a test note').first()
        self.assertIsNotNone(note)

    def test_home_post_empty_note(self):
        """Test POST request with empty note"""
        self.login_user()
        note_count = Note.query.count()
        response = self.client.post('/', data={'note': ''}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Note.query.count(), note_count)

    def test_delete_note_valid(self):
        """Test deleting a valid note"""
        note = Note(data='Note to delete', user_id=self.test_user.id)
        db.session.add(note)
        db.session.commit()
        
        self.login_user()
        response = self.client.post('/delete-note', data=json.dumps({'noteId': note.id}), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(Note.query.get(note.id))

    def test_delete_note_unauthorized(self):
        """Test deleting a note that belongs to another user"""
        note = Note(data='Other user note', user_id=self.test_user2.id)
        db.session.add(note)
        db.session.commit()
        
        self.login_user()
        response = self.client.post('/delete-note', data=json.dumps({'noteId': note.id}), content_type='application/json')
        self.assertEqual(response.status_code, 403)

    def test_delete_note_not_found(self):
        """Test deleting a non-existent note"""
        self.login_user()
        response = self.client.post('/delete-note', data=json.dumps({'noteId': 99999}), content_type='application/json')
        self.assertEqual(response.status_code, 404)

    def test_delete_note_requires_login(self):
        """Test that delete note requires login"""
        response = self.client.post('/delete-note', data=json.dumps({'noteId': 1}), content_type='application/json')
        self.assertEqual(response.status_code, 302)


class TestAPI(BaseTestCase):
    """Test API routes"""
    
    def test_api_test_route(self):
        """Test the API test route"""
        response = self.client.get('/api/test')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'API is working!')

    def test_debug_user_requires_login(self):
        """Test debug user route requires login"""
        response = self.client.get('/api/debug/user')
        self.assertEqual(response.status_code, 302)

    def test_debug_user_when_logged_in(self):
        """Test debug user route when logged in"""
        self.login_user()
        response = self.client.get('/api/debug/user')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['user_id'], self.test_user.id)

    def test_debug_all_notes(self):
        """Test debug all notes route"""
        note1 = Note(data='Note 1', user_id=self.test_user.id)
        note2 = Note(data='Note 2', user_id=self.test_user2.id)
        db.session.add_all([note1, note2])
        db.session.commit()
        
        response = self.client.get('/api/debug/all-notes')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 2)

    def test_test_create_note(self):
        """Test the test create note route"""
        response = self.client.post('/api/test/notes', json={'data': 'Test note', 'user_id': self.test_user.id})
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['message'], 'Test note created')

    def test_test_create_note_missing_data(self):
        """Test test create note with missing data"""
        response = self.client.post('/api/test/notes', json={})
        self.assertEqual(response.status_code, 400)
        response = self.client.post('/api/test/notes', json={'data': 'Test note'})
        self.assertEqual(response.status_code, 400)

    def test_get_notes_requires_login(self):
        """Test get notes requires login"""
        response = self.client.get('/api/notes')
        self.assertEqual(response.status_code, 302)

    def test_get_notes_when_logged_in(self):
        """Test get notes when logged in"""
        note1 = Note(data='Note 1', user_id=self.test_user.id)
        note2 = Note(data='Note 2', user_id=self.test_user.id)
        db.session.add_all([note1, note2])
        db.session.commit()
        
        self.login_user()
        response = self.client.get('/api/notes')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 2)

    def test_get_note_by_id_valid(self):
        """Test get specific note by ID"""
        note = Note(data='Specific note', user_id=self.test_user.id)
        db.session.add(note)
        db.session.commit()
        
        self.login_user()
        response = self.client.get(f'/api/notes/{note.id}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['data'], 'Specific note')

    def test_get_note_by_id_unauthorized(self):
        """Test get note belonging to another user"""
        note = Note(data='Other user note', user_id=self.test_user2.id)
        db.session.add(note)
        db.session.commit()
        
        self.login_user()
        response = self.client.get(f'/api/notes/{note.id}')
        self.assertEqual(response.status_code, 403)

    def test_get_note_by_id_not_found(self):
        """Test get non-existent note"""
        self.login_user()
        response = self.client.get('/api/notes/99999')
        self.assertEqual(response.status_code, 404)

    def test_create_note_via_api(self):
        """Test creating note via API"""
        self.login_user()
        response = self.client.post('/api/notes', json={'data': 'API created note'})
        self.assertEqual(response.status_code, 201)
        note = Note.query.filter_by(data='API created note').first()
        self.assertIsNotNone(note)

    def test_create_note_via_api_missing_data(self):
        """Test creating note via API with missing data"""
        self.login_user()
        response = self.client.post('/api/notes', json={})
        self.assertEqual(response.status_code, 400)

    def test_create_note_via_api_requires_login(self):
        """Test creating note via API requires login"""
        response = self.client.post('/api/notes', json={'data': 'Test note'})
        self.assertEqual(response.status_code, 302)

    def test_update_note_valid(self):
        """Test updating a valid note"""
        note = Note(data='Original note', user_id=self.test_user.id)
        db.session.add(note)
        db.session.commit()
        
        self.login_user()
        response = self.client.put(f'/api/notes/{note.id}', json={'data': 'Updated note'})
        self.assertEqual(response.status_code, 200)
        updated_note = Note.query.get(note.id)
        self.assertEqual(updated_note.data, 'Updated note')

    def test_update_note_unauthorized(self):
        """Test updating note belonging to another user"""
        note = Note(data='Other user note', user_id=self.test_user2.id)
        db.session.add(note)
        db.session.commit()
        
        self.login_user()
        response = self.client.put(f'/api/notes/{note.id}', json={'data': 'Hacked note'})
        self.assertEqual(response.status_code, 403)

    def test_update_note_not_found(self):
        """Test updating non-existent note"""
        self.login_user()
        response = self.client.put('/api/notes/99999', json={'data': 'Updated note'})
        self.assertEqual(response.status_code, 404)

    def test_update_note_empty_content(self):
        """Test updating note with empty content"""
        note = Note(data='Original note', user_id=self.test_user.id)
        db.session.add(note)
        db.session.commit()
        
        self.login_user()
        response = self.client.put(f'/api/notes/{note.id}', json={'data': ''})
        self.assertEqual(response.status_code, 400)

    def test_delete_note_via_api_valid(self):
        """Test deleting note via API"""
        note = Note(data='Note to delete', user_id=self.test_user.id)
        db.session.add(note)
        db.session.commit()
        
        self.login_user()
        response = self.client.delete(f'/api/notes/{note.id}')
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(Note.query.get(note.id))

    def test_delete_note_via_api_unauthorized(self):
        """Test deleting note via API - unauthorized"""
        note = Note(data='Other user note', user_id=self.test_user2.id)
        db.session.add(note)
        db.session.commit()
        
        self.login_user()
        response = self.client.delete(f'/api/notes/{note.id}')
        self.assertEqual(response.status_code, 403)

    def test_delete_note_via_api_not_found(self):
        """Test deleting non-existent note via API"""
        self.login_user()
        response = self.client.delete('/api/notes/99999')
        self.assertEqual(response.status_code, 404)


class TestAppFactory(BaseTestCase):
    """Test application factory and initialization"""
    
    def test_app_creation(self):
        """Test that app is created successfully"""
        self.assertIsNotNone(self.app)
        self.assertTrue(self.app.config['TESTING'])

    def test_blueprints_registered(self):
        """Test that all blueprints are registered"""
        blueprint_names = [bp.name for bp in self.app.blueprints.values()]
        self.assertIn('views_blueprint', blueprint_names)
        self.assertIn('auth_blueprint', blueprint_names)
        self.assertIn('api_blueprint', blueprint_names)

    @patch('website.os.path.exists')
    def test_create_database_when_not_exists(self, mock_exists):
        """Test database creation when it doesn't exist"""
        from website import create_database
        mock_exists.return_value = False
        
        with patch('website.db.create_all') as mock_create_all:
            create_database(self.app)
            mock_create_all.assert_called_once()

    @patch('website.os.path.exists')
    def test_create_database_when_exists(self, mock_exists):
        """Test database creation when it already exists"""
        from website import create_database
        mock_exists.return_value = True
        
        with patch('website.db.create_all') as mock_create_all:
            create_database(self.app)
            mock_create_all.assert_not_called()


class TestErrorHandling(BaseTestCase):
    """Test error handling scenarios"""
    
    def test_invalid_json_in_delete_note(self):
        """Test delete note with invalid JSON"""
        self.login_user()
        response = self.client.post('/delete-note', data='invalid json', content_type='application/json')
        self.assertIn(response.status_code, [400, 500])

    def test_missing_form_data_in_signup(self):
        """Test signup with missing form data"""
        response = self.client.post('/sign-up', data={})
        self.assertEqual(response.status_code, 200)

    def test_missing_form_data_in_login(self):
        """Test login with missing form data"""
        response = self.client.post('/login', data={})
        self.assertEqual(response.status_code, 200)


if __name__ == '__main__':
    # Create and run test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    test_classes = [TestModels, TestAuth, TestViews, TestAPI, TestAppFactory, TestErrorHandling]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print(f"\n{'='*50}")
    print("TEST COVERAGE SUMMARY")
    print(f"{'='*50}")
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    if result.testsRun > 0:
        success_rate = ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100)
        print(f"Success rate: {success_rate:.1f}%")