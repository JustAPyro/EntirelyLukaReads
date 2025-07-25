import os

import boto3
from flask import Blueprint, abort, flash, jsonify, render_template, request
from flask_login import current_user, login_required, login_user
from flask_wtf.csrf import CSRFError
from werkzeug.utils import secure_filename

from app import db
from app.database import Books, Progress, Segment, User, upload_to_r2
from app.forms import BookForm, BookPermissionForm, LogInForm, SignUpForm

app = Blueprint('main', __name__)

from flask import redirect, url_for
from flask_login import current_user, logout_user


@app.context_processor
def inject_user():
    return dict(current_user=current_user)



@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    flash(f"CSRF error: {e.description}", "danger")
    return redirect(request.url)


#-#-#-#-#-#-#-#-#-#- Auth Pages -#-#-#-#-#-#-#-#-#-#

@app.route('/log-in.html', methods=['GET', 'POST'])
def log_in():
    form = LogInForm()

    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        password = form.password.data

        user = db.session.query(User).filter_by(email=email).first()

        if not user:
            flash('No account found with that email.', category='error')
            return render_template('log_in.html', form=form), 403

        if not user.check_pass(password):
            flash('Incorrect password.', category='error')
            return render_template('log_in.html', form=form), 403

        login_user(user)
        flash(f"Welcome back, {user.email}!", category='success')

        next_page = request.args.get('next')
        return redirect(next_page or url_for('main.home'))

    return render_template('log_in.html', form=form)

@app.route('/sign-up.html', methods=['POST', 'GET'])
def sign_up():
    form = SignUpForm()

    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        password = form.password.data


        if db.session.query(User).filter_by(email=email).first():
            flash('Email already in use.', category='error')
            return render_template('sign_up.html', form=form), 403

        # Create and store new user
        user = User(email=email, password=User.hash_pass(password))
        db.session.add(user)
        db.session.commit()

        login_user(user)

        next_url = request.args.get('next')
        return redirect(next_url or url_for('main.home'))

    return render_template('sign_up.html', form=form)

@app.route('/log-out.html')
def log_out():
    logout_user()
    return redirect(url_for('main.log_in'))

#-#-#-#-#-#-#-#-#-#- End -#-#-#-#-#-#-#-#-#-#

@app.route('/')
def home():
    return render_template('home.html')


@app.route('/test.html')
def test():
    return render_template('test.html')

#-#-#-#-#-#-#-#-#-#- Start Media -#-#-#-#-#-#-#-#-#-#

@app.route('/books/add.html', methods=['GET', 'POST'])
@login_required
def add_books():
    form = BookForm()

    if form.validate_on_submit():
        book = Books(
            producer_id=current_user.id,
            title = form.data.get('title'),
            author = form.data.get('author'))
        db.session.add(book)
        db.session.commit()
        flash(f'Created production of "{book.title}"')

    else:
        # Flash all form errors
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"{form[field].label.text}: {error}", "danger")

    return render_template('books_edit.html', form=form, zip=zip, editing=False)


@app.route('/books/<int:book_id>/permissions.html', methods=['GET', 'POST'])
@login_required
def books_permissions(book_id: int):

    book_form = BookPermissionForm()
    
    book = db.get_or_404(Books, book_id)
    if book.producer_id != current_user.id:
        abort(403)

    if book_form.validate_on_submit():
        email = book_form.data.get('email')
        user = db.session.query(User).filter_by(email=email).first()
        if not user:
            flash(f'There is no user with the email "{email}"')
        else:
            user.available.append(book)
            db.session.commit()


    return render_template('books_permissions.html', book=book, book_form=book_form)




@app.route('/books/<int:book_id>/edit.html', methods=['GET', 'POST'])
@login_required
def books_edit(book_id: int):

    book = db.get_or_404(Books, book_id)
    if book.producer_id != current_user.id:
        abort(403)

    book_form = BookForm()

    if book_form.validate_on_submit():
        book.description = book_form.data.get('description')

        for i, chapter_data in enumerate(book_form.chapters.data):

            chapter_id = chapter_data.get('segment_id')
            title = chapter_data.get('title')

            print(book_form.chapters.data)
            if not chapter_id:
                db.session.add(Segment(
                    book_id = book.id,
                    title=title,
                    position = len(book.chapters),
                    commentary=False
                ))

                
        flash('Production updated!')

        # flash what was updated
        db.session.commit()
        return redirect(url_for('main.books_edit', book_id=book_id))
    else:
        book_form = BookForm(obj=book)
        book_form.process_obj(book)
        


    recorded_flags = []
    for chapter in book.chapters:
        entry = book_form.chapters.append_entry({
            'title': chapter.title
        })
        recorded_flags.append(bool(chapter.audio_url))


    return render_template('books_edit.html', form=book_form, book=book, recorded_flags=recorded_flags, zip=zip)

@app.route('/books.html')
@login_required
def books():


    return render_template('books.html',
                           produced=current_user.produced,
                           available=current_user.available)


@app.route('/books/<int:book_id>.html')
def book(book_id):

    progress = exists = db.session.query(Progress).filter(
        Progress.user_id == current_user.id,
        Progress.book_id == book_id
    ).first()

    if not progress:

        fs_id = db.session.query(Segment).filter(Segment.book_id == book_id).order_by(Segment.position.asc()).first().id

        progress = Progress(
            user_id=current_user.id,
            book_id=book_id,
            chapter_id=fs_id,
            timestamp=0,
        )
        db.session.add(progress)
        db.session.commit()

    segments = db.session.query(Segment).filter_by(book_id=book_id).order_by(Segment.position).all()
    book = db.session.query(Books).filter_by(id=book_id).first()

    return render_template('book_reader.html', book=book, segments=segments, progress=progress)

@app.route('/update_progress', methods=['POST'])
@login_required
def update_progress():
    data = request.get_json()
    book_id = data.get('book_id')
    chapter_id = int(data.get('chapter_id'))
    timestamp = data.get('timestamp')

    if not (book_id and chapter_id and timestamp is not None):
        return jsonify({'error': 'Invalid data'}), 400

    progress = db.session.query(Progress).filter_by(
        user_id=current_user.id,
        book_id=book_id,
    ).first()

    progress.chapter_id = chapter_id
    progress.timestamp = timestamp

    db.session.commit()
    return jsonify({'success': True})

#-#-#-#-#-#-#-#-#-#- End Media -#-#-#-#-#-#-#-#-#-#

# CHAPTER api

# Delete Chapter
@app.route('/api/chapter/<int:chapter_id>.json', methods=['DELETE'])
@login_required
def chapter_api_delete(chapter_id: int):

    chapter = db.get_or_404(Segment, chapter_id)
    if chapter.book.producer_id != current_user.id:
        abort(403)

    db.session.delete(chapter)
    db.session.commit()
    return  jsonify({'success': True, 'message': 'Chapter deleted'}), 200

# Upload a chapter audio
@app.route('/api/chapter/<int:chapter_id>/upload.json', methods=['POST'])
@login_required
def chapter_api_upload(chapter_id: int):
    file = request.files.get('audio')

    if not file or not chapter_id:
        return jsonify(success=False, error='Missing data'), 400

    chapter = db.get_or_404(Segment, chapter_id)
    if chapter.book.producer_id != current_user.id:
        abort(403)
 
    # Save the file
    upload_to_r2(file, chapter)
    db.session.commit()

    return jsonify(success=True, audio_url=chapter.audio_url)

# Lock or unlock a chapter
@app.route('/chapters/<int:chapter_id>/access.json', methods=['POST'])
@login_required
def toggle_chapter_access(chapter_id: int):
    data = request.get_json()
    user_id = data.get('user_id')
    action = data.get('action')  # 'lock' or 'unlock'

    if not user_id or action not in {'lock', 'unlock'}:
        return jsonify({'error': 'Invalid request'}), 400

    segment = db.session.get(Segment, chapter_id)
    user = db.session.get(User, user_id)

    if not segment or not user:
        return jsonify({'error': 'Segment or user not found'}), 404

    # Check current user is the producer of this book
    if segment.book.producer_id != current_user.id:
        abort(403)

    if action == 'unlock':
        if user not in segment.users:
            segment.users.append(user)
    else:  # lock
        if user in segment.users:
            segment.users.remove(user)

    db.session.commit()
    return jsonify({'success': True, 'status': action})



@app.route('/reader/')
def reader():
    return render_template('reader.html')

@app.route('/book/<int:book_id>/chapter/<int:chapter_id>')
def book_page(book_id, chapter_id):
    book = {
        'id': book_id,
        'title': 'The Way Of Kings',
        'author': 'Brandon Sanderson',
        'description': 'A gentle tale read chapter by chapter.',
        'cover_image': 'covers/quiet-forest.jpg'
    }

    chips = [
        'Dedication',
        'Prelude to the Stormlight Archive',
        'Prologue: To Kill',
        'Chapter 1: Stormblessed',
        'Chapter 2: Honor is Dead',
        'Chapter 3: City of Bells',
        'Chapter 4: The Shattered Plains',
        'Chapter 5: Heretic',
        'Chapter 6: Bridge Four',
        'Chapter 7: Anything Reasonable',
        'Chapter 8: Nearer the Flame',
        'Chapter 9: Damnation',
        'Chapter 10: Stories of Surgeons',
        'Chapter 11: Droplets',

        'Interlude I-1: Ishikk',
        'Interlude I-2: Nan Balat',
        'Interlude I-3: The Glory of Ignorance',

        'Chapter 12: Unity',
        'Chapter 13: Ten Heartbeats',
        'Chapter 14: Payday',
        'Chapter 15: The Decoy',
        'Chapter 16: Cocoons',
        'Chapter 17: A Bloody Red Sunset',
        'Chapter 18: Highprince of War',
        'Chapter 19: Starfalls',
        'Chapter 20: Scarlet',
        'Chapter 21: Why Men Lie',
        'Chapter 22: Eyes, Hands, or Spheres',
        'Chapter 23: Many Uses',
        'Chapter 24: The Gallery of Maps',
        'Chapter 25: The Butcher',
        'Chapter 26: Stillness',
        'Chapter 27: Chasm Duty',
        'Chapter 28: Decision',

        'Interlude I-4: Rysn',
        'Interlude I-5: Axies the Collector',
        'Interlude I-6: A Work of Art',

        'Chapter 29: Errorgance',
        'Chapter 30: Darkness Unseen',
        'Chapter 31: Beneath the Skin',
        'Chapter 32: Side Carry',
        'Chapter 33: Cymatics',
        'Chapter 34: Stormwall',
        'Chapter 35: A Light By Which to See',
        'Chapter 36: The Lesson',
        'Chapter 37: Sides',
        'Chapter 38: Envisager',
        'Chapter 39: Burned Into Her',
        'Chapter 40: Eyes of Red and Blue',
        'Chapter 41: Of Alds and Milp',
        'Chapter 42: Beggars and Barmaids',
        'Chapter 43: The Wretch',
        'Chapter 44: The Weeping',
        'Chapter 45: Shadesmar',
        'Chapter 46: Child of Tanavast',
        'Chapter 47: Stormblessings',
        'Chapter 48: Strawberry',
        'Chapter 49: To Care',
        'Chapter 50: Backbreaker Powder',
        'Chapter 51: Sas Nahn',
    ]

    chapters = [
        {'id': 1, 'title': 'Chapter 1: The Awakening', 'filename': 'quiet-forest-ch1.mp3'},
        {'id': 2, 'title': 'Chapter 2: The Path', 'filename': 'quiet-forest-ch2.mp3'},
        {'id': 3, 'title': 'Chapter 3: Into the Trees', 'filename': 'quiet-forest-ch3.mp3'},
    ]

    current = next(ch for ch in chapters if ch['id'] == chapter_id)
    current['description'] = 'In this chapter, we begin our journey...'

    return render_template('reader.html',
                           book=book,
                           chapters=chapters,
                           chaps=chips,
                           current_chapter=current)


