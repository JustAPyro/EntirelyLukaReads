from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired, EqualTo, Length


class SignUpForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Password', validators=[
        DataRequired(), Length(min=6, message="At least 6 characters")
    ])
    confirm = PasswordField('Confirm Password', validators=[
        DataRequired(), EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Sign Up')


from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, SubmitField
from wtforms.validators import DataRequired


class LogInForm(FlaskForm):
    email = StringField('Email', validators=[
        DataRequired(),
    ])
    password = PasswordField('Password', validators=[
        DataRequired()
    ])
    submit = SubmitField('Log In')

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField, FileRequired
from wtforms import (FieldList, FileField, FormField, StringField, SubmitField,
                     TextAreaField)
from wtforms.validators import DataRequired, Length


class ChapterForm(FlaskForm):
    title = StringField('Chapter Title', validators=[DataRequired(), Length(max=255)])


class BookForm(FlaskForm):
    title = StringField('Title', validators=[
        DataRequired(), Length(min=1, max=100)
    ])

    author = StringField('Author', validators=[
        DataRequired(), Length(min=1, max=100)
    ])

    description = TextAreaField('Description', validators=[DataRequired()])

    cover = FileField('Cover Image', validators=[
        FileAllowed(['jpg', 'jpeg', 'png', 'webp'], 'Image files only!')
    ])

    chapters = FieldList(FormField(ChapterForm))

    submit = SubmitField('Add Book')

