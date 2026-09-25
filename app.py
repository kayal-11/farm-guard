from flask import Flask, request, jsonify, redirect, url_for, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from dotenv import load_dotenv
from flask_cors import CORS
import os
import uuid
from rag_engine import rag_engine_instance

load_dotenv()
app = Flask(__name__, static_folder='.', static_url_path='')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here-change-this')

# Database Configuration (Target DB: livestock)
DB_USER = os.getenv('DB_USER', 'postgres')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'kayaladmin1109')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'livestock')

def test_pg_connection():
    try:
        import psycopg
        conn = psycopg.connect(f"host={DB_HOST} port={DB_PORT} user={DB_USER} password={DB_PASSWORD} dbname=postgres", connect_timeout=3)
        conn.close()
        return True
    except Exception as err:
        print(f"[NOTE] PostgreSQL test connection notice: {err}")
        return False

if test_pg_connection():
    app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    print(f"[OK] Connected to PostgreSQL database '{DB_NAME}' on {DB_HOST}:{DB_PORT}")
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql+psycopg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
    print(f"[OK] Using primary PostgreSQL URI for database '{DB_NAME}'")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

CORS(app, supports_credentials=True)
db = SQLAlchemy(app)

# ========================
# DATABASE MODELS
# ========================

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    identifier = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)  # farmer, vet, authority
    phone = db.Column(db.String(20))
    email = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    amu_entries = db.relationship('AMUEntry', backref='farmer', lazy=True, foreign_keys='AMUEntry.farmer_id')
    audit_logs = db.relationship('AuditLog', backref='user', lazy=True)
    alerts = db.relationship('Alert', backref='user', lazy=True)


class Animal(db.Model):
    __tablename__ = 'animals'
    id = db.Column(db.Integer, primary_key=True)
    tag_number = db.Column(db.String(50), unique=True, nullable=False)
    species = db.Column(db.String(50), nullable=False)
    farmer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    amu_entries = db.relationship('AMUEntry', backref='animal', lazy=True)


class Drug(db.Model):
    __tablename__ = 'drugs'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    active_ingredient = db.Column(db.String(100))
    species = db.Column(db.String(150))
    route = db.Column(db.String(150))
    indication = db.Column(db.Text)
    withdrawal_period_days = db.Column(db.Integer, nullable=False)
    max_dosage = db.Column(db.Float)
    unit = db.Column(db.String(20))
    source = db.Column(db.String(255))
    source_date = db.Column(db.String(50))
    mrl_info = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    entries = db.relationship('AMUEntry', backref='drug', lazy=True)


class AMUEntry(db.Model):
    __tablename__ = 'amu_entries'
    id = db.Column(db.Integer, primary_key=True)
    entry_id = db.Column(db.String(50), unique=True, nullable=False)
    farmer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    animal_id = db.Column(db.Integer, db.ForeignKey('animals.id'), nullable=False)
    drug_id = db.Column(db.Integer, db.ForeignKey('drugs.id'), nullable=False)
    dosage = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), nullable=False)
    route = db.Column(db.String(100))
    indication = db.Column(db.Text)
    treatment_date = db.Column(db.Date, nullable=False)
    withdrawal_end_date = db.Column(db.Date)
    expected_selling_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected, correction_requested
    vet_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    vet_notes = db.Column(db.Text)
    reviewed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    vet = db.relationship('User', foreign_keys=[vet_id])


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    log_id = db.Column(db.String(50), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    related_entry_id = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class Alert(db.Model):
    __tablename__ = 'alerts'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    alert_type = db.Column(db.String(50), nullable=False)  # withdrawal, compliance, notification
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    priority = db.Column(db.String(20), default='normal')  # urgent, high, medium, normal
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class RAGEvidence(db.Model):
    __tablename__ = 'rag_evidences'
    id = db.Column(db.Integer, primary_key=True)
    amu_entry_id = db.Column(db.Integer, db.ForeignKey('amu_entries.id', ondelete='CASCADE'), nullable=False)
    document_title = db.Column(db.String(255), nullable=False)
    retrieved_chunk = db.Column(db.Text, nullable=False)
    source_reference = db.Column(db.String(255), nullable=False)
    recommended_withdrawal_days = db.Column(db.Integer)
    max_allowed_dosage = db.Column(db.Float)
    mrl_info = db.Column(db.Text)
    regulatory_summary = db.Column(db.Text)
    verification_status = db.Column(db.String(50))
    verification_details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    amu_entry = db.relationship('AMUEntry', backref=db.backref('rag_evidence', uselist=False, lazy=True))



from functools import wraps

def require_roles(*allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session or 'role' not in session:
                return jsonify({'error': 'Unauthorized', 'message': 'Authentication required'}), 401
            
            user_role = session.get('role')
            if allowed_roles and user_role not in allowed_roles:
                return jsonify({'error': 'Forbidden', 'message': f'Role "{user_role}" is not authorized to access this resource'}), 403
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# ========================
# ROUTES (HTML PAGES)
# ========================


@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        identifier = data.get('identifier')
        password = data.get('password')
        role = data.get('role')

        user = User.query.filter_by(identifier=identifier, role=role).first()

        if not user:
            return jsonify({
                'success': False,
                'message': f'User with identifier "{identifier}" and role "{role}" not found. Available test users: FARM001, VET001, AUTH001'
            }), 401

        if not check_password_hash(user.password_hash, password):
            return jsonify({'success': False, 'message': 'Invalid password. Default password is: password123'}), 401

        session['user_id'] = user.id
        session['role'] = user.role
        session['name'] = user.name

        log = AuditLog(
            log_id=f"LOG-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}",
            user_id=user.id,
            action='login',
            description=f"{user.name} logged in as {user.role}"
        )
        db.session.add(log)
        db.session.commit()

        return jsonify({'success': True, 'role': user.role})

    return send_from_directory('.', 'login.html')


@app.route('/logout')
def logout():
    if 'user_id' in session:
        user_id = session['user_id']
        user = User.query.get(user_id)

        if user:
            log = AuditLog(
                log_id=f"LOG-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}",
                user_id=user_id,
                action='logout',
                description=f"{user.name} logged out"
            )
            db.session.add(log)
            db.session.commit()

    session.clear()
    return redirect(url_for('index'))


@app.route('/farmer-dashboard')
def farmer_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    role = session.get('role')
    if role == 'vet':
        return redirect(url_for('vet_dashboard'))
    if role == 'authority':
        return redirect(url_for('authority_dashboard'))
    if role != 'farmer':
        return redirect(url_for('login'))
    return send_from_directory('.', 'farmer-dashboard.html')


@app.route('/vet-dashboard')
def vet_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    role = session.get('role')
    if role == 'farmer':
        return redirect(url_for('farmer_dashboard'))
    if role == 'authority':
        return redirect(url_for('authority_dashboard'))
    if role != 'vet':
        return redirect(url_for('login'))
    return send_from_directory('.', 'vet-dashboard.html')


@app.route('/authority-dashboard')
def authority_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    role = session.get('role')
    if role == 'farmer':
        return redirect(url_for('farmer_dashboard'))
    if role == 'vet':
        return redirect(url_for('vet_dashboard'))
    if role != 'authority':
        return redirect(url_for('login'))
    return send_from_directory('.', 'authority-dashboard.html')


@app.route('/analytics')
def analytics():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    # Farmers must not access authority analytics
    if session.get('role') == 'farmer':
        return redirect(url_for('farmer_dashboard'))
    return send_from_directory('.', 'analytics.html')


@app.route('/audit-log')
def audit_log():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return send_from_directory('.', 'audit-log.html')


@app.route('/alerts')
def alerts():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return send_from_directory('.', 'alerts.html')


# ========================
# API ENDPOINTS
# ========================

def compute_real_kpi_stats():
    now = datetime.now()
    total_entries = AMUEntry.query.count()
    approved_entries = AMUEntry.query.filter_by(status='approved').count()
    total_violations = AMUEntry.query.filter_by(status='rejected').count()
    total_farms = User.query.filter_by(role='farmer').count()

    compliance_rate = round((approved_entries / total_entries * 100), 1) if total_entries > 0 else 0.0

    # 1. Total AMU Entries Trend (30 days vs previous 30 days)
    m1_start = now - timedelta(days=30)
    m2_start = now - timedelta(days=60)
    entries_m1 = AMUEntry.query.filter(AMUEntry.created_at >= m1_start).count()
    entries_m2 = AMUEntry.query.filter(AMUEntry.created_at >= m2_start, AMUEntry.created_at < m1_start).count()
    if entries_m2 > 0:
        pct_change = ((entries_m1 - entries_m2) / entries_m2) * 100
        entries_trend = f"↑ {pct_change:.1f}% from last month" if pct_change >= 0 else f"↓ {abs(pct_change):.1f}% from last month"
    elif entries_m1 > 0:
        entries_trend = f"↑ {entries_m1} entries this month"
    else:
        entries_trend = "N/A (No historical data)"

    # 2. Compliance Rate Trend (30 days vs previous 30 days)
    m1_tot = entries_m1
    m1_app = AMUEntry.query.filter(AMUEntry.created_at >= m1_start, AMUEntry.status == 'approved').count()
    m2_tot = entries_m2
    m2_app = AMUEntry.query.filter(AMUEntry.created_at >= m2_start, AMUEntry.created_at < m1_start, AMUEntry.status == 'approved').count()

    r1 = (m1_app / m1_tot * 100) if m1_tot > 0 else None
    r2 = (m2_app / m2_tot * 100) if m2_tot > 0 else None

    if r1 is not None and r2 is not None:
        diff = r1 - r2
        compliance_trend = f"↑ {diff:.1f}% improvement" if diff >= 0 else f"↓ {abs(diff):.1f}% decline"
    elif total_entries > 0:
        compliance_trend = "Based on active records"
    else:
        compliance_trend = "N/A (No historical data)"

    # 3. Active Violations Trend (7 days vs previous 7 days)
    w1_start = now - timedelta(days=7)
    w2_start = now - timedelta(days=14)
    v1 = AMUEntry.query.filter(AMUEntry.created_at >= w1_start, AMUEntry.status == 'rejected').count()
    v2 = AMUEntry.query.filter(AMUEntry.created_at >= w2_start, AMUEntry.created_at < w1_start, AMUEntry.status == 'rejected').count()
    v_diff = v1 - v2
    if v_diff < 0:
        violations_trend = f"↓ {abs(v_diff)} from last week"
    elif v_diff > 0:
        violations_trend = f"↑ {v_diff} from last week"
    elif total_violations > 0:
        violations_trend = "No change from last week"
    else:
        violations_trend = "N/A (No violations)"

    # 4. Active Farms Trend (New farmer registrations in last 30 days)
    new_farms = User.query.filter(User.role == 'farmer', User.created_at >= m1_start).count()
    if new_farms > 0:
        farms_trend = f"↑ {new_farms} new registrations"
    else:
        farms_trend = "0 new registrations"

    return {
        'total_entries': total_entries,
        'entries_trend': entries_trend,
        'compliance_rate': compliance_rate,
        'compliance_trend': compliance_trend,
        'violations': total_violations,
        'violations_trend': violations_trend,
        'farms': total_farms,
        'farms_trend': farms_trend
    }


@app.route('/api/public-stats')
def public_stats():
    kpi_stats = compute_real_kpi_stats()
    total_entries = kpi_stats['total_entries']
    approved_entries = AMUEntry.query.filter_by(status='approved').count()
    pending_entries = AMUEntry.query.filter_by(status='pending').count()
    total_vets = User.query.filter_by(role='vet').count()

    res = {
        'compliance_rate': kpi_stats['compliance_rate'],
        'compliance_trend': kpi_stats['compliance_trend'],
        'active_entries': total_entries,
        'entries_trend': kpi_stats['entries_trend'],
        'pending_review': pending_entries,
        'approved_entries': approved_entries,
        'violations': kpi_stats['violations'],
        'violations_trend': kpi_stats['violations_trend'],
        'total_farms': kpi_stats['farms'],
        'farms_trend': kpi_stats['farms_trend'],
        'total_vets': total_vets
    }
    return jsonify(res)


@app.route('/api/amu-entries', methods=['GET', 'POST'])
@require_roles('farmer', 'vet', 'authority')
def amu_entries_api():
    if request.method == 'GET':
        role = session.get('role')
        if role == 'farmer':
            entries = AMUEntry.query.filter_by(farmer_id=session['user_id']).all()
        else:
            entries = AMUEntry.query.all()

        return jsonify([{
            'id': e.id,
            'entry_id': e.entry_id,
            'animal_tag': e.animal.tag_number if e.animal else 'N/A',
            'animal_species': e.animal.species if e.animal else 'N/A',
            'drug_name': e.drug.name if e.drug else 'N/A',
            'dosage': e.dosage,
            'unit': e.unit,
            'route': e.route,
            'indication': e.indication,
            'treatment_date': e.treatment_date.isoformat() if e.treatment_date else None,
            'withdrawal_end_date': e.withdrawal_end_date.isoformat() if e.withdrawal_end_date else None,
            'expected_selling_date': e.expected_selling_date.isoformat() if e.expected_selling_date else None,
            'status': e.status,
            'verification_status': e.rag_evidence.verification_status if e.rag_evidence else None,
            'created_at': e.created_at.isoformat() if e.created_at else None
        } for e in entries])

    # POST - Only Farmer can submit AMU records
    if session.get('role') != 'farmer':
        return jsonify({'error': 'Forbidden', 'message': 'Only farmers can submit treatment records'}), 403

    data = request.get_json()
    entry_id = f"AMU-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"

    drug = Drug.query.get(data['drug_id'])
    if not drug:
        return jsonify({'error': 'Drug not found'}), 404

    animal = Animal.query.get(data['animal_id'])
    if not animal:
        return jsonify({'error': 'Animal not found'}), 404
    if animal.farmer_id != session['user_id']:
        return jsonify({'error': 'Forbidden', 'message': 'Animal does not belong to you'}), 403

    treatment_date = datetime.strptime(data['treatment_date'], '%Y-%m-%d').date()
    expected_selling_date = None
    if data.get('expected_selling_date'):
        try:
            expected_selling_date = datetime.strptime(data['expected_selling_date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Expected selling date must be a valid date (YYYY-MM-DD)'}), 400
        if expected_selling_date < treatment_date:
            return jsonify({'error': 'Expected selling date cannot be before treatment date'}), 400

    route = data.get('route') or drug.route or 'Injectable'
    indication = data.get('indication') or drug.indication or 'General Antibacterial'

    # Trigger RAG Retrieval & 7-parameter Verification
    rag_res = None
    verification_status = 'insufficient'
    verification_details = None
    recommended_days = drug.withdrawal_period_days

    try:
        rag_res = rag_engine_instance.retrieve_evidence(
            drug_name=drug.name,
            species=animal.species,
            route=route,
            indication=indication,
            dosage=data['dosage'],
            unit=data['unit'],
            treatment_date=treatment_date.isoformat(),
            expected_selling_date=expected_selling_date.isoformat() if expected_selling_date else None
        )
        if rag_res:
            verification_status = rag_res.get('verification_status', 'insufficient')
            verification_details = rag_res.get('verification_details')
            if rag_res.get('recommended_withdrawal_days'):
                recommended_days = rag_res['recommended_withdrawal_days']
    except Exception as rag_err:
        print(f"RAG Retrieval warning: {rag_err}")

    # Deterministic Withdrawal Calculation:
    # If evidence is insufficient and no clear official withdrawal period is available, do not calculate a potentially incorrect date.
    if verification_status == 'insufficient' and not recommended_days:
        withdrawal_end = None
    else:
        withdrawal_end = treatment_date + timedelta(days=recommended_days or 0)

    entry = AMUEntry(
        entry_id=entry_id,
        farmer_id=session['user_id'],
        animal_id=data['animal_id'],
        drug_id=data['drug_id'],
        dosage=data['dosage'],
        unit=data['unit'],
        route=route,
        indication=indication,
        treatment_date=treatment_date,
        withdrawal_end_date=withdrawal_end,
        expected_selling_date=expected_selling_date,
        status='pending'
    )

    db.session.add(entry)
    db.session.commit()

    if rag_res:
        evidence = RAGEvidence(
            amu_entry_id=entry.id,
            document_title=rag_res['document_title'],
            retrieved_chunk=rag_res['retrieved_chunk'],
            source_reference=rag_res['source_reference'],
            recommended_withdrawal_days=rag_res['recommended_withdrawal_days'],
            max_allowed_dosage=rag_res['max_allowed_dosage'],
            mrl_info=rag_res['mrl_info'],
            regulatory_summary=rag_res['regulatory_summary'],
            verification_status=verification_status,
            verification_details=verification_details
        )
        db.session.add(evidence)
        db.session.commit()

    log = AuditLog(
        log_id=f"LOG-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}",
        user_id=session['user_id'],
        action='create',
        description=f"Created AMU entry {entry_id} with RAG evidence ({verification_status})",
        related_entry_id=entry_id
    )
    db.session.add(log)
    db.session.commit()

    return jsonify({'success': True, 'entry_id': entry_id, 'verification_status': verification_status})



@app.route('/api/amu-entries/<int:entry_id>/review', methods=['POST'])
@require_roles('vet')
def review_entry(entry_id):
    data = request.get_json()
    entry = AMUEntry.query.get(entry_id)

    if not entry:
        return jsonify({'error': 'Entry not found'}), 404

    if entry.status != 'pending':
        return jsonify({'error': 'Entry has already been reviewed'}), 400

    entry.status = data['status']
    entry.vet_id = session['user_id']
    entry.vet_notes = data.get('notes', '')
    entry.reviewed_at = datetime.utcnow()

    log = AuditLog(
        log_id=f"LOG-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}",
        user_id=session['user_id'],
        action=data['status'],
        description=f"{data['status'].capitalize()} AMU entry {entry.entry_id} for farmer {entry.farmer.name}",
        related_entry_id=entry.entry_id
    )
    db.session.add(log)

    alert = Alert(
        user_id=entry.farmer_id,
        alert_type='notification',
        title=f"Entry {data['status'].capitalize()}",
        message=f"Your AMU entry {entry.entry_id} has been {data['status']} by {User.query.get(session['user_id']).name}",
        priority='high' if data['status'] == 'rejected' else 'normal'
    )
    db.session.add(alert)
    db.session.commit()

    return jsonify({'success': True, 'message': f'Entry {data["status"]} successfully'})


@app.route('/api/stats')
@require_roles('farmer', 'vet', 'authority')
def get_stats():
    role = session.get('role')
    if role == 'farmer':
        total = AMUEntry.query.filter_by(farmer_id=session['user_id']).count()
        pending = AMUEntry.query.filter_by(farmer_id=session['user_id'], status='pending').count()
        approved = AMUEntry.query.filter_by(farmer_id=session['user_id'], status='approved').count()

        return jsonify({
            'total_entries': total,
            'pending': pending,
            'compliance_rate': (approved / total * 100) if total > 0 else 0
        })

    if role == 'authority':
        total = AMUEntry.query.count()
        approved = AMUEntry.query.filter_by(status='approved').count()
        farms = User.query.filter_by(role='farmer').count()

        return jsonify({
            'total_entries': total,
            'compliance_rate': (approved / total * 100) if total > 0 else 0,
            'total_farms': farms
        })

    if role == 'vet':
        pending = AMUEntry.query.filter_by(status='pending').count()
        approved_today = AMUEntry.query.filter_by(vet_id=session['user_id'], status='approved').filter(
            db.func.date(AMUEntry.reviewed_at) == datetime.now().date()
        ).count()
        return jsonify({
            'pending': pending,
            'approved_today': approved_today
        })


@app.route('/api/check-session')
def check_session():
    if 'user_id' not in session:
        return jsonify({'authenticated': False}), 401

    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'authenticated': False}), 401

    return jsonify({
        'authenticated': True,
        'user': {
            'id': user.id,
            'name': user.name,
            'role': user.role
        }
    })


@app.route('/api/user')
@require_roles('farmer', 'vet', 'authority')
def get_user():
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify({
        'id': user.id,
        'name': user.name,
        'role': user.role,
        'identifier': user.identifier,
        'email': user.email,
        'phone': user.phone
    })


@app.route('/api/farmer/dashboard')
@require_roles('farmer')
def farmer_dashboard_api():
    user = User.query.get(session['user_id'])
    entries = AMUEntry.query.filter_by(farmer_id=user.id).order_by(AMUEntry.created_at.desc()).limit(10).all()

    total_entries = AMUEntry.query.filter_by(farmer_id=user.id).count()
    pending_entries = AMUEntry.query.filter_by(farmer_id=user.id, status='pending').count()
    active_withdrawals = AMUEntry.query.filter(
        AMUEntry.farmer_id == user.id,
        AMUEntry.withdrawal_end_date >= datetime.now().date(),
        AMUEntry.status == 'approved'
    ).count()

    approved = AMUEntry.query.filter_by(farmer_id=user.id, status='approved').count()
    compliance_rate = (approved / total_entries * 100) if total_entries > 0 else 0

    today = datetime.now().date()
    withdrawal_alert_rows = AMUEntry.query.filter(
        AMUEntry.farmer_id == user.id,
        AMUEntry.status == 'approved',
        AMUEntry.withdrawal_end_date >= today
    ).order_by(AMUEntry.withdrawal_end_date.asc()).limit(25).all()

    return jsonify({
        'user': {
            'name': user.name,
            'role': user.role
        },
        'stats': {
            'total_entries': total_entries,
            'pending': pending_entries,
            'active_withdrawals': active_withdrawals,
            'compliance_rate': round(compliance_rate, 1)
        },
        'entries': [{
            'id': e.id,
            'entry_id': e.entry_id,
            'animal_tag': e.animal.tag_number if e.animal else 'N/A',
            'drug_name': e.drug.name if e.drug else 'N/A',
            'dosage': e.dosage,
            'unit': e.unit,
            'status': e.status,
            'vet_notes': (e.vet_notes or '').strip() or None,
            'vet_name': e.vet.name if e.vet_id and e.vet else None,
            'treatment_date': e.treatment_date.isoformat() if e.treatment_date else None,
            'withdrawal_end_date': e.withdrawal_end_date.isoformat() if e.withdrawal_end_date else None,
            'expected_selling_date': e.expected_selling_date.isoformat() if e.expected_selling_date else None,
            'created_at': e.created_at.isoformat() if e.created_at else None
        } for e in entries],
        'withdrawal_alerts': [{
            'entry_id': e.entry_id,
            'animal_tag': e.animal.tag_number if e.animal else 'N/A',
            'drug_name': e.drug.name if e.drug else 'N/A',
            'withdrawal_end_date': e.withdrawal_end_date.isoformat() if e.withdrawal_end_date else None
        } for e in withdrawal_alert_rows]
    })


@app.route('/api/vet/dashboard')
@require_roles('vet')
def vet_dashboard_api():
    user = User.query.get(session['user_id'])
    pending_entries = AMUEntry.query.filter_by(status='pending').order_by(AMUEntry.created_at.desc()).all()

    pending_count = len(pending_entries)
    approved_today = AMUEntry.query.filter_by(
        vet_id=user.id,
        status='approved'
    ).filter(
        db.func.date(AMUEntry.reviewed_at) == datetime.now().date()
    ).count()

    new_entries_this_week = AMUEntry.query.filter(
        AMUEntry.created_at >= datetime.now() - timedelta(days=7)
    ).count()

    return jsonify({
        'user': {
            'name': user.name,
            'role': user.role
        },
        'stats': {
            'pending': pending_count,
            'approved_today': approved_today,
            'new_entries_week': new_entries_this_week
        },
        'pending_entries': [{
            'id': e.id,
            'entry_id': e.entry_id,
            'farmer_name': e.farmer.name if e.farmer else 'Unknown',
            'animal_tag': e.animal.tag_number if e.animal else 'N/A',
            'drug_name': e.drug.name if e.drug else 'N/A',
            'dosage': e.dosage,
            'unit': e.unit,
            'treatment_date': e.treatment_date.isoformat() if e.treatment_date else None,
            'animal_species': e.animal.species if e.animal else 'N/A',
            'drug_max_dosage': e.drug.max_dosage if e.drug else None,
            'withdrawal_end_date': e.withdrawal_end_date.isoformat() if e.withdrawal_end_date else None,
            'expected_selling_date': e.expected_selling_date.isoformat() if e.expected_selling_date else None,
            'created_at': e.created_at.isoformat() if e.created_at else None,
            'created_ago': format_time_ago(e.created_at) if e.created_at else None
        } for e in pending_entries]
    })


@app.route('/api/authority/dashboard')
@require_roles('authority')
def authority_dashboard_api():
    user = User.query.get(session['user_id'])

    total_entries = AMUEntry.query.count()
    total_approved = AMUEntry.query.filter_by(status='approved').count()
    total_violations = AMUEntry.query.filter_by(status='rejected').count()
    total_farms = User.query.filter_by(role='farmer').count()

    today = datetime.now().date()
    entries_today = AMUEntry.query.filter(
        db.func.date(AMUEntry.created_at) == today
    ).count()

    week_ago = datetime.now() - timedelta(days=7)
    entries_this_week = AMUEntry.query.filter(
        AMUEntry.created_at >= week_ago
    ).count()

    compliance_rate = (total_approved / total_entries * 100) if total_entries > 0 else 0

    recent_entries = AMUEntry.query.order_by(AMUEntry.created_at.desc()).limit(20).all()

    drug_usage = db.session.query(
        Drug.name,
        db.func.count(AMUEntry.id).label('usage_count'),
        (db.func.count(AMUEntry.id) * 100.0 / total_entries).label('percentage')
    ).join(AMUEntry).group_by(Drug.name).order_by(db.func.count(AMUEntry.id).desc()).limit(10).all()

    # Compliance trend (last 6 months)
    compliance_trend = []
    for i in range(5, -1, -1):
        month_start = datetime.now().replace(day=1) - timedelta(days=30 * i)
        if i == 0:
            month_end = datetime.now()
        else:
            next_month = month_start + timedelta(days=32)
            month_end = next_month.replace(day=1) - timedelta(days=1)

        month_entries = AMUEntry.query.filter(
            AMUEntry.created_at >= month_start,
            AMUEntry.created_at <= month_end
        ).all()

        month_total = len(month_entries)
        month_approved = len([e for e in month_entries if e.status == 'approved'])
        month_compliance = (month_approved / month_total * 100) if month_total > 0 else 0

        compliance_trend.append({
            'month': month_start.strftime('%b %Y'),
            'compliance_rate': round(month_compliance, 1),
            'total_entries': month_total,
            'approved': month_approved
        })

    # Regional distribution (simulated by farmer_id % 4)
    regions = {
        'North Zone': 0,
        'South Zone': 0,
        'East Zone': 0,
        'West Zone': 0
    }

    for entry in AMUEntry.query.all():
        farmer_mod = entry.farmer_id % 4
        if farmer_mod == 0:
            regions['North Zone'] += 1
        elif farmer_mod == 1:
            regions['South Zone'] += 1
        elif farmer_mod == 2:
            regions['East Zone'] += 1
        else:
            regions['West Zone'] += 1

    regional_distribution = []
    for region, count in regions.items():
        percentage = (count / total_entries * 100) if total_entries > 0 else 0
        regional_distribution.append({
            'region': region,
            'count': count,
            'percentage': round(percentage, 1)
        })

    kpi_stats = compute_real_kpi_stats()

    return jsonify({
        'user': {
            'name': user.name,
            'role': user.role
        },
        'stats': {
            'total_entries': total_entries,
            'entries_trend': kpi_stats['entries_trend'],
            'compliance_rate': kpi_stats['compliance_rate'],
            'compliance_trend': kpi_stats['compliance_trend'],
            'violations': total_violations,
            'violations_trend': kpi_stats['violations_trend'],
            'farms': total_farms,
            'farms_trend': kpi_stats['farms_trend'],
            'entries_today': entries_today,
            'entries_this_week': entries_this_week
        },
        'recent_entries': [{
            'id': e.id,
            'entry_id': e.entry_id,
            'farmer_name': e.farmer.name if e.farmer else 'Unknown',
            'animal_tag': e.animal.tag_number if e.animal else 'N/A',
            'drug_name': e.drug.name if e.drug else 'N/A',
            'dosage': e.dosage,
            'unit': e.unit,
            'status': e.status,
            'vet_name': e.vet.name if e.vet else 'Pending',
            'treatment_date': e.treatment_date.isoformat() if e.treatment_date else None,
            'reviewed_at': e.reviewed_at.isoformat() if e.reviewed_at else None,
            'created_at': e.created_at.isoformat() if e.created_at else None
        } for e in recent_entries],
        'drug_analytics': [{
            'drug_name': d.name,
            'usage_count': int(d.usage_count),
            'percentage': float(d.percentage)
        } for d in drug_usage],
        'compliance_trend': compliance_trend,
        'regional_distribution': regional_distribution
    })


# Analytics data for charts
@app.route('/api/analytics')
@require_roles('vet', 'authority')
def get_analytics():
    # Monthly entries (last 12 months)
    monthly_entries = []
    for i in range(11, -1, -1):
        month_start = datetime.now().replace(day=1) - timedelta(days=30 * i)
        if i == 0:
            month_end = datetime.now()
        else:
            next_month = month_start + timedelta(days=32)
            month_end = next_month.replace(day=1) - timedelta(days=1)

        count = AMUEntry.query.filter(
            AMUEntry.created_at >= month_start,
            AMUEntry.created_at <= month_end
        ).count()
        monthly_entries.append({
            'month': month_start.strftime('%b %Y'),
            'count': count
        })

    # Regional compliance (reuse simulated regions)
    regional_compliance = []
    regions = ['North Zone', 'South Zone', 'East Zone', 'West Zone']

    for idx, region in enumerate(regions):
        region_entries = []
        all_entries = AMUEntry.query.all()
        for e in all_entries:
            if e.farmer_id % 4 == idx:
                region_entries.append(e)

        total = len(region_entries)
        approved = len([e for e in region_entries if e.status == 'approved'])
        compliance = (approved / total * 100) if total > 0 else 0

        regional_compliance.append({
            'region': region,
            'compliance_rate': round(compliance, 1),
            'total_entries': total,
            'approved': approved
        })

    # Species distribution
    species_counts = {}
    for e in AMUEntry.query.all():
        if e.animal and e.animal.species:
            key = e.animal.species.capitalize()
            species_counts[key] = species_counts.get(key, 0) + 1

    total_species = sum(species_counts.values())
    species_distribution = [{
        'species': name,
        'count': count,
        'percentage': round((count / total_species * 100) if total_species > 0 else 0, 1)
    } for name, count in species_counts.items()]

    # Monthly violation trends (rejected entries)
    monthly_violations = []
    for i in range(11, -1, -1):
        month_start = datetime.now().replace(day=1) - timedelta(days=30 * i)
        if i == 0:
            month_end = datetime.now()
        else:
            next_month = month_start + timedelta(days=32)
            month_end = next_month.replace(day=1) - timedelta(days=1)

        violations = AMUEntry.query.filter(
            AMUEntry.created_at >= month_start,
            AMUEntry.created_at <= month_end,
            AMUEntry.status == 'rejected'
        ).count()

        monthly_violations.append({
            'month': month_start.strftime('%b %Y'),
            'violations': violations
        })

    return jsonify({
        'monthly_entries': monthly_entries,
        'regional_compliance': regional_compliance,
        'species_distribution': species_distribution,
        'monthly_violations': monthly_violations
    })


@app.route('/api/animals', methods=['GET', 'POST'])
@require_roles('farmer', 'vet', 'authority')
def get_animals():
    if request.method == 'POST':
        if session.get('role') != 'farmer':
            return jsonify({'error': 'Forbidden', 'message': 'Only farmers can add animals'}), 403

        data = request.get_json()
        animal = Animal(
            tag_number=data['tag_number'],
            species=data['species'],
            farmer_id=session['user_id']
        )

        try:
            db.session.add(animal)
            db.session.commit()
            return jsonify({
                'success': True,
                'animal': {
                    'id': animal.id,
                    'tag_number': animal.tag_number,
                    'species': animal.species
                }
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 400

    if session.get('role') == 'farmer':
        animals = Animal.query.filter_by(farmer_id=session['user_id']).all()
    else:
        animals = Animal.query.all()

    return jsonify([{
        'id': a.id,
        'tag_number': a.tag_number,
        'species': a.species
    } for a in animals])


@app.route('/api/drugs')
@require_roles('farmer', 'vet', 'authority')
def get_drugs():
    drugs = Drug.query.order_by(Drug.name.asc()).all()
    return jsonify([{
        'id': d.id,
        'name': d.name,
        'active_ingredient': d.active_ingredient or d.name,
        'species': d.species or 'cattle, buffalo, goat',
        'route': d.route or 'Injectable, Oral',
        'indication': d.indication or 'Systemic bacterial infection',
        'withdrawal_period_days': d.withdrawal_period_days,
        'max_dosage': d.max_dosage,
        'unit': d.unit,
        'source': d.source or 'CDSCO (Central Drugs Standard Control Organisation, Govt of India)',
        'source_date': d.source_date or 'Current Approved List',
        'mrl_info': d.mrl_info or 'Codex/FSSAI MRL Compliant'
    } for d in drugs])



@app.route('/api/alerts')
@require_roles('farmer', 'vet', 'authority')
def get_alerts():
    user_id = session['user_id']
    role = session.get('role')

    base_alerts = Alert.query.filter_by(user_id=user_id).order_by(Alert.created_at.desc()).all()

    alerts_list = [{
        'id': a.id,
        'alert_type': a.alert_type,
        'title': a.title,
        'message': a.message,
        'priority': a.priority,
        'is_read': a.is_read,
        'created_at': a.created_at.isoformat() if a.created_at else None
    } for a in base_alerts]

    # Augment for farmers: withdrawal & compliance alerts from AMU entries
    if role == 'farmer':
        farmer_entries = AMUEntry.query.filter_by(farmer_id=user_id).all()

        # Withdrawal alerts
        for e in farmer_entries:
            if e.status == 'approved' and e.withdrawal_end_date:
                end_date = e.withdrawal_end_date
                days_remaining = (end_date - datetime.now().date()).days
                if days_remaining <= 14:
                    priority = 'urgent' if days_remaining <= 2 else 'high' if days_remaining <= 5 else 'medium'
                    alerts_list.append({
                        'id': f'withdrawal-{e.id}',
                        'alert_type': 'withdrawal',
                        'title': f'{e.animal.tag_number if e.animal else "Animal"} - Withdrawal '
                                 f'{"Ending Soon" if days_remaining <= 2 else "Active"}',
                        'message': f'{e.drug.name if e.drug else "Drug"} treatment withdrawal period '
                                   f'ends {end_date.strftime("%B %d, %Y")}',
                        'priority': priority,
                        'is_read': False,
                        'created_at': e.created_at.isoformat() if e.created_at else None,
                        'entry_id': e.entry_id,
                        'withdrawal_end_date': end_date.isoformat()
                    })

        # Compliance alerts (rejected entries)
        for e in farmer_entries:
            if e.status == 'rejected':
                alerts_list.append({
                    'id': f'compliance-{e.id}',
                    'alert_type': 'compliance',
                    'title': f'Entry Rejected: {e.entry_id}',
                    'message': f'Your AMU entry was rejected. {e.vet_notes if e.vet_notes else "Please review and resubmit."}',
                    'priority': 'high',
                    'is_read': False,
                    'created_at': e.reviewed_at.isoformat() if e.reviewed_at else e.created_at.isoformat() if e.created_at else None,
                    'entry_id': e.entry_id
                })

    return jsonify(alerts_list)


@app.route('/api/audit-logs')
@require_roles('farmer', 'vet', 'authority')
def get_audit_logs():
    role = session.get('role')
    user_id = session.get('user_id')

    # Authority sees all audit logs; Farmers and Vets see only their own audit history
    if role == 'authority':
        logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(50).all()
    else:
        logs = AuditLog.query.filter_by(user_id=user_id).order_by(AuditLog.timestamp.desc()).limit(50).all()

    return jsonify([{
        'id': l.id,
        'log_id': l.log_id,
        'user_name': l.user.name if l.user else 'Unknown',
        'user_role': l.user.role if l.user else 'Unknown',
        'action': l.action,
        'description': l.description,
        'related_entry_id': l.related_entry_id,
        'timestamp': l.timestamp.isoformat() if l.timestamp else None
    } for l in logs])


@app.route('/api/amu-entries/<int:entry_id>')
@require_roles('farmer', 'vet', 'authority')
def get_entry(entry_id):
    entry = AMUEntry.query.get(entry_id)
    if not entry:
        return jsonify({'error': 'Entry not found'}), 404

    # Farmers must never access another farmer's records
    if session.get('role') == 'farmer' and entry.farmer_id != session['user_id']:
        return jsonify({'error': 'Forbidden', 'message': 'You cannot access another farmer\'s treatment records'}), 403

    route = entry.route or (entry.drug.route if entry.drug else 'Injectable')
    indication = entry.indication or (entry.drug.indication if entry.drug else 'Systemic infection')

    if not entry.rag_evidence and entry.drug:
        try:
            rag_res = rag_engine_instance.retrieve_evidence(
                drug_name=entry.drug.name,
                species=entry.animal.species if entry.animal else 'cattle',
                route=route,
                indication=indication,
                dosage=entry.dosage,
                unit=entry.unit,
                treatment_date=entry.treatment_date.isoformat() if entry.treatment_date else None,
                expected_selling_date=entry.expected_selling_date.isoformat() if entry.expected_selling_date else None
            )
            ev = RAGEvidence(
                amu_entry_id=entry.id,
                document_title=rag_res['document_title'],
                retrieved_chunk=rag_res['retrieved_chunk'],
                source_reference=rag_res['source_reference'],
                recommended_withdrawal_days=rag_res['recommended_withdrawal_days'],
                max_allowed_dosage=rag_res['max_allowed_dosage'],
                mrl_info=rag_res['mrl_info'],
                regulatory_summary=rag_res['regulatory_summary'],
                verification_status=rag_res['verification_status'],
                verification_details=rag_res['verification_details']
            )
            db.session.add(ev)
            db.session.commit()
            entry.rag_evidence = ev
        except Exception as e:
            print(f"Error auto-generating RAG evidence: {e}")

    rag_data = None
    if entry.rag_evidence:
        rag_data = {
            'id': entry.rag_evidence.id,
            'document_title': entry.rag_evidence.document_title,
            'retrieved_chunk': entry.rag_evidence.retrieved_chunk,
            'source_reference': entry.rag_evidence.source_reference,
            'recommended_withdrawal_days': entry.rag_evidence.recommended_withdrawal_days,
            'max_allowed_dosage': entry.rag_evidence.max_allowed_dosage,
            'mrl_info': entry.rag_evidence.mrl_info,
            'regulatory_summary': entry.rag_evidence.regulatory_summary,
            'verification_status': entry.rag_evidence.verification_status or 'insufficient',
            'verification_details': entry.rag_evidence.verification_details
        }

    return jsonify({
        'id': entry.id,
        'entry_id': entry.entry_id,
        'farmer_name': entry.farmer.name if entry.farmer else 'Unknown',
        'animal_tag': entry.animal.tag_number if entry.animal else 'N/A',
        'animal_species': entry.animal.species if entry.animal else 'N/A',
        'drug_name': entry.drug.name if entry.drug else 'N/A',
        'active_ingredient': (entry.drug.active_ingredient if entry.drug and entry.drug.active_ingredient else entry.drug.name) if entry.drug else 'N/A',
        'drug_max_dosage': entry.drug.max_dosage if entry.drug else None,
        'dosage': entry.dosage,
        'unit': entry.unit,
        'route': route,
        'indication': indication,
        'treatment_date': entry.treatment_date.isoformat() if entry.treatment_date else None,
        'withdrawal_end_date': entry.withdrawal_end_date.isoformat() if entry.withdrawal_end_date else None,
        'expected_selling_date': entry.expected_selling_date.isoformat() if entry.expected_selling_date else None,
        'status': entry.status,
        'created_at': entry.created_at.isoformat() if entry.created_at else None,
        'created_ago': format_time_ago(entry.created_at) if entry.created_at else None,
        'rag_evidence': rag_data
    })



def format_time_ago(dt):
    if not dt:
        return 'Recently'
    delta = datetime.utcnow() - dt
    if delta.days > 0:
        return f"{delta.days} day{'s' if delta.days > 1 else ''} ago"
    hours = delta.seconds // 3600
    if hours > 0:
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    minutes = delta.seconds // 60
    return f"{minutes} minute{'s' if minutes > 1 else ''} ago"


@app.route('/api/test-db')
def test_database():
    try:
        db.session.execute(db.text('SELECT 1'))

        db_info = {
            'connected': True,
            'database_uri': app.config['SQLALCHEMY_DATABASE_URI'].split('@')[-1]
            if '@' in app.config['SQLALCHEMY_DATABASE_URI'] else 'hidden',
            'tables': []
        }

        try:
            user_count = User.query.count()
            animal_count = Animal.query.count()
            drug_count = Drug.query.count()
            entry_count = AMUEntry.query.count()
            log_count = AuditLog.query.count()
            alert_count = Alert.query.count()

            db_info['tables'] = {
                'users': user_count,
                'animals': animal_count,
                'drugs': drug_count,
                'amu_entries': entry_count,
                'audit_logs': log_count,
                'alerts': alert_count
            }
        except Exception as e:
            db_info['tables'] = {'error': str(e)}

        return jsonify({
            'status': 'success',
            'message': 'Database connection successful!',
            'database': db_info
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': 'Database connection failed!',
            'error': str(e),
            'database_uri': app.config['SQLALCHEMY_DATABASE_URI'].split('@')[-1]
            if '@' in app.config['SQLALCHEMY_DATABASE_URI'] else 'hidden',
            'help': 'Please check: 1) PostgreSQL is running, 2) Database "farmguard" exists, 3) Username/password are correct'
        }), 500


def ensure_livestock_db():
    if 'postgresql' in app.config['SQLALCHEMY_DATABASE_URI']:
        try:
            import psycopg
            conn = psycopg.connect(f"host={DB_HOST} port={DB_PORT} user={DB_USER} password={DB_PASSWORD} dbname=postgres", autocommit=True)
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM pg_database WHERE datname=%s", (DB_NAME,))
                if not cur.fetchone():
                    print(f"[INFO] Creating database '{DB_NAME}' in PostgreSQL...")
                    cur.execute(f"CREATE DATABASE {DB_NAME}")
                    print(f"[OK] Database '{DB_NAME}' created in PostgreSQL!")
            conn.close()
        except Exception as err:
            print(f"[NOTE] PostgreSQL database check note: {err}")


def init_db():
    ensure_livestock_db()
    with app.app_context():
        try:
            print("Connecting to database...")
            print(f"Database URI: {app.config['SQLALCHEMY_DATABASE_URI'].split('@')[-1] if '@' in app.config['SQLALCHEMY_DATABASE_URI'] else app.config['SQLALCHEMY_DATABASE_URI']}")

            db.session.execute(db.text('SELECT 1'))
            print("[OK] Database connection successful!")

            print("Creating database tables...")
            db.create_all()
            print("[OK] Tables created successfully!")
            
            # Auto-migrate table columns if using existing SQLite or PostgreSQL DB
            alter_commands = [
                "ALTER TABLE drugs ADD COLUMN active_ingredient VARCHAR(100)",
                "ALTER TABLE drugs ADD COLUMN species VARCHAR(150)",
                "ALTER TABLE drugs ADD COLUMN route VARCHAR(150)",
                "ALTER TABLE drugs ADD COLUMN indication TEXT",
                "ALTER TABLE drugs ADD COLUMN source VARCHAR(255)",
                "ALTER TABLE drugs ADD COLUMN source_date VARCHAR(50)",
                "ALTER TABLE drugs ADD COLUMN mrl_info TEXT",
                "ALTER TABLE amu_entries ADD COLUMN expected_selling_date DATE",
                "ALTER TABLE amu_entries ADD COLUMN route VARCHAR(100)",
                "ALTER TABLE amu_entries ADD COLUMN indication TEXT",
                "ALTER TABLE rag_evidences ADD COLUMN verification_status VARCHAR(50)",
                "ALTER TABLE rag_evidences ADD COLUMN verification_details TEXT"
            ]
            for cmd in alter_commands:
                try:
                    db.session.execute(db.text(cmd))
                    db.session.commit()
                except Exception:
                    db.session.rollback()

            # Ensure official CDSCO drugs exist and are populated with full metadata
            cdsco_catalog = [
                {
                    "name": 'Amoxicillin',
                    "active_ingredient": 'Amoxicillin Trihydrate',
                    "species": 'cattle, buffalo, goat, sheep, swine',
                    "route": 'Intramuscular, Oral',
                    "indication": 'Respiratory tract infection, Mastitis, Metritis, Enteritis',
                    "withdrawal_period_days": 5,
                    "max_dosage": 15.0,
                    "unit": 'mg/kg',
                    "source": 'CDSCO (Central Drugs Standard Control Organisation, India)',
                    "source_date": '2024-03-10',
                    "mrl_info": 'Codex/FSSAI MRL: 50 µg/kg in muscle/liver/kidney, 4 µg/kg in milk.'
                },
                {
                    "name": 'Ceftiofur Sodium',
                    "active_ingredient": 'Ceftiofur',
                    "species": 'cattle, buffalo, swine',
                    "route": 'Subcutaneous, Intramuscular',
                    "indication": 'Bovine respiratory disease, Foot rot, Acute metritis',
                    "withdrawal_period_days": 4,
                    "max_dosage": 2.2,
                    "unit": 'mg/kg',
                    "source": 'CDSCO (Central Drugs Standard Control Organisation, India)',
                    "source_date": '2023-11-20',
                    "mrl_info": 'Codex/FSSAI MRL: 1000 µg/kg in muscle, 2000 µg/kg in kidney, 100 µg/kg in milk.'
                },
                {
                    "name": 'Enrofloxacin',
                    "active_ingredient": 'Enrofloxacin',
                    "species": 'cattle, buffalo, goat, poultry',
                    "route": 'Injectable, Intramuscular, Subcutaneous, Oral',
                    "indication": 'Complex respiratory disease, Colibacillosis, CCPP',
                    "withdrawal_period_days": 10,
                    "max_dosage": 5.0,
                    "unit": 'mg/kg',
                    "source": 'CDSCO & WHO MIA Guidelines',
                    "source_date": '2024-01-15',
                    "mrl_info": 'Codex/FSSAI MRL: 100 µg/kg (combined enrofloxacin + ciprofloxacin) in muscle.'
                },
                {
                    "name": 'Oxytetracycline',
                    "active_ingredient": 'Oxytetracycline',
                    "species": 'cattle, buffalo, goat, sheep, swine',
                    "route": 'Intramuscular, Intravenous',
                    "indication": 'Anaplasmosis, Blackquarter, HS, Pneumonia, Foot rot',
                    "withdrawal_period_days": 7,
                    "max_dosage": 10.0,
                    "unit": 'mg/kg',
                    "source": 'CDSCO (Central Drugs Standard Control Organisation, India)',
                    "source_date": '2024-02-01',
                    "mrl_info": 'Codex/FSSAI MRL: 100 µg/kg in muscle, 300 µg/kg in liver, 600 µg/kg in kidney.'
                },
                {
                    "name": 'Penicillin G Procaine',
                    "active_ingredient": 'Procaine Penicillin G',
                    "species": 'cattle, buffalo, goat, horse, sheep',
                    "route": 'Intramuscular',
                    "indication": 'Blackleg, Mastitis, Erysipelas, Gram-positive infection',
                    "withdrawal_period_days": 14,
                    "max_dosage": 20000.0,
                    "unit": 'IU/kg',
                    "source": 'CDSCO (Central Drugs Standard Control Organisation, India)',
                    "source_date": '2023-09-05',
                    "mrl_info": 'Codex/FSSAI MRL: 50 µg/kg in muscle, 4 µg/kg in milk.'
                },
                {
                    "name": 'Sulfadimidine Sodium',
                    "active_ingredient": 'Sulfadimidine',
                    "species": 'cattle, buffalo, goat, poultry, sheep',
                    "route": 'Oral, Intravenous, Subcutaneous',
                    "indication": 'Coccidiosis, Calf diphtheria, Bacterial enteritis',
                    "withdrawal_period_days": 10,
                    "max_dosage": 100.0,
                    "unit": 'mg/kg',
                    "source": 'CDSCO (Central Drugs Standard Control Organisation, India)',
                    "source_date": '2023-12-12',
                    "mrl_info": 'Codex/FSSAI MRL: 100 µg/kg total sulfonamide residues.'
                },
                {
                    "name": 'Tylosin Tartrate',
                    "active_ingredient": 'Tylosin',
                    "species": 'cattle, buffalo, goat, poultry, swine',
                    "route": 'Intramuscular, Oral',
                    "indication": 'Bovine respiratory complex, Mycoplasmosis, Foot rot',
                    "withdrawal_period_days": 21,
                    "max_dosage": 10.0,
                    "unit": 'mg/kg',
                    "source": 'CDSCO (Central Drugs Standard Control Organisation, India)',
                    "source_date": '2024-04-18',
                    "mrl_info": 'Codex/FSSAI MRL: 100 µg/kg in muscle, 50 µg/kg in milk.'
                }
            ]

            for d_info in cdsco_catalog:
                existing_drug = Drug.query.filter_by(name=d_info['name']).first()
                if existing_drug:
                    existing_drug.active_ingredient = d_info['active_ingredient']
                    existing_drug.species = d_info['species']
                    existing_drug.route = d_info['route']
                    existing_drug.indication = d_info['indication']
                    existing_drug.withdrawal_period_days = d_info['withdrawal_period_days']
                    existing_drug.max_dosage = d_info['max_dosage']
                    existing_drug.unit = d_info['unit']
                    existing_drug.source = d_info['source']
                    existing_drug.source_date = d_info['source_date']
                    existing_drug.mrl_info = d_info['mrl_info']
                else:
                    new_drug = Drug(**d_info)
                    db.session.add(new_drug)
            db.session.commit()


            if User.query.count() == 0:
                print("Adding sample data...")
                farmer = User(
                    identifier='FARM001',
                    password_hash=generate_password_hash('password123'),
                    name='Rajesh Kumar',
                    role='farmer',
                    phone='9876543210'
                )

                custom_farmer = User(
                    identifier='kayalvizhi110906',
                    password_hash=generate_password_hash('password123'),
                    name='Kayalvizhi',
                    role='farmer',
                    phone=''
                )

                vet = User(
                    identifier='VET001',
                    password_hash=generate_password_hash('password123'),
                    name='Dr. Priya Sharma',
                    role='vet',
                    email='priya.sharma@vet.com'
                )

                authority = User(
                    identifier='AUTH001',
                    password_hash=generate_password_hash('password123'),
                    name='Admin User',
                    role='authority',
                    email='admin@authority.gov.in'
                )

                db.session.add_all([farmer, vet, authority, custom_farmer])

                drugs = [
                    Drug(
                        name='Amoxicillin',
                        active_ingredient='Amoxicillin Trihydrate',
                        species='cattle, buffalo, goat, sheep, swine',
                        route='Intramuscular, Oral',
                        indication='Respiratory tract infection, Mastitis, Metritis, Enteritis',
                        withdrawal_period_days=5,
                        max_dosage=15.0,
                        unit='mg/kg',
                        source='CDSCO (Central Drugs Standard Control Organisation, India)',
                        source_date='2024-03-10',
                        mrl_info='Codex/FSSAI MRL: 50 µg/kg in muscle/liver/kidney, 4 µg/kg in milk.'
                    ),
                    Drug(
                        name='Ceftiofur Sodium',
                        active_ingredient='Ceftiofur',
                        species='cattle, buffalo, swine',
                        route='Subcutaneous, Intramuscular',
                        indication='Bovine respiratory disease, Foot rot, Acute metritis',
                        withdrawal_period_days=4,
                        max_dosage=2.2,
                        unit='mg/kg',
                        source='CDSCO (Central Drugs Standard Control Organisation, India)',
                        source_date='2023-11-20',
                        mrl_info='Codex/FSSAI MRL: 1000 µg/kg in muscle, 2000 µg/kg in kidney, 100 µg/kg in milk.'
                    ),
                    Drug(
                        name='Enrofloxacin',
                        active_ingredient='Enrofloxacin',
                        species='cattle, buffalo, goat, poultry',
                        route='Injectable, Intramuscular, Subcutaneous, Oral',
                        indication='Complex respiratory disease, Colibacillosis, CCPP',
                        withdrawal_period_days=10,
                        max_dosage=5.0,
                        unit='mg/kg',
                        source='CDSCO & WHO MIA Guidelines',
                        source_date='2024-01-15',
                        mrl_info='Codex/FSSAI MRL: 100 µg/kg (combined enrofloxacin + ciprofloxacin) in muscle.'
                    ),
                    Drug(
                        name='Oxytetracycline',
                        active_ingredient='Oxytetracycline',
                        species='cattle, buffalo, goat, sheep, swine',
                        route='Intramuscular, Intravenous',
                        indication='Anaplasmosis, Blackquarter, HS, Pneumonia, Foot rot',
                        withdrawal_period_days=7,
                        max_dosage=10.0,
                        unit='mg/kg',
                        source='CDSCO (Central Drugs Standard Control Organisation, India)',
                        source_date='2024-02-01',
                        mrl_info='Codex/FSSAI MRL: 100 µg/kg in muscle, 300 µg/kg in liver, 600 µg/kg in kidney.'
                    ),
                    Drug(
                        name='Penicillin G Procaine',
                        active_ingredient='Procaine Penicillin G',
                        species='cattle, buffalo, goat, horse, sheep',
                        route='Intramuscular',
                        indication='Blackleg, Mastitis, Erysipelas, Gram-positive infection',
                        withdrawal_period_days=14,
                        max_dosage=20000.0,
                        unit='IU/kg',
                        source='CDSCO (Central Drugs Standard Control Organisation, India)',
                        source_date='2023-09-05',
                        mrl_info='Codex/FSSAI MRL: 50 µg/kg in muscle, 4 µg/kg in milk.'
                    ),
                    Drug(
                        name='Sulfadimidine Sodium',
                        active_ingredient='Sulfadimidine',
                        species='cattle, buffalo, goat, poultry, sheep',
                        route='Oral, Intravenous, Subcutaneous',
                        indication='Coccidiosis, Calf diphtheria, Bacterial enteritis',
                        withdrawal_period_days=10,
                        max_dosage=100.0,
                        unit='mg/kg',
                        source='CDSCO (Central Drugs Standard Control Organisation, India)',
                        source_date='2023-12-12',
                        mrl_info='Codex/FSSAI MRL: 100 µg/kg total sulfonamide residues.'
                    ),
                    Drug(
                        name='Tylosin Tartrate',
                        active_ingredient='Tylosin',
                        species='cattle, buffalo, goat, poultry, swine',
                        route='Intramuscular, Oral',
                        indication='Bovine respiratory complex, Mycoplasmosis, Foot rot',
                        withdrawal_period_days=21,
                        max_dosage=10.0,
                        unit='mg/kg',
                        source='CDSCO (Central Drugs Standard Control Organisation, India)',
                        source_date='2024-04-18',
                        mrl_info='Codex/FSSAI MRL: 100 µg/kg in muscle, 50 µg/kg in milk.'
                    )
                ]
                db.session.add_all(drugs)
                db.session.commit()

                animals = [
                    Animal(tag_number='CATTLE-001', species='cattle', farmer_id=farmer.id),
                    Animal(tag_number='CATTLE-002', species='cattle', farmer_id=farmer.id),
                    Animal(tag_number='BUFFALO-001', species='buffalo', farmer_id=farmer.id),
                    Animal(tag_number='GOAT-001', species='goat', farmer_id=farmer.id),
                    Animal(tag_number='CATTLE-003', species='cattle', farmer_id=custom_farmer.id),
                    Animal(tag_number='BUFFALO-002', species='buffalo', farmer_id=custom_farmer.id),
                    Animal(tag_number='GOAT-002', species='goat', farmer_id=custom_farmer.id),
                ]
                db.session.add_all(animals)
                db.session.commit()

                # Seed sample AMU entry and RAG evidence
                today = datetime.now().date()
                sample_amu = AMUEntry(
                    entry_id='AMU-2026-001',
                    farmer_id=farmer.id,
                    animal_id=animals[0].id,
                    drug_id=drugs[3].id,  # Oxytetracycline
                    dosage=10.0,
                    unit='mg/kg',
                    route='Intramuscular',
                    indication='Pneumonia',
                    treatment_date=today,
                    withdrawal_end_date=today + timedelta(days=7),
                    status='pending'
                )
                db.session.add(sample_amu)
                db.session.commit()

                rag_res = rag_engine_instance.retrieve_evidence(
                    drug_name=drugs[3].name,
                    species='cattle',
                    route='Intramuscular',
                    indication='Pneumonia',
                    dosage=10.0,
                    unit='mg/kg',
                    treatment_date=today.isoformat()
                )
                sample_rag = RAGEvidence(
                    amu_entry_id=sample_amu.id,
                    document_title=rag_res['document_title'],
                    retrieved_chunk=rag_res['retrieved_chunk'],
                    source_reference=rag_res['source_reference'],
                    recommended_withdrawal_days=rag_res['recommended_withdrawal_days'],
                    max_allowed_dosage=rag_res['max_allowed_dosage'],
                    mrl_info=rag_res['mrl_info'],
                    regulatory_summary=rag_res['regulatory_summary'],
                    verification_status=rag_res['verification_status'],
                    verification_details=rag_res['verification_details']
                )
                db.session.add(sample_rag)
                db.session.commit()

                print("[OK] Sample data added successfully!")
            else:
                print("[OK] Database already has data.")


            custom_user = User.query.filter_by(identifier='kayalvizhi110906', role='farmer').first()
            if not custom_user:
                custom_user = User(
                    identifier='kayalvizhi110906',
                    password_hash=generate_password_hash('password123'),
                    name='Kayalvizhi',
                    role='farmer',
                    phone=''
                )
                db.session.add(custom_user)
                db.session.commit()

        except Exception as e:
            print(f"[ERROR] Database initialization error: {e}")
            raise


if __name__ == '__main__':
    init_db()
    port = int(os.getenv('PORT', 5001))
    print(f"Starting FarmGuard server on http://127.0.0.1:{port}")
    app.run(debug=False, host='0.0.0.0', port=port)
