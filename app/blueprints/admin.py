import os
import random
import uuid
from flask import Blueprint, render_template, request, redirect, url_for, current_app
from PIL import Image
from app.db import get_db
from app.utils import requires_auth, are_submissions_open, is_voting_open, get_reveal_level, rotate_entry_image

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/', methods=['GET', 'POST'])
@requires_auth
def index():
    conn = get_db()
    categories = current_app.config['CATEGORIES']
    
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'toggle_submissions':
            current = are_submissions_open()
            new_state = 'false' if current else 'true'
            conn.execute("UPDATE state SET value=? WHERE key='submissions_open'", (new_state,))
            if new_state == 'true':
                conn.execute("UPDATE state SET value='false' WHERE key='voting_open'")
                conn.execute("UPDATE state SET value='0' WHERE key LIKE 'reveal_%'")
        elif action == 'toggle_voting':
            current = is_voting_open()
            new_state = 'false' if current else 'true'
            conn.execute("UPDATE state SET value=? WHERE key='voting_open'", (new_state,))
            if new_state == 'true':
                conn.execute("UPDATE state SET value='false' WHERE key='submissions_open'")
        elif action and action.startswith('reveal_'):
            level = action.split('_')[1]
            slug = request.form.get('category')
            conn.execute("UPDATE state SET value=? WHERE key=?", (level, f"reveal_{slug}"))
        elif action == 'rotate_entry':
            entry_id = request.form.get('entry_id')
            if entry_id:
                row = conn.execute("SELECT image_path FROM entries WHERE id=?", (entry_id,)).fetchone()
                if row:
                    rotate_entry_image(row['image_path'])
        elif action == 'delete_entry':
            entry_id = request.form.get('entry_id')
            if entry_id:
                row = conn.execute("SELECT image_path FROM entries WHERE id=?", (entry_id,)).fetchone()
                if row:
                    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], row['image_path'])
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                    conn.execute("DELETE FROM entries WHERE id=?", (entry_id,))
                    conn.execute("DELETE FROM votes WHERE entry_id=?", (entry_id,))
        elif action == 'populate_test':
            colors = [(255,0,0), (0,255,0), (0,0,255), (255,165,0), (128,0,128), (0,128,128), (255,255,0)]
            names = ['Spooky Steve', 'Vampire Vic', 'Mummy Mary', 'Wicked Wanda', 'Franken Fred', 'Skeleton Sue']
            for _ in range(10):
                cat_name = random.choice(list(categories.values()))
                name = f"{random.choice(names)} {random.randint(1,99)}"
                filename = f"test_{uuid.uuid4().hex}.jpg"
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                img = Image.new('RGB', (800, 800), color=random.choice(colors))
                img.save(filepath)
                cursor = conn.cursor()
                cursor.execute("INSERT INTO entries (name, category, image_path) VALUES (?, ?, ?)", (name, cat_name, filename))
                entry_id = cursor.lastrowid
                for _ in range(random.randint(0, 15)):
                    voter = str(uuid.uuid4())
                    fake_fp = f"test_fp_{uuid.uuid4().hex[:8]}"
                    conn.execute("INSERT INTO votes (voter_uuid, category, entry_id, fingerprint) VALUES (?, ?, ?, ?)", (voter, cat_name, entry_id, fake_fp))
        conn.commit()
        return redirect(url_for('admin.index'))

    standings = {}
    reveal_levels = {}
    for slug, cat_name in categories.items():
        reveal_levels[slug] = get_reveal_level(slug)
        standings[slug] = conn.execute('''
            SELECT e.name, COUNT(v.entry_id) as vote_count 
            FROM entries e 
            LEFT JOIN votes v ON e.id = v.entry_id 
            WHERE e.category = ? 
            GROUP BY e.id 
            ORDER BY vote_count DESC, e.name ASC
        ''', (cat_name,)).fetchall()

    all_entries = conn.execute('''
        SELECT e.id, e.name, e.category, e.image_path, COUNT(v.entry_id) as vote_count
        FROM entries e
        LEFT JOIN votes v ON e.id = v.entry_id
        GROUP BY e.id
        ORDER BY e.category, vote_count DESC, e.id DESC
    ''').fetchall()

    return render_template(
        'admin.html',
        submissions_open=are_submissions_open(),
        voting_open=is_voting_open(),
        categories=categories,
        standings=standings,
        reveal_levels=reveal_levels,
        all_entries=all_entries
    )

@admin_bp.route('/reset', methods=['POST'])
@requires_auth
def reset():
    conn = get_db()
    conn.execute("DELETE FROM entries")
    conn.execute("DELETE FROM votes")
    conn.execute("UPDATE state SET value='true' WHERE key='submissions_open'")
    conn.execute("UPDATE state SET value='false' WHERE key='voting_open'")
    conn.execute("UPDATE state SET value='0' WHERE key LIKE 'reveal_%'")
    conn.commit()
    
    upload_folder = current_app.config['UPLOAD_FOLDER']
    for filename in os.listdir(upload_folder):
        file_path = os.path.join(upload_folder, filename)
        if os.path.isfile(file_path):
            os.remove(file_path)
            
    return redirect(url_for('admin.index'))