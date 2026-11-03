import os
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, make_response, send_from_directory, current_app
from app.db import get_db
from app.utils import are_submissions_open, is_voting_open, get_reveal_level, save_and_optimize_image

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    submissions_open = are_submissions_open()
    voting_open = is_voting_open()
    
    if submissions_open:
        status_text = "Photo Submissions are OPEN"
    elif voting_open:
        status_text = "Voting is OPEN"
    else:
        status_text = "Voting is CLOSED"

    return render_template(
        'index.html',
        status_text=status_text,
        categories=current_app.config['CATEGORIES']
    )

@main_bp.route('/category/<slug>', methods=['GET', 'POST'])
def category(slug):
    categories = current_app.config['CATEGORIES']
    if slug not in categories:
        return redirect(url_for('main.index'))
    
    cat_name = categories[slug]
    submissions_open = are_submissions_open()
    voting_open = is_voting_open()
    reveal_level = get_reveal_level(slug)
    category_voting_allowed = voting_open and (reveal_level == 0)
    
    voter_uuid = request.cookies.get('voter_uuid')
    conn = get_db()
    
    if request.method == 'POST':
        if submissions_open:
            name = request.form.get('name')
            file = request.files.get('photo')
            if name and file and file.filename:
                filename = save_and_optimize_image(file)
                conn.execute(
                    "INSERT INTO entries (name, category, image_path) VALUES (?, ?, ?)",
                    (name, cat_name, filename)
                )
                conn.commit()
                return redirect(url_for('main.category', slug=slug))
                
        elif category_voting_allowed:
            fingerprint = request.form.get('device_fp') or 'unknown'
            if not voter_uuid:
                voter_uuid = str(uuid.uuid4())
            entry_id = request.form.get('entry_id')
            
            if entry_id:
                existing = conn.execute('''
                    SELECT 1 FROM votes 
                    WHERE category=? AND (
                        voter_uuid=? OR 
                        (fingerprint=? AND fingerprint != 'unknown')
                    )
                ''', (cat_name, voter_uuid, fingerprint)).fetchone()
                
                resp = make_response(redirect(url_for('main.category', slug=slug)))
                resp.set_cookie('voter_uuid', voter_uuid, max_age=60*60*24*30)
                
                if not existing:
                    conn.execute('''
                        INSERT OR REPLACE INTO votes (voter_uuid, category, entry_id, fingerprint) 
                        VALUES (?, ?, ?, ?)
                    ''', (voter_uuid, cat_name, entry_id, fingerprint))
                    conn.commit()
                    
                return resp
                
        return redirect(url_for('main.category', slug=slug))

    entries = conn.execute("SELECT * FROM entries WHERE category=?", (cat_name,)).fetchall()
    already_voted = False
    if voter_uuid:
        already_voted = conn.execute(
            "SELECT 1 FROM votes WHERE voter_uuid=? AND category=?",
            (voter_uuid, cat_name)
        ).fetchone() is not None

    return render_template(
        'category.html',
        slug=slug,
        cat_name=cat_name,
        entries=entries,
        submissions_open=submissions_open,
        category_voting_allowed=category_voting_allowed,
        already_voted=already_voted,
        voter_uuid=voter_uuid
    )

@main_bp.route('/data/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(current_app.config['UPLOAD_FOLDER'], filename)

@main_bp.route('/qr')
def serve_qr():
    data_dir = current_app.config['DATA_DIR']
    for ext in ['png', 'jpg']:
        qr_file = f"QR.{ext}"
        if os.path.exists(os.path.join(data_dir, qr_file)):
            return send_from_directory(data_dir, qr_file)
    return "QR file missing. Place QR.png or QR.jpg inside the data folder.", 404