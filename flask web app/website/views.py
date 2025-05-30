from flask import Blueprint, render_template, flash, request, jsonify, redirect, url_for
from flask_login import login_required, current_user
from .models import Note
from . import db
import json

# Changed blueprint name to 'views' for consistency
views = Blueprint('views', __name__)

@views.route('/', methods=['GET', 'POST'])
@login_required
def home():
    if request.method == 'POST': 
        note = request.form.get('note')

        if len(note) < 1:
            flash('Note is too short!', category='error') 
        else:
            new_note = Note(data=note, user_id=current_user.id)  
            db.session.add(new_note) 
            db.session.commit()
            flash('Note added!', category='success')

        return redirect(url_for('views.home'))  # Fixed: changed from 'views_blueprint.home' to 'views.home'
  
    user_notes = Note.query.filter_by(user_id=current_user.id).all()
    
    return render_template("home.html", user=current_user, notes=user_notes)

@views.route('/delete-note', methods=['POST'])
@login_required
def delete_note():  
    note = json.loads(request.data) 
    noteId = note['noteId']
    note = Note.query.get(noteId)
    if note:
        if note.user_id == current_user.id:
            db.session.delete(note)
            db.session.commit()
            return jsonify({"message": "Note deleted successfully"}), 200
        else:
            return jsonify({"message": "Unauthorized action"}), 403
    else:
        return jsonify({"message": "Note not found"}), 404