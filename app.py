from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from flask_sqlalchemy import SQLAlchemy
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config
from sqlalchemy import text
from uuid import uuid4
from werkzeug.utils import secure_filename
from functools import wraps
from flask_login import LoginManager, UserMixin, login_required, current_user


import os
import json
import datetime

app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy(app)
with app.app_context():
    db.create_all()

s = URLSafeTimedSerializer(app.config['SECRET_KEY'])


UPLOAD_FOLDER = os.path.join("static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
ALLOWED_EXT = {'png', 'jpg', 'jpeg', 'gif'}

ADMIN_EMAIL = "tulasiranamagar37@gmail.com"

login_manager = LoginManager()
login_manager.login_view = "login"  
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))



def send_email(subject, recipient, body):
    """Fake email sender for development (prints in console)."""
    print("\n--- EMAIL DEBUG ---")
    print("To:", recipient)
    print("Subject:", subject)
    print("Body:", body)
    print("--- END EMAIL ---\n")


def save_images(files_list):
    """Save up to 5 images and return filenames list"""
    saved = []
    for f in files_list[:5]:
        if f and f.filename:
            filename = f"{int(datetime.datetime.now().timestamp())}_{secure_filename(f.filename)}"
            path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            try:
                f.save(path)
                saved.append(filename)
            except Exception as e:
                print("save_images error:", e)
    return saved


def login_required(f):
    """Simple decorator to ensure a user is logged in."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("user_id"):
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

@app.context_processor
def inject_now():
    return {'current_year': datetime.datetime.now().year}


@app.context_processor
def inject_user():
   
    return dict(User=globals().get('User', None))

class Contact(db.Model):
    __tablename__ = "contacts"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)


class User(db.Model, UserMixin):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(20))
    email_verified = db.Column(db.Boolean, default=False)
    is_admin = db.Column(db.Boolean, default=False)
    profile_pic = db.Column(db.String(255), default="default_profile.png")

    properties = db.relationship("Property", back_populates="owner", lazy=True)
    agents = db.relationship("Agent", back_populates="user", lazy=True)
    testimonials = db.relationship("Testimonial", back_populates="user", lazy=True)
    bookings = db.relationship("Booking", back_populates="buyer", lazy=True)

    def __repr__(self):
        return f"<User {self.id} - {self.email}>"


class Agent(db.Model):
    __tablename__ = "agents"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True)
    license_no = db.Column(db.String(100), unique=True, nullable=False)
    experience = db.Column(db.Integer, nullable=True)
    verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    user = db.relationship("User", backref="agent", uselist=False)

    def __repr__(self):
        return f"<Agent {self.id} - User {self.user_id}>"


class Property(db.Model):
    __tablename__ = "properties"
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"))
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    price = db.Column(db.Float)
    property_type = db.Column(db.String(50))
    sale_type = db.Column(db.String(50))
    location = db.Column(db.String(200))
    images = db.Column(db.Text)
    seller_type = db.Column(db.String(50), default="Individual")
    approved = db.Column(db.Boolean, default=False)   
    featured = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default="Available")  
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    owner = db.relationship("User", back_populates="properties", foreign_keys=[owner_id])
    bookings = db.relationship("Booking", back_populates="property", lazy=True)

    def __repr__(self):
        return f"<Property {self.id} - {self.title}>"


class Testimonial(db.Model):
    __tablename__ = "testimonials"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    message = db.Column(db.Text)
    rating = db.Column(db.Integer, default=5)
    approved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    user = db.relationship("User", back_populates="testimonials")

    def __repr__(self):
        return f"<Testimonial {self.id} - User {self.user_id}>"


class Booking(db.Model):
    __tablename__ = "bookings"
    id = db.Column(db.Integer, primary_key=True)
    property_id = db.Column(db.Integer, db.ForeignKey("properties.id", ondelete="CASCADE"))
    buyer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    status = db.Column(db.String(20), default="Pending")  
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    property = db.relationship("Property", back_populates="bookings", foreign_keys=[property_id])
    buyer = db.relationship("User", back_populates="bookings", foreign_keys=[buyer_id])

    def __repr__(self):
        return f"<Booking {self.id} property={self.property_id} buyer={self.buyer_id}>"


def ensure_status_column():
    """
    Lightweight check: if `status` column missing in `properties` table,
    attempt to add it with ALTER TABLE.
    """
    try:
        engine = db.engine
        dialect = engine.dialect.name.lower()
        with engine.connect() as conn:
            if dialect == "sqlite":
                res = conn.execute(text("PRAGMA table_info(properties);"))
                cols = [row[1] for row in res.fetchall()]
                if 'status' not in cols:
                    conn.execute(text("ALTER TABLE properties ADD COLUMN status TEXT DEFAULT 'Available';"))
            else:
                try:
                    q = text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name='properties' AND column_name='status' AND table_schema=:schema;"
                    )
                    r = conn.execute(q, {"schema": app.config.get('SQLALCHEMY_DATABASE_URI').rsplit('/', 1)[-1]}).fetchone()
                    if not r:
                        conn.execute(text("ALTER TABLE properties ADD COLUMN status VARCHAR(20) DEFAULT 'Available';"))
                except Exception:
                    try:
                        conn.execute(text("ALTER TABLE properties ADD COLUMN status VARCHAR(20) DEFAULT 'Available'"))
                    except Exception:
                        pass
    except Exception as e:
        print("Auto-migrate: could not ensure status column:", e)


@app.template_filter('load_json')
def load_json_filter(s):
    try:
        return json.loads(s) if s else []
    except Exception:
        return []


def _user_property_base_query(user_id):
    return Property.query.filter_by(owner_id=user_id)


@app.route('/')
def index():
    top_offers = (
        Property.query
        .filter_by(approved=True, status='Available')
        .order_by(Property.created_at.desc(), Property.price.asc())
        .limit(4)
        .all()
    )

    testimonials = (
        Testimonial.query
        .filter_by(approved=True)
        .order_by(Testimonial.created_at.desc())
        .limit(5)
        .all()
    )

    return render_template('index.html', top_offers=top_offers, testimonials=testimonials)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password")
        phone = request.form.get("phone")

        if not email or not password or not name:
            flash("Name, email and password are required.", "danger")
            return redirect(url_for("signup"))

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("This email is already registered. Please log in instead.", "danger")
            return redirect(url_for("login"))

        hashed_pw = generate_password_hash(password)
        is_admin_flag = True if (email and email.strip().lower() == ADMIN_EMAIL) else False

        new_user = User(
            name=name,
            email=email,
            password=hashed_pw,
            phone=phone,
            email_verified=False,
            is_admin=is_admin_flag
        )

        try:
            db.session.add(new_user)
            db.session.commit()
            flash("Signup successful! Please log in.", "success")
            return redirect(url_for("login"))
        except Exception as e:
            db.session.rollback()
            flash(f"Error creating account: {e}", "danger")

    return render_template("signup.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            if user.email == ADMIN_EMAIL and not user.is_admin:
                user.is_admin = True
                try:
                    db.session.commit()
                except Exception:
                    db.session.rollback()

            session["user_id"] = user.id
            session["user_name"] = user.name
            session["is_admin"] = user.is_admin

            flash(f"Welcome back, {user.name}!", "success")
            if user.is_admin:
                return redirect(url_for("admin_dashboard"))
            else:
                return redirect(url_for("dashboard"))
        else:
            flash("Invalid email or password. Please try again.", "danger")

    return render_template("login.html")


@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@app.route('/dashboard/<status>')
@login_required
def dashboard(status='all'):
    user_id = session['user_id']
    user = User.query.get_or_404(user_id)

    query = _user_property_base_query(user_id)
    if status == 'available':
        query = query.filter_by(status='Available', approved=True)
    elif status == 'sold':
        query = query.filter_by(status='Sold', approved=True)
    elif status == 'pending':
        query = query.filter_by(approved=False)

    properties = query.order_by(Property.created_at.desc()).all()

    types = (db.session.query(Property.property_type, db.func.count(Property.id))
                    .filter_by(owner_id=user_id)
                    .group_by(Property.property_type)
                    .all())
    type_counts = [{'type': t[0] or 'Unknown', 'count': t[1]} for t in types]

    counts = {
        'all': _user_property_base_query(user_id).count(),
        'available': _user_property_base_query(user_id).filter_by(status='Available', approved=True).count(),
        'sold': _user_property_base_query(user_id).filter_by(status='Sold', approved=True).count(),
        'pending': _user_property_base_query(user_id).filter_by(approved=False).count()
    }

    owner_bookings = (
        Booking.query
        .join(Property)
        .filter(Property.owner_id == user_id)
        .order_by(Booking.created_at.desc())
        .all()
    )

    user_bookings = Booking.query.filter_by(buyer_id=user_id).order_by(Booking.created_at.desc()).all()

    return render_template(
        'dashboard.html',
        user=user,
        properties=properties,
        selected_status=status,
        type_counts=type_counts,
        counts=counts,
        owner_bookings=owner_bookings,
        user_bookings=user_bookings
    )


@app.route('/dashboard/type/<ptype>')
@login_required
def dashboard_filter_type(ptype):
    user_id = session['user_id']
    props = Property.query.filter_by(owner_id=user_id, property_type=ptype).order_by(Property.created_at.desc()).all()
    types = (db.session.query(Property.property_type, db.func.count(Property.id))
                    .filter_by(owner_id=user_id)
                    .group_by(Property.property_type)
                    .all())
    type_counts = [{'type': t[0] or 'Unknown', 'count': t[1]} for t in types]
    counts = {
        'all': _user_property_base_query(user_id).count(),
        'available': _user_property_base_query(user_id).filter_by(status='Available', approved=True).count(),
        'sold': _user_property_base_query(user_id).filter_by(status='Sold', approved=True).count(),
        'pending': _user_property_base_query(user_id).filter_by(approved=False).count()
    }
    owner_bookings = (
        Booking.query
        .join(Property)
        .filter(Property.owner_id == user_id)
        .order_by(Booking.created_at.desc())
        .all()
    )
    return render_template('dashboard.html',
                           properties=props,
                           selected_status='type:' + ptype,
                           type_counts=type_counts,
                           counts=counts,
                           owner_bookings=owner_bookings)

@app.route('/property/<int:prop_id>/toggle_status', methods=['POST'])
@login_required
def toggle_property_status(prop_id):
    prop = Property.query.get_or_404(prop_id)
    if prop.owner_id != session['user_id']:
        flash('Unauthorized', 'error')
        return redirect(url_for('dashboard'))

    new_status = 'Sold' if prop.status != 'Sold' else 'Available'
    prop.status = new_status
    db.session.commit()
    flash(f'Property marked as {new_status}.', 'success')
    return redirect(request.referrer or url_for('dashboard'))


@app.route('/sell', methods=['GET', 'POST'])
@login_required
def sell():
    form_mode = request.args.get("form")

    if request.method == 'POST':
        filenames = save_images(request.files.getlist('images'))
        new_property = Property(
            owner_id=session['user_id'],
            title=request.form.get('title'),
            description=request.form.get('description'),
            price=request.form.get('price') or 0,
            property_type=request.form.get('property_type'),
            sale_type=request.form.get('sale_type'),
            location=request.form.get('location'),
            seller_type=request.form.get('seller_type', 'Individual'),
            images=json.dumps(filenames),
            approved=False,
            status="Available"
        )
        db.session.add(new_property)
        db.session.commit()
        flash('Property submitted for admin approval!', 'success')
        return redirect(url_for('dashboard', status='pending'))

    if form_mode:
        return render_template('sellformpage.html')
    return render_template('sell.html')

@app.route('/properties')
def properties_list():
    featured = (
        Property.query
        .filter_by(approved=True, status='Available')
        .order_by(Property.created_at.desc())
        .limit(6)
        .all()
    )

    props = (
        Property.query
        .filter_by(approved=True, status='Available')
        .order_by(Property.created_at.desc())
        .all()
    )

    return render_template('property.html', featured=featured, properties=props)


@app.route('/buy')
def buy_page():
    props = (
        Property.query
        .filter_by(approved=True, status='Available', sale_type='Buy')
        .order_by(Property.created_at.desc())
        .all()
    )
    return render_template('buy.html', properties=props)


@app.route('/rent')
def rent_page():
    props = (
        Property.query
        .filter_by(approved=True, status='Available', sale_type='Rent')
        .order_by(Property.created_at.desc())
        .all()
    )
    return render_template('rent.html', properties=props)


@app.route('/property/<int:prop_id>')
def property_detail(prop_id):
    prop = Property.query.get_or_404(prop_id)
    imgs = []
    try:
        imgs = json.loads(prop.images) if prop.images else []
    except Exception:
        imgs = []

    if not prop.approved:
        if not ('user_id' in session and (session.get('is_admin') or session['user_id'] == prop.owner_id)):
            flash("This property is not available.", "warning")
            return redirect(url_for('properties_list'))

    return render_template('property_detail.html', property=prop, images=imgs)


@app.route("/property/<int:prop_id>/edit", methods=["GET", "POST"])
@login_required
def edit_property(prop_id):
    prop = Property.query.get_or_404(prop_id)

    if prop.owner_id != session["user_id"] and not session.get("is_admin"):
        flash("Unauthorized action", "error")
        return redirect(url_for("property_detail", prop_id=prop.id))

    if prop.status == "Booked" and not session.get("is_admin"):
        flash("Cannot edit a booked property.", "warning")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        prop.title = request.form.get("title")
        prop.description = request.form.get("description")
        prop.price = request.form.get("price") or prop.price
        prop.location = request.form.get("location")
        prop.property_type = request.form.get("property_type")
        prop.sale_type = request.form.get("sale_type")
        if not session.get("is_admin"):
            prop.approved = False 
        else:
            prop.approved = (request.form.get("approved") == "on") if request.form.get("approved") is not None else prop.approved

        files = request.files.getlist("images")
        if files and files[0].filename != "":
            filenames = save_images(files)
            prop.images = json.dumps(filenames)

        db.session.commit()
        flash("Property updated successfully!", "success")
        return redirect(url_for("property_detail", prop_id=prop.id))

    return render_template("edit_property.html", property=prop)


@app.route('/delete_property/<int:property_id>', methods=['POST'])
@login_required
def delete_property(property_id):
    
    prop = Property.query.get_or_404(property_id)

    
    if prop.owner_id != current_user.id and not current_user.is_admin:
        flash("You do not have permission to delete this property.", "danger")
        return redirect(url_for('dashboard'))

    
    booking_exists = Booking.query.filter(
        Booking.property_id == property_id,
        Booking.status.in_(["pending", "booked"])
    ).first()

    if booking_exists:
        flash("Cannot delete property with pending or booked bookings.", "warning")
        return redirect(url_for('dashboard'))

   
    db.session.delete(prop)
    db.session.commit()
    flash("Property deleted successfully.", "success")
    return redirect(url_for('dashboard'))


@app.route('/contact', methods=['GET','POST'])
def contact():
    if request.method=='POST':
        new_contact = Contact(
            name=request.form.get('first_name'),
            email=request.form.get('email'),
            phone=request.form.get('phone',''),
            message=request.form.get('message')
        )
        db.session.add(new_contact)
        db.session.commit()
        flash('Contact submitted — we will be in touch', 'success')
        return redirect(url_for('contact'))
    return render_template('contact.html')


@app.route('/agents')
def agents_page():
    ags = Agent.query.filter_by(verified=True).all()
    return render_template('agents.html', agents=ags)


@app.route('/testimonials', methods=['GET','POST'])
def testimonials():
    if request.method=='POST':
        if 'user_id' not in session:
            flash('Login to submit testimonial', 'error')
            return redirect(url_for('login'))
        new_test = Testimonial(
            user_id=session['user_id'],
            message=request.form.get('message'),
            rating=int(request.form.get('rating',5)),
            approved=False  
        )
        db.session.add(new_test)
        db.session.commit()
        flash('Thanks — testimonial submitted for approval', 'success')
        return redirect(url_for('testimonials'))
    list_test = Testimonial.query.filter_by(approved=True).order_by(Testimonial.created_at.desc()).all()
    return render_template('testimonials.html', testimonials=list_test)


@app.route('/admin/properties')
@login_required
def admin_properties():
    if not session.get('is_admin'):
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    props = Property.query.order_by(Property.created_at.desc()).all()
    return render_template('admin_properties.html', properties=props)


@app.route('/admin/property/<int:prop_id>/<action>')
@login_required
def admin_property_action(prop_id, action):
    if not session.get('is_admin'):
        flash('Unauthorized', 'danger')
        return redirect(url_for('index'))
    prop = Property.query.get_or_404(prop_id)
    if action == 'approve':
        prop.approved = True
    elif action == 'reject':
        db.session.delete(prop)
    else:
        flash('Invalid action', 'error')
        return redirect(url_for('admin_properties'))
    db.session.commit()
    flash('Action applied', 'success')
    return redirect(url_for('admin_properties'))


@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not session.get("is_admin"):
        flash("Unauthorized access", "danger")
        return redirect(url_for("index"))

    pending_props = Property.query.filter_by(approved=False).order_by(Property.created_at.desc()).all()
    pending_agents = Agent.query.filter_by(verified=False).all()
    pending_testimonials = Testimonial.query.filter_by(approved=False).order_by(Testimonial.created_at.desc()).all()
    pending_bookings = Booking.query.filter_by(status="Pending").order_by(Booking.created_at.desc()).all()

    return render_template(
        "admin_dashboard.html",
        properties=pending_props,
        agents=pending_agents,
        testimonials=pending_testimonials,
        bookings=pending_bookings
    )


@app.route("/admin/testimonials/<int:test_id>/<string:action>")
@login_required
def admin_testimonial_action(test_id, action):
    if not session.get("is_admin"):
        flash("Unauthorized access", "danger")
        return redirect(url_for("index"))

    test = Testimonial.query.get_or_404(test_id)
    if action == "approve":
        test.approved = True
        db.session.commit()
        flash("Testimonial approved!", "success")
    elif action == "reject":
        db.session.delete(test)
        db.session.commit()
        flash("Testimonial rejected and removed.", "danger")

    return redirect(url_for("admin_dashboard"))

@app.route("/apply_agent", methods=["GET", "POST"])
@login_required
def apply_agent():
    user_id = session["user_id"]
    existing = Agent.query.filter_by(user_id=user_id).first()

    error = None

    if request.method == "POST":
        license_no = request.form.get("license_no", "").strip()
        experience = request.form.get("experience")

        license_exists = Agent.query.filter_by(license_no=license_no).first()

        if existing:
            flash("You already applied or are an agent.", "info")
            return redirect(url_for("dashboard"))
        elif license_exists:
            error = "This license number is already in use. Please provide a valid one."
        else:
            new_app = Agent(
                user_id=user_id,
                license_no=license_no,
                experience=experience if experience else None,
                verified=False
            )
            db.session.add(new_app)
            db.session.commit()
            flash("Application submitted. Wait for admin approval.", "success")
            return redirect(url_for("dashboard"))

    return render_template("apply_agent.html", error=error)


@app.route("/admin/agents")
@login_required
def admin_agents():
    if not session.get("is_admin"):
        return redirect(url_for("login"))
    agents = Agent.query.all()
    return render_template("admin_agents.html", agents=agents)


@app.route("/admin/agents/<int:agent_id>/<string:action>")
@login_required
def admin_agent_action(agent_id, action):
    if not session.get("is_admin"):
        flash("Unauthorized access")
        return redirect(url_for("index"))

    agent = Agent.query.get_or_404(agent_id)

    if action == "approve":
        agent.verified = True
        db.session.commit()
        flash("Agent approved successfully!", "success")
    elif action == "reject":
        db.session.delete(agent)
        db.session.commit()
        flash("Agent rejected and removed.", "danger")

    return redirect(url_for("admin_dashboard"))

@app.route("/upload_profile_pic", methods=["POST"])
@login_required
def upload_profile_pic():
    file = request.files.get("profile_pic")
    if not file or file.filename == "":
        flash("No file selected.", "danger")
        return redirect(request.referrer or url_for("dashboard"))

    filename = secure_filename(file.filename)
    if "." not in filename:
        flash("File must have an extension.", "danger")
        return redirect(request.referrer or url_for("dashboard"))

    ext = filename.rsplit(".", 1)[1].lower()
    if ext not in ALLOWED_EXT:
        flash("Invalid file type. Allowed: png, jpg, jpeg, gif", "danger")
        return redirect(request.referrer or url_for("dashboard"))

    if not (file.mimetype and file.mimetype.startswith("image/")):
        flash("Uploaded file is not an image.", "danger")
        return redirect(request.referrer or url_for("dashboard"))

    unique_name = f"{uuid4().hex}.{ext}"
    save_path = os.path.join(app.config["UPLOAD_FOLDER"], unique_name)

    try:
        file.save(save_path)
    except Exception as e:
        flash("Could not save file.", "danger")
        print("File save error:", e)
        return redirect(request.referrer or url_for("dashboard"))

    try:
        user = User.query.get(session["user_id"])
        if not user:
            flash("User not found.", "danger")
            return redirect(url_for("login"))

        old = user.profile_pic or "default_profile.png"
        user.profile_pic = unique_name
        db.session.commit()

        if old and old != "default_profile.png":
            old_path = os.path.join(app.config["UPLOAD_FOLDER"], old)
            if os.path.exists(old_path):
                try:
                    os.remove(old_path)
                except Exception:
                    pass

        flash("Profile picture updated!", "success")
    except Exception as e:
        db.session.rollback()
        flash("Could not update profile in DB.", "danger")
        print("DB update error:", e)
        try:
            os.remove(save_path)
        except Exception:
            pass

    return redirect(request.referrer or url_for("dashboard"))

@app.route('/reset_request', methods=['GET', 'POST'])
def reset_request():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()
        if user:
            token = s.dumps(email, salt='password-reset')
            link = url_for('reset_token', token=token, _external=True)
            body = f"Click to reset your password: {link}"
            send_email("Password Reset Request", email, body)
            flash('Password reset link sent (check console)', 'info')
            return redirect(url_for('login'))
        else:
            flash('No account found with that email', 'error')
            return redirect(url_for('reset_request'))
    return render_template('reset_request.html')


@app.route('/reset/<token>', methods=['GET', 'POST'])
def reset_token(token):
    try:
        email = s.loads(token, salt='password-reset', max_age=3600)
    except (SignatureExpired, BadSignature):
        flash('Reset link is invalid or expired', 'error')
        return redirect(url_for('reset_request'))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash('Invalid user', 'error')
        return redirect(url_for('reset_request'))

    if request.method == 'POST':
        password = request.form.get('password')
        confirm = request.form.get('confirm')
        if password != confirm:
            flash('Passwords do not match', 'error')
            return redirect(url_for('reset_token', token=token))

        user.password = generate_password_hash(password)
        db.session.commit()
        flash('Password has been reset — you may log in', 'success')
        return redirect(url_for('login'))

    return render_template('reset_token.html')

@app.route('/about')
def about():
    return render_template('about.html')


@app.route("/search")
def search():
    location = request.args.get("location", "")
    min_price = request.args.get("min_price", type=int)
    max_price = request.args.get("max_price", type=int)
    property_type = request.args.get("property_type", "")

    query = Property.query.filter_by(approved=True, status='Available')

    if location:
        query = query.filter(Property.location.ilike(f"%{location}%"))
    if min_price:
        query = query.filter(Property.price >= min_price)
    if max_price:
        query = query.filter(Property.price <= max_price)
    if property_type:
        query = query.filter(Property.property_type == property_type)

    results = query.order_by(Property.created_at.desc()).all()
    return render_template("search_results.html", properties=results)

@app.route('/book_property/<int:property_id>', methods=['POST'])
@login_required
def book_property(property_id):
    user_id = session['user_id']
    prop = Property.query.get_or_404(property_id)

    if prop.owner_id == user_id:
        flash("You cannot book your own property.", "warning")
        return redirect(url_for('property_detail', prop_id=property_id))

    if prop.status != "Available":
        flash("This property is not available for booking.", "warning")
        return redirect(url_for('property_detail', prop_id=property_id))

    existing_booking = Booking.query.filter_by(
        buyer_id=user_id, property_id=property_id
    ).first()

    if existing_booking and existing_booking.status == "Pending":
        flash("You already have a pending booking for this property.", "warning")
        return redirect(url_for('dashboard'))

    new_booking = Booking(
        buyer_id=user_id,
        property_id=property_id,
        status="Pending"
    )
    db.session.add(new_booking)
    db.session.commit()

    flash("Booking request submitted successfully!", "success")
    return redirect(url_for('dashboard'))


@app.route('/booking/<int:booking_id>')
@login_required
def booking_detail(booking_id):
    booking = Booking.query.get_or_404(booking_id)

    if booking.buyer_id != session['user_id'] and booking.property.owner_id != session['user_id']:
        flash("You are not authorized to view this booking.", "danger")
        return redirect(url_for('dashboard'))

    return render_template("booking_dashboard.html", booking=booking)


@app.route('/booking_dashboard')
@login_required
def booking_dashboard():
    user_id = session['user_id']
    bookings = Booking.query.filter_by(buyer_id=user_id).order_by(Booking.created_at.desc()).all()
    return render_template('booking_dashboard.html', bookings=bookings)


@app.route('/cancel_booking/<int:booking_id>', methods=['POST'])
@login_required
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)

    if booking.buyer_id != session.get('user_id'):
        flash("Unauthorized action", "danger")
        return redirect(url_for('dashboard'))

    booking.status = "Cancelled"
    booking.property.status = "Available"

    db.session.commit()
    flash("Your booking has been cancelled.", "info")
    return redirect(url_for('dashboard'))


@app.route('/owner_cancel_booking/<int:booking_id>', methods=['POST'])
@login_required
def owner_cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)

    if booking.property.owner_id != session.get('user_id'):
        flash("Unauthorized action", "danger")
        return redirect(url_for('dashboard'))

    booking.status = "Cancelled"
    booking.property.status = "Available"

    db.session.commit()
    flash("Booking cancelled. Property is now available again.", "info")
    return redirect(url_for('dashboard'))


@app.route('/confirm_booking/<int:booking_id>', methods=['POST'])
@login_required
def confirm_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)

    if booking.property.owner_id != session.get('user_id'):
        flash("Invalid action", "danger")
        return redirect(url_for('dashboard'))


    booking.status = "Confirmed"
    booking.property.status = "Booked"
    db.session.commit()

    flash("Booking confirmed. Property is now marked as booked.", "success")
    return redirect(url_for('dashboard'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        ensure_status_column()
    app.run(debug=True)
