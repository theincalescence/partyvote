import os
import random
import uuid
import logging
from flask import Blueprint, render_template, request, redirect, url_for, current_app, flash
from PIL import Image
from app.db import get_db
from app.utils import requires_auth, are_submissions_open, is_voting_open, get_reveal_level, rotate_entry_image, generate_qr_code, get_current_qr_url, get_event_branding, set_event_branding

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
logger = logging.getLogger(__name__)


def build_broadcast_drafts(categories, standings, target_url):
    url = target_url or "http://localhost:5000"

    # 1. Submissions Open
    draft_submissions = (
        f"🎃 Costume & Pumpkin submissions are OPEN! "
        f"Snap a picture and upload your entry here: {url} "
        f"(or scan the TV screen) before submissions lock!"
    )

    # 2. Voting Live
    draft_voting = (
        f"👻 Voting is officially LIVE! "
        f"Check out all the entries and cast your ballots now: {url}\n"
        f"May the best costume and pumpkin win!"
    )

    # 3. 10-Minute Warning
    draft_warning = (
        f"⏳ Final call! Voting closes in 10 minutes! "
        f"Get your votes in now at {url} before the polls lock."
    )

    # 4. Winners Podium (built directly from category standings)
    medals = ["🥇", "🥈", "🥉"]
    winner_lines = ["🏆 RouwenRick Manor: The winners are officially crowned!"]
    has_standings = False

    for slug, cat_name in categories.items():
        cat_rows = standings.get(slug, [])
        if cat_rows:
            has_standings = True
            winner_lines.append(f"\n{cat_name}:")
            for i, r in enumerate(cat_rows[:3]):
                winner_lines.append(
                    f"{medals[i]} {r['name']} ({r['vote_count']} votes)"
                )

    if not has_standings:
        winner_lines.append(
            "\n(Winners will populate automatically once votes are cast!)"
        )

    winner_lines.append(
        "\nIf you placed in the top 3 and already headed out, text the host to grab your prize!"
    )
    draft_winners = "\n".join(winner_lines)

    return {
        "submissions": draft_submissions,
        "voting": draft_voting,
        "warning": draft_warning,
        "winners": draft_winners,
    }


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
            elif action == 'update_entry_name':
                try:
                    entry_id = request.form.get('entry_id')
                    new_name = request.form.get('new_name', '').strip()
                    if entry_id and new_name:
                        conn.execute("UPDATE entries SET name=? WHERE id=?", (new_name, entry_id))
                        flash(f"Entry name updated to '{new_name}'!", "success")
                        logger.info(f"Entry {entry_id} name updated to: {new_name}")
                    else:
                        flash("Entry name cannot be empty.", "warning")
                except Exception as e:
                    logger.error(f"Error updating entry name: {e}")
                    flash("Error updating entry name.", "error")
                    return "Error updating entry name", 500
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
            elif action == 'merge_entries':
                try:
                    primary_id = request.form.get('primary_id')
                    secondary_id = request.form.get('secondary_id')
                    keep_photo = request.form.get('keep_photo', 'primary') # 'primary' or 'secondary'
                    keep_name = request.form.get('keep_name', 'primary')   # 'primary' or 'secondary'

                    if not primary_id or not secondary_id or primary_id == secondary_id:
                        flash("Invalid entries selected for merge.", "error")
                        return redirect(url_for('admin.index'))

                    # Fetch both entry records
                    primary = conn.execute("SELECT * FROM entries WHERE id=?", (primary_id,)).fetchone()
                    secondary = conn.execute("SELECT * FROM entries WHERE id=?", (secondary_id,)).fetchone()

                    if not primary or not secondary:
                        flash("One or both entries could not be found.", "error")
                        return redirect(url_for('admin.index'))

                    # 1. Determine which image to keep and delete the discarded one
                    upload_folder = current_app.config['UPLOAD_FOLDER']
                    if keep_photo == 'secondary':
                        discarded_filename = primary['image_path']
                        kept_filename = secondary['image_path']
                        # Point primary entry to the secondary image
                        conn.execute("UPDATE entries SET image_path=? WHERE id=?", (kept_filename, primary_id))
                    else:
                        discarded_filename = secondary['image_path']

                    if discarded_filename:
                        discarded_path = os.path.join(upload_folder, discarded_filename)
                        if os.path.isfile(discarded_path):
                            os.remove(discarded_path)

                    # 2. Determine which name to keep
                    if keep_name == 'secondary':
                        conn.execute("UPDATE entries SET name=? WHERE id=?", (secondary['name'], primary_id))

                    # 3. Deduplicate votes: if a voter voted for both, purge the secondary vote
                    conn.execute("""
                        DELETE FROM votes 
                        WHERE entry_id = ? 
                        AND voter_uuid IN (SELECT voter_uuid FROM votes WHERE entry_id = ?)
                    """, (secondary_id, primary_id))

                    # 4. Reassign remaining secondary votes to the primary entry
                    conn.execute("UPDATE votes SET entry_id = ? WHERE entry_id = ?", (primary_id, secondary_id))

                    # 5. Delete the duplicate entry record
                    conn.execute("DELETE FROM entries WHERE id=?", (secondary_id,))

                    conn.commit()
                    flash(f"Successfully consolidated duplicate into '{primary['name']}'!", "success")
                    logger.info(f"Merged entry {secondary_id} into {primary_id}")
                    return redirect(url_for('admin.index'))

                except Exception as e:
                    logger.error(f"Error merging entries: {e}")
                    conn.rollback()
                    flash("Error merging entries.", "error")
                    return "Error merging entries", 500
            elif action == 'update_event_branding':
                try:
                    year = request.form.get('event_year', '2026')
                    loc = request.form.get('event_location', 'RouwenRick Manor')
                    l1 = request.form.get('event_title_line1', '').strip()
                    l2 = request.form.get('event_title_line2', '').strip()

                    if not l1:
                        flash("Hero Line 1 is required.", "warning")
                        return redirect(url_for('admin.index'))

                    set_event_branding(year, loc, l1, l2)
                    flash("Event branding updated successfully!", "success")
                    logger.info("Event branding updated")
                except Exception as e:
                    logger.error(f"Error updating branding: {e}")
                    flash("Error updating event branding.", "error")
                    return "Error updating branding", 500              
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
        
        # Build Partiful broadcast drafts using live URL and calculated standings
        branding = get_event_branding()
        event_slug = f"{branding['event_location']}" # e.g. "RouwenRick Manor"
        drafts = build_broadcast_drafts(categories, standings, current_qr_url)
        
        logger.info("Admin dashboard rendered successfully")
        return render_template(
            'admin.html',
            submissions_open=are_submissions_open(),
            voting_open=is_voting_open(),
            categories=categories,
            standings=standings,
            reveal_levels=reveal_levels,
            all_entries=all_entries,
            qr_url=current_qr_url,
            drafts=drafts
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

