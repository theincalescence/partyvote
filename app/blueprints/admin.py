import os
import random
import uuid
import logging
from flask import Blueprint, render_template, request, redirect, url_for, current_app, flash
from PIL import Image
from app.db import get_db
from app.utils import requires_auth, are_submissions_open, is_voting_open, get_reveal_level, rotate_entry_image, generate_qr_code, get_current_qr_url

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
logger = logging.getLogger(__name__)

@admin_bp.route('/', methods=['GET', 'POST'])
@requires_auth
def index():
    conn = get_db()
    categories = current_app.config['CATEGORIES']
    
    if request.method == 'POST':
        try:
            action = request.form.get('action')
            logger.info(f"Admin action initiated: {action}")

            # Handle QR code generation if it's a QR form submission
            if action == 'generate_qr':
                qr_url = request.form.get('qr_url', 'http://localhost:5000')
                
                # Update the QR URL in database
                try:
                    conn.execute('UPDATE state SET qr_url = ?', (qr_url,))
                    conn.commit()
                    
                    # Generate QR code (overwriting previous)
                    qr_filename = generate_qr_code(qr_url)
                    
                    if qr_filename:
                        flash('QR code generated successfully!', 'success')
                    else:
                        flash('Error generating QR code.', 'error')
                        
                except Exception as e:
                    logger.error(f"Error generating QR code: {e}")
                    flash('Error generating QR code.', 'error')
                    
                return redirect(url_for('admin.index'))

            if action == 'toggle_submissions':
                try:
                    current = are_submissions_open()
                    new_state = 'false' if current else 'true'
                    conn.execute("UPDATE state SET value=? WHERE key='submissions_open'", (new_state,))
                    if new_state == 'true':
                        conn.execute("UPDATE state SET value='false' WHERE key='voting_open'")
                        conn.execute("UPDATE state SET value='0' WHERE key LIKE 'reveal_%'")
                    logger.info(f"Submissions toggled to: {new_state}")
                except Exception as e:
                    logger.error(f"Error toggling submissions: {e}")
                    return "Error updating submissions", 500
            elif action == 'toggle_voting':
                try:
                    current = is_voting_open()
                    new_state = 'false' if current else 'true'
                    conn.execute("UPDATE state SET value=? WHERE key='voting_open'", (new_state,))
                    if new_state == 'true':
                        conn.execute("UPDATE state SET value='false' WHERE key='submissions_open'")
                    logger.info(f"Voting toggled to: {new_state}")
                except Exception as e:
                    logger.error(f"Error toggling voting: {e}")
                    return "Error updating voting", 500
            elif action and action.startswith('reveal_'):
                try:
                    level = action.split('_')[1]
                    slug = request.form.get('category')
                    conn.execute("UPDATE state SET value=? WHERE key=?", (level, f"reveal_{slug}"))
                    logger.info(f"Reveal level set to {level} for category {slug}")
                except Exception as e:
                    logger.error(f"Error setting reveal level: {e}")
                    return "Error updating reveal level", 500
            elif action == 'rotate_entry':
                try:
                    entry_id = request.form.get('entry_id')
                    if entry_id:
                        row = conn.execute("SELECT image_path FROM entries WHERE id=?", (entry_id,)).fetchone()
                        if row:
                            if rotate_entry_image(row['image_path']):
                                logger.info(f"Successfully rotated entry {entry_id}")
                            else:
                                logger.warning(f"Failed to rotate entry {entry_id}")
                except Exception as e:
                    logger.error(f"Error rotating entry: {e}")
                    return "Error rotating entry", 500
            elif action == 'delete_entry':
                try:
                    entry_id = request.form.get('entry_id')
                    if entry_id:
                        row = conn.execute("SELECT image_path FROM entries WHERE id=?", (entry_id,)).fetchone()
                        if row:
                            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], row['image_path'])
                            if os.path.isfile(file_path):
                                os.remove(file_path)
                            conn.execute("DELETE FROM entries WHERE id=?", (entry_id,))
                            logger.info(f"Entry {entry_id} deleted successfully")
                except Exception as e:
                    logger.error(f"Error deleting entry: {e}")
                    return "Error deleting entry", 500
            elif action == 'populate_test_data':
                try:
                    # Generate test data for each category
                    for slug, cat_name in categories.items():
                        # Add some test entries
                        names = ['Test Entry', 'Sample Entry', 'Demo Entry']
                        colors = ['#FF5733', '#33FF57', '#3357FF', '#F333FF', '#FF33A1']
                        for _ in range(3):
                            name = f"{random.choice(names)} {random.randint(1, 99)}"
                            filename = f"test_{uuid.uuid4().hex[:8]}.jpg"
                            img = Image.new('RGB', (800, 800), color=random.choice(colors))
                            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                            img.save(filepath)
                            cursor = conn.cursor()
                            cursor.execute("INSERT INTO entries (name, category, image_path) VALUES (?, ?, ?)", (name, cat_name, filename))
                            entry_id = cursor.lastrowid
                            for _ in range(random.randint(0, 15)):
                                voter = str(uuid.uuid4())
                                fake_fp = f"test_fp_{uuid.uuid4().hex[:8]}"
                                conn.execute("INSERT INTO votes (voter_uuid, category, entry_id, fingerprint) VALUES (?, ?, ?, ?)", (voter, cat_name, entry_id, fake_fp))
                    logger.info("Test data populated successfully")
                except Exception as e:
                    logger.error(f"Error populating test data: {e}")
                    return "Error populating test data", 500
            
            conn.commit()
            logger.info("Admin actions committed successfully")
            return redirect(url_for('admin.index'))
            
        except Exception as e:
            logger.error(f"Error in admin index route: {e}")
            conn.rollback()
            return "An error occurred during admin operations", 500
    
    # Regular GET request handling
    try:
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

        current_qr_url = get_current_qr_url()
        
        logger.info("Admin dashboard rendered successfully")
        return render_template(
            'admin.html',
            submissions_open=are_submissions_open(),
            voting_open=is_voting_open(),
            categories=categories,
            standings=standings,
            reveal_levels=reveal_levels,
            all_entries=all_entries,
            qr_url=current_qr_url
        )
        
    except Exception as e:
        logger.error(f"Error rendering admin dashboard: {e}")
        return "Error loading admin dashboard", 500

@admin_bp.route('/reset', methods=['POST'])
@requires_auth
def reset():
    conn = get_db()
    try:
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
                
        logger.info("Database reset completed successfully")
        return redirect(url_for('admin.index'))
        
    except Exception as e:
        logger.error(f"Error resetting database: {e}")
        conn.rollback()
        return "Error resetting database", 500
