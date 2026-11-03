from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, PasswordField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, Length


class BaseForm(FlaskForm):
    class Meta:
        csrf = True


class SubmitForm(BaseForm):
    name = StringField("Name", validators=[DataRequired(), Length(max=100)])
    category = SelectField("Category", choices=[], validators=[DataRequired()])
    image = TextAreaField("Image Path", validators=[Length(max=200)])
    submit = SubmitField("Submit")

class AdminForm(BaseForm):
    action = StringField("Action")
    category = StringField("Category")
    entry_id = StringField("Entry ID")
    submit = SubmitField("Submit")
