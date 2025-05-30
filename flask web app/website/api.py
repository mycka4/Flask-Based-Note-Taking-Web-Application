from flask import Blueprint, request, jsonify, abort
from flask_login import login_required, current_user
from .models import Note
from . import db

api = Blueprint('api_blueprint', __name__, url_prefix='/api')

# Test route to check if API is working
@api.route('/test', methods=['GET'])
def test_api():
    return jsonify({"message": "API is working!"}), 200

# Debug route to check current user
@api.route('/debug/user', methods=['GET'])
@login_required
def debug_user():
    return jsonify({
        "user_id": current_user.id,
        "email": current_user.email,
        "is_authenticated": current_user.is_authenticated
    }), 200

# Debug route to see all notes in database
@api.route('/debug/all-notes', methods=['GET'])
def debug_all_notes():
    all_notes = Note.query.all()
    return jsonify([{
        'id': n.id, 
        'data': n.data, 
        'user_id': n.user_id
    } for n in all_notes]), 200

# Test route to create note without authentication (for testing only)
@api.route('/test/notes', methods=['POST'])
def test_create_note():
    data = request.get_json()
    
    if not data or 'data' not in data or 'user_id' not in data:
        return jsonify({"error": "Missing note content or user_id"}), 400
    
    new_note = Note(data=data['data'], user_id=data['user_id'])
    db.session.add(new_note)
    db.session.commit()
    
    return jsonify({"message": "Test note created", "id": new_note.id}), 201

# Production routes with authentication
@api.route('/notes', methods=['GET'])
@login_required
def get_notes():
    notes = Note.query.filter_by(user_id=current_user.id).all()
    return jsonify([{'id': n.id, 'data': n.data} for n in notes]), 200

@api.route('/notes/<int:id>', methods=['GET'])
@login_required
def get_note(id):
    note = Note.query.get_or_404(id)
    print(f"Note user_id: {note.user_id}, Current user_id: {current_user.id}")  # Debug print
    if note.user_id != current_user.id:
        return jsonify({"error": f"Access denied. Note belongs to user {note.user_id}, you are user {current_user.id}"}), 403
    return jsonify({'id': note.id, 'data': note.data}), 200

@api.route('/notes', methods=['POST'])
@login_required
def create_note():
    data = request.get_json()

    if not data or 'data' not in data:
        return jsonify({"error": "Missing note content"}), 400

    new_note = Note(data=data['data'], user_id=current_user.id)
    db.session.add(new_note)
    db.session.commit()

    return jsonify({"message": "Note created", "id": new_note.id}), 201

@api.route('/notes/<int:id>', methods=['PUT'])
@login_required
def update_note(id):
    note = Note.query.get_or_404(id)
    if note.user_id != current_user.id:
        abort(403)
    data = request.get_json()
    content = data.get('data', '')
    if not content:
        return jsonify({'error': 'Note content is required'}), 400
    note.data = content
    db.session.commit()
    return jsonify({'message': 'Note updated', 'id': note.id}), 200

@api.route('/notes/<int:id>', methods=['DELETE'])
@login_required
def delete_note(id):
    note = Note.query.get_or_404(id)

    if note.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403

    db.session.delete(note)
    db.session.commit()
    return jsonify({"message": "Note deleted"}), 200