
from flask import Flask, render_template, request, redirect, url_for, flash, abort
from flask_login import (
    login_user, logout_user, login_required, current_user
)
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import or_
from flask_migrate import Migrate

from extensions import db, login_manager
from models import User, Post, Comment, Tag


app = Flask(__name__)

app.config["SECRET_KEY"] = "replace-this-with-a-long-random-secret"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///blog.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = "login"

migrate = Migrate(app, db)


# POST FORM
class PostForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired()])
    content = TextAreaField("Content", validators=[DataRequired()])
    submit = SubmitField("Publish")


# LOAD USER
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# UPDATE POST TAGS
def update_post_tags(post, tags_text):
    tag_names = set(
        name.strip()
        for name in (tags_text or "").split(",")
        if name.strip()
    )

    tags = []

    for name in tag_names:
        tag = Tag.query.filter(
            db.func.lower(Tag.name) == name.lower()
        ).first()

        if not tag:
            tag = Tag(name=name)
            db.session.add(tag)
            db.session.flush()

        tags.append(tag)

    post.tags = tags


# HOME PAGE WITH SEARCH, TAG FILTERING AND PAGINATION
@app.route("/")
def home():
    search_query = request.args.get("q", "").strip()
    tag_filter = request.args.get("tag", "").strip()
    page = request.args.get("page", 1, type=int)

    posts_query = Post.query

    if search_query:
        pattern = f"%{search_query}%"

        posts_query = posts_query.filter(
            or_(
                Post.title.ilike(pattern),
                Post.content.ilike(pattern)
            )
        )

    if tag_filter:
        posts_query = posts_query.filter(
            Post.tags.any(Tag.name == tag_filter)
        )

    tags = Tag.query.order_by(Tag.name).all()

    posts = posts_query.order_by(
        Post.date_created.desc()
    ).paginate(
        page=page,
        per_page=5,
        error_out=False
    )

    return render_template(
        "index.html",
        posts=posts,
        search_query=search_query,
        tags=tags,
        tag_filter=tag_filter
    )


# REGISTER
@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not username or not email or not password:
            flash("Please complete all fields.", "error")

        elif len(username) < 3:
            flash("Username must contain at least 3 characters.", "error")

        elif len(password) < 8:
            flash("Password must contain at least 8 characters.", "error")

        elif User.query.filter_by(username=username).first():
            flash("Username already registered.", "error")

        elif User.query.filter_by(email=email).first():
            flash("Email already registered.", "error")

        else:
            user = User(
                username=username,
                email=email,
                password=generate_password_hash(password)
            )

            db.session.add(user)
            db.session.commit()

            flash("Account created successfully.", "success")
            return redirect(url_for("login"))

    return render_template("register.html")


# LOGIN
@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            flash("Login successful.", "success")
            return redirect(url_for("home"))

        flash("Incorrect email or password.", "error")

    return render_template("login.html")


# LOGOUT
@app.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have logged out.", "success")
    return redirect(url_for("home"))


# CREATE POST
@app.route("/post/new", methods=["GET", "POST"])
@login_required
def create_post():
    form = PostForm()

    if form.validate_on_submit():
        post = Post(
            title=form.title.data.strip(),
            content=form.content.data.strip(),
            user_id=current_user.id
        )

        db.session.add(post)

        update_post_tags(
            post,
            request.form.get("tags", "")
        )

        db.session.commit()

        flash("Your blog post has been published.", "success")

        return redirect(
            url_for("post_detail", post_id=post.id)
        )

    return render_template("create_post.html", form=form)


# VIEW POST
@app.route("/post/<int:post_id>")
def post_detail(post_id):
    post = Post.query.get_or_404(post_id)

    return render_template(
        "post_detail.html",
        post=post
    )


# EDIT POST
@app.route("/post/<int:post_id>/edit", methods=["GET", "POST"])
@login_required
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)

    if post.user_id != current_user.id:
        abort(403)

    form = PostForm(obj=post)

    if form.validate_on_submit():
        post.title = form.title.data.strip()
        post.content = form.content.data.strip()

        update_post_tags(
            post,
            request.form.get("tags", "")
        )

        db.session.commit()

        flash("Post updated successfully.", "success")

        return redirect(
            url_for("post_detail", post_id=post.id)
        )

    return render_template(
        "edit_post.html",
        post=post,
        form=form
    )


# DELETE POST
@app.route("/post/<int:post_id>/delete", methods=["POST"])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)

    if post.user_id != current_user.id:
        abort(403)

    db.session.delete(post)
    db.session.commit()

    flash("Post deleted successfully.", "success")

    return redirect(url_for("home"))


# ADD COMMENT
@app.route("/post/<int:post_id>/comment", methods=["POST"])
@login_required
def add_comment(post_id):
    post = Post.query.get_or_404(post_id)

    content = request.form.get("content", "").strip()

    if content:
        comment = Comment(
            content=content,
            user_id=current_user.id,
            post_id=post.id
        )

        db.session.add(comment)
        db.session.commit()

        flash("Comment added.", "success")

    else:
        flash("Comment cannot be empty.", "error")

    return redirect(
        url_for("post_detail", post_id=post.id)
    )


# DELETE COMMENT
@app.route("/comment/<int:comment_id>/delete", methods=["POST"])
@login_required
def delete_comment(comment_id):
    comment = Comment.query.get_or_404(comment_id)

    if (
        comment.user_id != current_user.id
        and comment.post.user_id != current_user.id
    ):
        abort(403)

    post_id = comment.post_id

    db.session.delete(comment)
    db.session.commit()

    flash("Comment deleted.", "success")

    return redirect(
        url_for("post_detail", post_id=post_id)
    )


# USER PROFILE
@app.route("/profile/<int:user_id>")
@login_required
def profile(user_id):
    user = User.query.get_or_404(user_id)

    return render_template(
        "profile.html",
        user=user
    )


# ERROR HANDLERS
@app.errorhandler(403)
def forbidden(error):
    return render_template(
        "error.html",
        code=403,
        message="You do not have permission to do that."
    ), 403


@app.errorhandler(404)
def not_found(error):
    return render_template(
        "error.html",
        code=404,
        message="The page or post was not found."
    ), 404


# RUN APPLICATION
if __name__ == "__main__":
    app.run(debug=True)
