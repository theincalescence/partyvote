from flask import Blueprint, render_template, current_app, jsonify
from app.db import get_db
from app.utils import are_submissions_open, is_voting_open

tv_bp = Blueprint('tv', __name__)

@tv_bp.route('/tv')
def tv_dashboard():
    return render_template('tv.html')

@tv_bp.route('/tv_content')
def tv_content():
    submissions_open = are_submissions_open()
    voting_open = is_voting_open()
    conn = get_db()
    categories = current_app.config['CATEGORIES']
    
    category_data = {}
    any_reveals = False
    
    for slug, cat_name in categories.items():
        row = conn.execute("SELECT value FROM state WHERE key=?", (f"reveal_{slug}",)).fetchone()
        reveal_level = int(row[0]) if row else 0
        if reveal_level > 0:
            any_reveals = True
            
        results = []
        if reveal_level > 0:
            results = conn.execute('''
                SELECT e.name, e.image_path, COUNT(v.entry_id) as vote_count 
                FROM entries e JOIN votes v ON e.id = v.entry_id 
                WHERE e.category = ? GROUP BY e.id ORDER BY vote_count DESC LIMIT 3
            ''', (cat_name,)).fetchall()
            
        category_data[slug] = {
            'name': cat_name,
            'reveal_level': reveal_level,
            'results': results
        }
        
    compact_header = any_reveals and not submissions_open
    
    html = render_template(
        'tv_content.html',
        submissions_open=submissions_open,
        voting_open=voting_open,
        any_reveals=any_reveals,
        category_data=category_data
    )
    
    return jsonify({"html": html, "compact": compact_header})