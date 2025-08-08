import os
import uuid
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, session, send_file, jsonify, abort
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import or_, desc, func
from app import app, db, mail
from models import User, Note, Subject, Rating, Comment, Download
from utils import send_email, allowed_file, get_file_size
from flask_mail import Message

# Initialize default subjects - moved to app.py to avoid decorator issue

@app.route('/')
def index():
    # Get latest notes
    latest_notes = Note.query.filter_by(is_approved=True).order_by(desc(Note.upload_date)).limit(6).all()
    
    # Get most downloaded notes
    popular_notes = Note.query.filter_by(is_approved=True).order_by(desc(Note.download_count)).limit(6).all()
    
    # Get statistics
    total_notes = Note.query.filter_by(is_approved=True).count()
    total_users = User.query.count()
    total_downloads = db.session.query(func.sum(Note.download_count)).scalar() or 0
    
    return render_template('index.html', 
                         latest_notes=latest_notes,
                         popular_notes=popular_notes,
                         total_notes=total_notes,
                         total_users=total_users,
                         total_downloads=total_downloads)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        security_question = request.form['security_question']
        security_answer = request.form['security_answer'].lower().strip()
        
        # Validation
        if password != confirm_password:
            flash('Passwords do not match!', 'error')
            return render_template('signup.html')
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists!', 'error')
            return render_template('signup.html')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered!', 'error')
            return render_template('signup.html')
        
        # Create new user
        user = User()
        user.username = username
        user.email = email
        user.password_hash = generate_password_hash(password)
        user.security_question = security_question
        user.security_answer = security_answer
        
        db.session.add(user)
        db.session.commit()
        
        # Send welcome email
        try:
            send_email(
                email,
                'Welcome to EduNotesPro!',
                f'Hello {username},\n\nWelcome to EduNotesPro! You can now start uploading and downloading educational notes.\n\nBest regards,\nEduNotesPro Team'
            )
        except Exception as e:
            app.logger.error(f"Failed to send welcome email: {e}")
        
        flash('Account created successfully! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            
            flash(f'Welcome back, {user.username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password!', 'error')
    
    return render_template('login.html')

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        security_answer = request.form['security_answer'].lower().strip()
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        user = User.query.filter_by(email=email).first()
        
        if not user:
            flash('Email not found!', 'error')
            return render_template('forgot_password.html')
        
        if user.security_answer != security_answer:
            flash('Incorrect security answer!', 'error')
            return render_template('forgot_password.html', user=user)
        
        if new_password != confirm_password:
            flash('Passwords do not match!', 'error')
            return render_template('forgot_password.html', user=user)
        
        user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        
        flash('Password reset successfully! Please log in with your new password.', 'success')
        return redirect(url_for('login'))
    
    email = request.args.get('email')
    user = None
    if email:
        user = User.query.filter_by(email=email).first()
    
    return render_template('forgot_password.html', user=user)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please log in to access dashboard.', 'error')
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    user_notes = Note.query.filter_by(user_id=user.id).all()
    
    # User statistics
    total_uploads = len(user_notes)
    approved_uploads = len([note for note in user_notes if note.is_approved])
    total_downloads_received = sum(note.download_count for note in user_notes)
    
    return render_template('dashboard.html',
                         user=user,
                         user_notes=user_notes,
                         total_uploads=total_uploads,
                         approved_uploads=approved_uploads,
                         total_downloads_received=total_downloads_received)

@app.route('/upload_note', methods=['GET', 'POST'])
def upload_note():
    if 'user_id' not in session:
        flash('Please log in to upload notes.', 'error')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        subject_id = request.form['subject_id']
        semester = request.form['semester']
        file = request.files['file']
        
        if file and file.filename and allowed_file(file.filename):
            # Generate unique filename
            filename = str(uuid.uuid4()) + '.' + file.filename.rsplit('.', 1)[1].lower()
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            note = Note()
            note.title = title
            note.description = description
            note.filename = filename
            note.original_filename = file.filename
            note.file_size = get_file_size(file_path)
            note.semester = int(semester)
            note.user_id = session['user_id']
            note.subject_id = int(subject_id)
            
            db.session.add(note)
            db.session.commit()
            
            flash('Note uploaded successfully! It will be visible after admin approval.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid file type! Please upload PDF or DOC files only.', 'error')
    
    subjects = Subject.query.all()
    return render_template('upload_note.html', subjects=subjects)

@app.route('/view_notes')
def view_notes():
    page = request.args.get('page', 1, type=int)
    subject_id = request.args.get('subject')
    semester = request.args.get('semester')
    search = request.args.get('search')
    sort_by = request.args.get('sort', 'newest')
    
    query = Note.query.filter_by(is_approved=True)
    
    # Apply filters
    if subject_id:
        query = query.filter_by(subject_id=subject_id)
    if semester:
        query = query.filter_by(semester=semester)
    if search:
        query = query.filter(or_(
            Note.title.contains(search),
            Note.description.contains(search)
        ))
    
    # Apply sorting
    if sort_by == 'newest':
        query = query.order_by(desc(Note.upload_date))
    elif sort_by == 'downloads':
        query = query.order_by(desc(Note.download_count))
    elif sort_by == 'rating':
        # This is a simplified rating sort - in production you'd want to join with ratings table
        query = query.order_by(desc(Note.id))  # Placeholder
    
    notes = query.paginate(page=page, per_page=12, error_out=False)
    subjects = Subject.query.all()
    
    return render_template('view_notes.html', 
                         notes=notes, 
                         subjects=subjects,
                         current_subject=subject_id,
                         current_semester=semester,
                         current_search=search,
                         current_sort=sort_by)

@app.route('/note/<int:note_id>')
def note_detail(note_id):
    note = Note.query.get_or_404(note_id)
    
    if not note.is_approved:
        if 'user_id' not in session or (session['user_id'] != note.user_id and not session.get('is_admin')):
            abort(404)
    
    comments = Comment.query.filter_by(note_id=note_id).order_by(desc(Comment.created_at)).all()
    user_rating = None
    
    if 'user_id' in session:
        user_rating = Rating.query.filter_by(user_id=session['user_id'], note_id=note_id).first()
    
    return render_template('note_detail.html', 
                         note=note, 
                         comments=comments, 
                         user_rating=user_rating)

@app.route('/download/<int:note_id>')
def download_note(note_id):
    if 'user_id' not in session:
        flash('Please log in to download notes.', 'error')
        return redirect(url_for('login'))
    
    note = Note.query.get_or_404(note_id)
    
    if not note.is_approved:
        abort(404)
    
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], note.filename)
    
    if not os.path.exists(file_path):
        flash('File not found!', 'error')
        return redirect(url_for('view_notes'))
    
    # Record download
    download = Download()
    download.user_id = session['user_id']
    download.note_id = note_id
    db.session.add(download)
    
    # Increment download count
    note.download_count += 1
    db.session.commit()
    
    return send_file(file_path, as_attachment=True, download_name=note.original_filename)

@app.route('/rate_note', methods=['POST'])
def rate_note():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please log in to rate notes.'})
    
    note_id = request.form.get('note_id')
    score_str = request.form.get('score', '').strip()
    
    if not note_id or not score_str:
        return jsonify({'success': False, 'message': 'Missing rating data.'})
    
    try:
        score = int(score_str)
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid rating score.'})
    
    if score < 1 or score > 5:
        return jsonify({'success': False, 'message': 'Rating must be between 1 and 5.'})
    
    # Check if user already rated this note
    existing_rating = Rating.query.filter_by(user_id=session['user_id'], note_id=note_id).first()
    
    if existing_rating:
        existing_rating.score = score
    else:
        rating = Rating()
        rating.user_id = session['user_id']
        rating.note_id = note_id
        rating.score = score
        db.session.add(rating)
    
    db.session.commit()
    
    # Calculate new average rating
    note = Note.query.get(note_id)
    avg_rating = note.average_rating() if note and hasattr(note, 'average_rating') else 0
    
    return jsonify({
        'success': True, 
        'message': 'Rating submitted successfully!',
        'average_rating': round(avg_rating, 1)
    })

@app.route('/add_comment', methods=['POST'])
def add_comment():
    if 'user_id' not in session:
        flash('Please log in to add comments.', 'error')
        return redirect(url_for('login'))
    
    note_id = request.form['note_id']
    content = request.form['content']
    
    if content.strip():
        comment = Comment()
        comment.user_id = session['user_id']
        comment.note_id = note_id
        comment.content = content
        db.session.add(comment)
        db.session.commit()
        flash('Comment added successfully!', 'success')
    else:
        flash('Comment cannot be empty!', 'error')
    
    return redirect(url_for('note_detail', note_id=note_id))

# Admin Authentication Routes
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        # Check if user exists and is admin
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password) and user.is_admin:
            session['user_id'] = user.id
            session['is_admin'] = True
            flash('Admin login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid admin credentials!', 'error')
    
    return render_template('admin/login.html')

@app.route('/admin')
@app.route('/admin/')
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'user_id' not in session or not session.get('is_admin'):
        flash('Access denied. Admin login required.', 'error')
        return redirect(url_for('admin_login'))
    
    # Dashboard statistics
    total_users = User.query.count()
    total_notes = Note.query.count()
    approved_notes = Note.query.filter_by(is_approved=True).count()
    pending_notes = Note.query.filter_by(is_approved=False).count()
    blocked_users = User.query.filter_by(is_blocked=True).count()
    total_downloads = db.session.query(func.sum(Note.download_count)).scalar() or 0
    total_ratings = Rating.query.count()
    
    # Recent activity
    recent_notes = Note.query.order_by(desc(Note.upload_date)).limit(5).all()
    recent_users = User.query.order_by(desc(User.created_at)).limit(5).all()
    recent_ratings = Rating.query.order_by(desc(Rating.date)).limit(5).all()
    
    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         total_notes=total_notes,
                         approved_notes=approved_notes,
                         pending_notes=pending_notes,
                         blocked_users=blocked_users,
                         total_downloads=total_downloads,
                         total_ratings=total_ratings,
                         recent_notes=recent_notes,
                         recent_users=recent_users,
                         recent_ratings=recent_ratings)

@app.route('/admin/notes')
def admin_notes():
    if 'user_id' not in session or not session.get('is_admin'):
        abort(403)
    
    # Filters
    status_filter = request.args.get('status', '')
    subject_filter = request.args.get('subject', '')
    search_query = request.args.get('search', '')
    
    # Base query
    query = Note.query
    
    # Apply filters
    if status_filter == 'approved':
        query = query.filter_by(is_approved=True)
    elif status_filter == 'pending':
        query = query.filter_by(is_approved=False)
    
    if subject_filter:
        query = query.filter_by(subject_id=subject_filter)
    
    if search_query:
        query = query.filter(or_(
            Note.title.contains(search_query),
            Note.description.contains(search_query)
        ))
    
    notes = query.order_by(desc(Note.upload_date)).all()
    subjects = Subject.query.all()
    
    return render_template('admin/notes.html',
                         notes=notes,
                         subjects=subjects,
                         current_status=status_filter,
                         current_subject=subject_filter,
                         current_search=search_query)

@app.route('/admin/users')
def admin_users():
    if 'user_id' not in session or not session.get('is_admin'):
        abort(403)
    
    # Filters
    status_filter = request.args.get('status', '')
    search_query = request.args.get('search', '')
    
    # Base query
    query = User.query
    
    # Apply filters
    if status_filter == 'blocked':
        query = query.filter_by(is_blocked=True)
    elif status_filter == 'active':
        query = query.filter_by(is_blocked=False)
    elif status_filter == 'admin':
        query = query.filter_by(is_admin=True)
    
    if search_query:
        query = query.filter(or_(
            User.username.contains(search_query),
            User.email.contains(search_query)
        ))
    
    users = query.order_by(desc(User.created_at)).all()
    
    return render_template('admin/users.html',
                         users=users,
                         current_status=status_filter,
                         current_search=search_query)

@app.route('/admin/feedback')
def admin_feedback():
    if 'user_id' not in session or not session.get('is_admin'):
        abort(403)
    
    # Get all ratings with comments
    ratings = Rating.query.filter(Rating.comment.isnot(None)).order_by(desc(Rating.date)).all()
    
    return render_template('admin/feedback.html', ratings=ratings)

@app.route('/admin/analytics')
def admin_analytics():
    if 'user_id' not in session or not session.get('is_admin'):
        abort(403)
    
    # Download analytics
    downloads_by_date = db.session.query(
        func.date(Download.download_date).label('date'),
        func.count(Download.id).label('count')
    ).group_by(func.date(Download.download_date)).order_by('date').all()
    
    # Top downloaded notes
    top_notes = Note.query.filter_by(is_approved=True).order_by(desc(Note.download_count)).limit(10).all()
    
    # Zero download notes
    zero_downloads = Note.query.filter_by(is_approved=True, download_count=0).all()
    
    # Notes by subject
    notes_by_subject = db.session.query(
        Subject.name,
        func.count(Note.id).label('count')
    ).join(Note).filter(Note.is_approved == True).group_by(Subject.name).all()
    
    return render_template('admin/analytics.html',
                         downloads_by_date=downloads_by_date,
                         top_notes=top_notes,
                         zero_downloads=zero_downloads,
                         notes_by_subject=notes_by_subject)

@app.route('/admin/settings', methods=['GET', 'POST'])
def admin_settings():
    if 'user_id' not in session or not session.get('is_admin'):
        abort(403)
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'change_password':
            current_password = request.form['current_password']
            new_password = request.form['new_password']
            confirm_password = request.form['confirm_password']
            
            user = User.query.get(session['user_id'])
            
            if not check_password_hash(user.password_hash, current_password):
                flash('Current password is incorrect!', 'error')
            elif new_password != confirm_password:
                flash('New passwords do not match!', 'error')
            else:
                user.password_hash = generate_password_hash(new_password)
                db.session.commit()
                flash('Password changed successfully!', 'success')
    
    return render_template('admin/settings.html')

# Admin Action Routes
@app.route('/admin/approve_note/<int:note_id>')
def approve_note(note_id):
    if 'user_id' not in session or not session.get('is_admin'):
        abort(403)
    
    note = Note.query.get_or_404(note_id)
    note.is_approved = True
    db.session.commit()
    
    # Send approval email to note author
    try:
        send_email(
            note.author.email,
            'Your note has been approved!',
            f'Hello {note.author.username},\n\nYour note "{note.title}" has been approved and is now visible to all users.\n\nBest regards,\nEduNotesPro Team'
        )
    except Exception as e:
        app.logger.error(f"Failed to send approval email: {e}")
    
    flash(f'Note "{note.title}" approved successfully!', 'success')
    return redirect(request.referrer or url_for('admin_dashboard'))

@app.route('/admin/block_user/<int:user_id>')
def block_user(user_id):
    if 'user_id' not in session or not session.get('is_admin'):
        abort(403)
    
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash('Cannot block admin users!', 'error')
        return redirect(request.referrer or url_for('admin_users'))
    
    user.is_blocked = True
    db.session.commit()
    flash(f'User "{user.username}" blocked successfully!', 'success')
    return redirect(request.referrer or url_for('admin_users'))

@app.route('/admin/unblock_user/<int:user_id>')
def unblock_user(user_id):
    if 'user_id' not in session or not session.get('is_admin'):
        abort(403)
    
    user = User.query.get_or_404(user_id)
    user.is_blocked = False
    db.session.commit()
    flash(f'User "{user.username}" unblocked successfully!', 'success')
    return redirect(request.referrer or url_for('admin_users'))

@app.route('/admin/delete_user/<int:user_id>')
def delete_user(user_id):
    if 'user_id' not in session or not session.get('is_admin'):
        abort(403)
    
    user = User.query.get_or_404(user_id)
    if user.is_admin:
        flash('Cannot delete admin users!', 'error')
        return redirect(request.referrer or url_for('admin_users'))
    
    username = user.username
    db.session.delete(user)
    db.session.commit()
    flash(f'User "{username}" deleted successfully!', 'success')
    return redirect(request.referrer or url_for('admin_users'))

@app.route('/admin/delete_feedback/<int:rating_id>')
def delete_feedback(rating_id):
    if 'user_id' not in session or not session.get('is_admin'):
        abort(403)
    
    rating = Rating.query.get_or_404(rating_id)
    rating.comment = None  # Remove comment but keep rating
    db.session.commit()
    flash('Feedback deleted successfully!', 'success')
    return redirect(request.referrer or url_for('admin_feedback'))

@app.route('/admin/delete_note/<int:note_id>')
def delete_note(note_id):
    if 'user_id' not in session or not session.get('is_admin'):
        abort(403)
    
    note = Note.query.get_or_404(note_id)
    
    # Delete file from filesystem
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], note.filename)
    if os.path.exists(file_path):
        os.remove(file_path)
    
    # Delete note from database (cascading will handle related records)
    title = note.title
    db.session.delete(note)
    db.session.commit()
    
    flash(f'Note "{title}" deleted successfully!', 'success')
    return redirect(request.referrer or url_for('admin_dashboard'))



@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash('Please log in to view profile.', 'error')
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    return render_template('profile.html', user=user)

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500
