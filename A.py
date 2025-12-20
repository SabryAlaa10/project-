
"""
=================================================================
🔒 نظام إدارة الجمعية العقارية - الإصدار الآمن
=================================================================
✅ PostgreSQL للبيانات الدائمة
✅ نظام جلسات محسّن
✅ حماية من تسريب البيانات
✅ نسخ احتياطية تلقائية

التعديلات الرئيسية:
1. دعم PostgreSQL مع Supabase (بيانات دائمة)
2. Session Management محسّن
3. اختبار الاتصال بقاعدة البيانات
4. تحذيرات واضحة
"""

import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, ForeignKey, Text, text, inspect
from sqlalchemy.orm import sessionmaker, declarative_base, relationship, Session as SQLSession
from sqlalchemy.pool import NullPool
from datetime import date, datetime
import hashlib
import io
import base64
import os
import shutil
import base64
import numpy
import psycopg2


# ==========================================
# 1. إعدادات الصفحة والتهيئة
# ==========================================
st.set_page_config(
    page_title="نظام إدارة الجمعية العقارية",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# تنسيق CSS (نفس التنسيق السابق - بدون تغيير)
st.markdown("""
    <style>
    /* ============ تنسيق حقول الإدخال ============ */
    input[type="text"],
    input[type="number"],
    input[type="date"],
    textarea {
        background-color: #2a2d3e !important;
        color: #e5e7eb !important;
        border: 2px solid #60a5fa !important;
        border-radius: 6px !important;
        padding: 12px !important;
        font-size: 16px !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
    }
    
    input::placeholder,
    textarea::placeholder {
        color: #9ca3af !important;
        opacity: 0.8 !important;
    }
    
    input[type="text"]:focus,
    input[type="number"]:focus,
    input[type="date"]:focus,
    textarea:focus {
        background-color: #3a3f55 !important;
        color: #a7f3d0 !important;
        border-color: #a7f3d0 !important;
        outline: none !important;
        box-shadow: 0 0 10px rgba(167, 243, 208, 0.4) !important;
    }
    
    select {
        background-color: #2a2d3e !important;
        color: #e5e7eb !important;
        border: 2px solid #60a5fa !important;
        border-radius: 6px !important;
        padding: 10px !important;
        font-size: 16px !important;
    }
    
    select:focus {
        background-color: #3a3f55 !important;
        color: #a7f3d0 !important;
        border-color: #a7f3d0 !important;
        outline: none !important;
    }
    
    select option {
        background-color: #2a2d3e;
        color: #e5e7eb;
        padding: 8px;
    }
    
    .stTextInput input,
    .stNumberInput input,
    .stSelectbox select {
        background-color: #2a2d3e !important;
        color: #e5e7eb !important;
        border: 2px solid #60a5fa !important;
    }
    
    label {
        color: #e5e7eb !important;
        font-weight: 600 !important;
        font-size: 15px !important;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. قاعدة البيانات - الإصدار الآمن
# ==========================================

Base = declarative_base()


# جلب الرابط من secrets
conn_url = st.secrets["connections"]["postgresql"]["url"]

try:
    conn = psycopg2.connect(conn_url)
    st.success("✅ تم الاتصال بنجاح بـ Supabase!")
    conn.close()
except Exception as e:
    st.error(f"❌ فشل الاتصال: {e}")

# ===== دالة الاتصال الذكية =====
# ==========================================
# تحسين إعدادات PostgreSQL - استبدل get_database_engine()
# ==========================================

@st.cache_resource
def get_database_engine():
    """🚀 اتصال محسّن بـ PostgreSQL"""
    try:
        if hasattr(st, 'secrets') and "connections" in st.secrets:
            db_url = st.secrets["connections"]["postgresql"]["url"]
            
            # تصحيح التوافق
            if db_url.startswith('postgres://'):
                db_url = db_url.replace('postgres://', 'postgresql://', 1)
            
            # ✅ إعدادات محسّنة للأداء
            engine = create_engine(
                db_url,
                pool_pre_ping=True,          # فحص الاتصال قبل الاستخدام
                pool_recycle=280,             # تجديد الاتصالات كل 280 ثانية
                pool_size=5,                  # ✅ عدد الاتصالات النشطة (كان مفقود)
                max_overflow=10,              # ✅ اتصالات إضافية عند الحاجة
                pool_timeout=30,              # ✅ وقت الانتظار للحصول على اتصال
                echo=False,                   # ✅ إيقاف SQL logging (يسرّع الأداء)
                connect_args={
                    "connect_timeout": 10,
                    "keepalives": 1,          # ✅ الحفاظ على الاتصال حي
                    "keepalives_idle": 30,    # ✅ فحص كل 30 ثانية
                    "keepalives_interval": 10,
                    "keepalives_count": 5,
                }
            )
            
            # اختبار الاتصال
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return engine, "postgresql"
            
            st.success("✅ Connected to PostgreSQL - Optimized!")
            return engine, "postgresql"
            
    except Exception as e:
        st.warning(f"⚠️ PostgreSQL failed: {e}")
    
    # Fallback to SQLite
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DB_PATH = os.path.join(BASE_DIR, "real_estate_v2.db")
    engine = create_engine(
        f'sqlite:///{DB_PATH}',
        connect_args={'check_same_thread': False},
        pool_pre_ping=True
    )
    
    st.error("⚠️ Using SQLite - Data is TEMPORARY!")
    return engine, "sqlite"


# إنشاء الاتصال
engine, db_type = get_database_engine()

# ===== Session Factory الآمنة =====
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

def get_db_session() -> SQLSession:
    """
    🔒 الحصول على جلسة آمنة من قاعدة البيانات
    """
    db = SessionLocal()
    try:
        return db
    except Exception as e:
        db.close()
        raise e

if db_type == "postgresql":
    st.sidebar.success("✅ متصل بسحابة Supabase")
else:
    st.sidebar.warning("⚠️ يعمل بنمط SQLite المحلي")
# الجلسة الرئيسية


# ==========================================
# 3. النماذج (Models) - نفس التعريفات السابقة
# ==========================================

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False)

class Asset(Base):
    __tablename__ = 'assets'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    location = Column(String)
    description = Column(Text)

class Unit(Base):
    __tablename__ = 'units'
    id = Column(Integer, primary_key=True)
    asset_id = Column(Integer, ForeignKey('assets.id'))
    unit_number = Column(String, nullable=False)
    floor = Column(String)
    area = Column(Float)
    usage_type = Column(String)
    status = Column(String, default="فاضي")
    asset = relationship("Asset")

class Tenant(Base):
    __tablename__ = 'tenants'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    type = Column(String)
    phone = Column(String)
    email = Column(String)
    national_id = Column(String)
    address = Column(Text)
    notes = Column(Text)
    created_date = Column(Date, default=date.today)

class Contract(Base):
    __tablename__ = 'contracts'
    id = Column(Integer, primary_key=True)
    contract_number = Column(String, unique=True)
    tenant_id = Column(Integer, ForeignKey('tenants.id'))
    contract_type = Column(String)
    rent_amount = Column(Float)
    payment_freq = Column(String)
    start_date = Column(Date)
    end_date = Column(Date)
    vat_rate = Column(Float, default=0.0)
    linked_units_ids = Column(String)
    status = Column(String, default="نشط")
    cancellation_reason = Column(Text, nullable=True)
    cancelled_by = Column(String, nullable=True)
    cancellation_date = Column(Date, nullable=True)
    tenant = relationship("Tenant")

class Payment(Base):
    __tablename__ = 'payments'
    id = Column(Integer, primary_key=True)
    contract_id = Column(Integer, ForeignKey('contracts.id'))
    payment_number = Column(Integer)
    due_date = Column(Date)
    paid_date = Column(Date, nullable=True)
    amount = Column(Float)
    vat = Column(Float)
    total = Column(Float)
    paid_amount = Column(Float, default=0.0)
    remaining_amount = Column(Float, default=0.0)
    status = Column(String)
    beneficiary = Column(String)
    payment_method = Column(String)
    contract = relationship("Contract")

# إنشاء الجداول
Base.metadata.create_all(engine)

from contextlib import contextmanager

@contextmanager
def get_safe_session():
    """
    ✅ إدارة آمنة للـ session مع إغلاق تلقائي
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ❌ احذف هذا السطر (السطر 234):
# session = get_db_session()

# ✅ استبدله بدالة للحصول على session عند الحاجة:
def get_session():
    """احصل على session جديدة"""
    return SessionLocal()

# ==========================================
# مثال على الاستخدام الصحيح:
# ==========================================

# ❌ الطريقة القديمة (خطأ):
# users = session.query(User).all()

# ✅ الطريقة الصحيحة (بعد تعريف User):
with get_safe_session() as session:
    users = session.query(User).all()


# ==========================================
# إضافة Caching - ضعه بعد imports
# ==========================================

from functools import lru_cache
from datetime import datetime, timedelta

# Cache للبيانات الثابتة (تنتهي صلاحيته كل 5 دقائق)
@st.cache_data(ttl=300)
def get_cached_assets():
    with get_safe_session() as session:
        return pd.read_sql(session.query(Asset).statement, session.bind)

@st.cache_data(ttl=300)
def get_cached_units(asset_id=None):
    with get_safe_session() as session:
        query = session.query(Unit)
        if asset_id:
            query = query.filter_by(asset_id=asset_id)
        return pd.read_sql(query.statement, session.bind)

@st.cache_data(ttl=300)
def get_cached_tenants():
    with get_safe_session() as session:
        return pd.read_sql(session.query(Tenant).statement, session.bind)

@st.cache_data(ttl=60)  # 1 minute للبيانات المتغيرة
def get_cached_contracts(status="نشط"):
    """جلب العقود مع caching"""
    with get_safe_session() as session:
        return session.query(Contract).filter_by(status=status).all()

# ==========================================
# مثال الاستخدام:
# ==========================================

# ❌ القديم:
# assets = session.query(Asset).all()

# ✅ الجديد:
assets = get_cached_assets()

# ==========================================
# 4. تحديث الجداول الموجودة (Migration)
# ==========================================

@st.cache_resource # 🔥 تعمل مرة واحدة فقط عند تشغيل السيرفر
def run_migrations():
    """تحديث هيكل قاعدة البيانات بدون إبطاء التطبيق"""
    inspector = inspect(engine)
    try:
        with engine.begin() as conn:
            # تحديث جدول العقود
            contracts_cols = [col['name'] for col in inspector.get_columns('contracts')]
            if 'status' not in contracts_cols:
                conn.execute(text("ALTER TABLE contracts ADD COLUMN status VARCHAR DEFAULT 'نشط'"))
            
            if 'cancellation_reason' not in contracts_cols:
                conn.execute(text("ALTER TABLE contracts ADD COLUMN cancellation_reason TEXT"))

            # تحديث جدول الدفعات
            payments_cols = [col['name'] for col in inspector.get_columns('payments')]
            if 'paid_amount' not in payments_cols:
                conn.execute(text("ALTER TABLE payments ADD COLUMN paid_amount FLOAT DEFAULT 0.0"))
            
        return "✅ Migrations completed successfully"
    except Exception as e:
        return f"⚠️ Migration skipped: {e}"

# تنفيذ الهجرة مرة واحدة
migration_status = run_migrations()

# ==========================================
# 5. دوال مساعدة
# ==========================================

def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_login(username, password):
    """التحقق من الدخول باستخدام جلسة آمنة"""
    username = username.strip().lower()
    with get_safe_session() as session:
        user = session.query(User).filter_by(username=username).first()
        if user and user.password_hash == hash_password(password):
            # نرجع كائن المستخدم قبل إغلاق الجلسة
            return {"username": user.username, "role": user.role, "id": user.id}
    return None

# ==========================================
# 6. تهيئة البيانات الأولية
# ==========================================

# def init_seed_data():
#     """تهيئة البيانات الأولية بطريقة سريعة ولا تستهلك الموارد"""
    
#     # نفتح Session جديدة مؤقتة للتحقق
#     local_session = SessionLocal()
#     try:
#         # التحقق من وجود مستخدمين (بسرعة وبأقل حجم بيانات)
#         exists = local_session.query(User.id).first()
        
#         if exists:
#             return  # البيانات موجودة.. اخرج فوراً
            
#         st.info("🌱 Initializing seed data...")
        
#         # إضافة المستخدمين
#         admin = User(username="admin", password_hash=hash_password("admin123"), role="Admin")
#         emp = User(username="emp", password_hash=hash_password("emp123"), role="Employee")
        
#         local_session.add_all([admin, emp])
#         local_session.commit()
#         st.success("✅ Seed data initialized successfully")
        
#     except Exception as e:
#         local_session.rollback()
#         print(f"Error seeding data: {e}")
#     finally:
#         local_session.close() # ضروري جداً قفل الاتصال عشان ميفضلش معلق ويتقل البرنامج

# # استدعاء الدالة داخل الـ main أو مرة واحدة فقط
# if 'data_seeded' not in st.session_state:
#     init_seed_data()
#     st.session_state['data_seeded'] = True

# ==========================================
# 7. تحذير حالة قاعدة البيانات
# ==========================================

def show_database_status():
    """
    🚨 إظهار تحذير إذا كانت قاعدة البيانات مؤقتة
    """
    if db_type == 'sqlite':
        st.markdown("""
        <div style="background-color: #3d1e1e; padding: 15px; border-radius: 10px; border-left: 5px solid #ff4444; margin-bottom: 20px;">
            <h4 style="color: #ff6b6b; margin: 0 0 10px 0;">🚨 تحذير: قاعدة بيانات مؤقتة!</h4>
            <p style="margin: 0; font-size: 14px;">
                <strong>البيانات الحالية مؤقتة وستُفقد عند إعادة التشغيل!</strong><br>
                يجب ربط قاعدة بيانات PostgreSQL من Streamlit Secrets.<br>
                <a href="https://supabase.com" target="_blank" style="color: #60a5fa;">سجل مجاناً في Supabase</a>
            </p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.success("✅ متصل بقاعدة بيانات دائمة (PostgreSQL)")

# ==========================================
# 8. اختبار الاتصال
# ==========================================

def test_database_connection():
    """
    🔌 اختبار اتصال قاعدة البيانات - نسخة سريعة وآمنة
    """
    st.subheader("🔌 حالة الاتصال بقاعدة البيانات")
    
    try:
        # ✅ استخدام الجلسة الآمنة بدلاً من المتغير العام session
        with get_safe_session() as session:
            user_count = session.query(User).count()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if db_type == 'postgresql':
                st.metric("نوع قاعدة البيانات", "PostgreSQL ✅")
                st.success("البيانات مخزنة سحابياً (Supabase)")
            else:
                st.metric("نوع قاعدة البيانات", "SQLite ⚠️")
                st.error("بيانات محلية مؤقتة")
        
        with col2:
            st.metric("عدد المستخدمين", user_count)
        
        with col3:
            st.metric("حالة الاتصال", "متصل ✅")

    except Exception as e:
        st.error(f"❌ فشل الاتصال: {str(e)}")

# ==========================================
# 9. دوال النسخ الاحتياطي (نفس السابق)
# ==========================================

def create_backup():
    """إنشاء نسخة احتياطية (تعمل فقط في النمط المحلي)"""
    if db_type == 'postgresql':
        return False, None, "ℹ️ في PostgreSQL، يتم النسخ الاحتياطي تلقائياً عبر Supabase Dashboard."

    try:
        source_db = "real_estate.db" # تأكد من مطابقة الاسم الذي استخدمناه في البداية
        if not os.path.exists(source_db):
            return False, None, "❌ ملف قاعدة البيانات غير موجود."
        
        backup_dir = "backups"
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(backup_dir, f"backup_{timestamp}.db")
        
        shutil.copy2(source_db, backup_path)
        return True, backup_path, "✅ تم إنشاء نسخة محلية بنجاح"
    except Exception as e:
        return False, None, f"❌ خطأ: {str(e)}"

def restore_backup(uploaded_file):
    """استرجاع نسخة احتياطية"""
    try:
        db_file = "real_estate_v2.db"
        
        if os.path.exists(db_file):
            backup_current = f"{db_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(db_file, backup_current)
        
        with open(db_file, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        return True, "✅ تم استرجاع النسخة الاحتياطية بنجاح!"
        
    except Exception as e:
        return False, f"❌ حدث خطأ أثناء الاسترجاع: {str(e)}"

# ==========================================
# 10. صفحة النسخ الاحتياطي المحدثة
# ==========================================

def backup_page():
    """صفحة إدارة النسخ الاحتياطية"""
    
    st.header("💾 إدارة النسخ الاحتياطية")
    
    if st.session_state.get('user_role') != 'Admin':
        st.error("⚠️ هذه الصفحة متاحة للمدير فقط")
        return
    
    # إظهار حالة قاعدة البيانات
    show_database_status()
    
    # اختبار الاتصال
    with st.expander("🔌 اختبار الاتصال", expanded=False):
        test_database_connection()
    
    st.markdown("---")
    
    # باقي كود النسخ الاحتياطي (نفس السابق)
    st.subheader("📤 حفظ نسخة احتياطية")
    
    if db_type == 'sqlite':
        if st.button("📥 تحميل نسخة احتياطية", type="primary", use_container_width=True):
            with st.spinner("جاري إنشاء النسخة..."):
                success, backup_path, message = create_backup()
                
                if success:
                    with open(backup_path, "rb") as f:
                        file_data = f.read()
                    
                    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
                    st.download_button(
                        label="⬇️ اضغط هنا لتحميل الملف",
                        data=file_data,
                        file_name=f"نسخة_احتياطية_{timestamp}.db",
                        mime="application/octet-stream",
                        use_container_width=True,
                        type="primary"
                    )
                    st.success(message)
                    
                    try:
                        os.remove(backup_path)
                    except:
                        pass
                else:
                    st.error(message)
    else:
        st.info("""
        ✅ أنت متصل بـ PostgreSQL
        
        البيانات محفوظة تلقائياً ولا تحتاج نسخ احتياطي يدوي.
        لكن يُنصح بتنزيل نسخة احتياطية شهرياً كإجراء إضافي.
        """)

# ==========================================
# 11. صفحة تسجيل الدخول
# ==========================================

# وضع هذا التنسيق في دالة مخبأة لتوفير المعالجة
@st.cache_data
def get_login_styles():
    return """
    <style>
        .login-card {
            background: #1E1E1E;
            padding: 30px;
            border-radius: 13px;
            text-align: center;
            border: 2px solid #764ba2;
        }
    </style>
    """

def login_page():
    st.markdown(get_login_styles(), unsafe_allow_html=True)
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # محاولة تحميل اللوجو مرة واحدة وتخزينه في الكاش
        try:
            st.image("logo.png", use_container_width=True)
        except:
            st.markdown("<h1 style='text-align:center; color:#6B9B7A;'>جمعية زواج</h1>", unsafe_allow_html=True)

        # استخدام st.form لمنع التطبيق من إعادة التشغيل مع كل حرف تكتبه (تسريع مذهل)
        with st.form("login_form"):
            st.subheader("🔐 تسجيل الدخول")
            username = st.text_input("👤 اسم المستخدم").strip().lower()
            password = st.text_input("🔒 كلمة المرور", type="password").strip()
            submit = st.form_submit_button("🚀 دخول", use_container_width=True)
            
            if submit:
                if not username or not password:
                    st.error("⚠️ الرجاء إدخال البيانات")
                else:
                    user = check_login(username, password)
                    if user:
                        st.session_state['logged_in'] = True
                        st.session_state['user_role'] = user['role']
                        st.session_state['username'] = user['username']
                        st.success("✅ تم الدخول")
                        st.rerun()
                    else:
                        st.error("❌ بيانات غير صحيحة")


from sqlalchemy import func

@st.cache_data(ttl=600)  # تخزين النتائج لمدة 10 دقائق
def get_dashboard_stats():
    """حساب المؤشرات داخل قاعدة البيانات مباشرة لسرعة قصوى"""
    with get_safe_session() as session:
        # 1. إجمالي الدخل المحصل
        income = session.query(func.sum(Payment.total)).join(Contract).filter(
            Payment.status == 'مدفوع',
            Contract.status == "نشط"
        ).scalar() or 0

        # 2. المتأخرات (المبلغ والعدد)
        overdue_query = session.query(
            func.count(Payment.id),
            func.sum(Payment.total)
        ).join(Contract).filter(
            Payment.status != 'مدفوع',
            Payment.due_date < date.today(),
            Contract.status == "نشط"
        ).first()
        
        # 3. حالات الوحدات
        rented = session.query(func.count(Unit.id)).filter_by(status='مؤجر').scalar()
        empty = session.query(func.count(Unit.id)).filter_by(status='فاضي').scalar()

        return {
            "income": income,
            "overdue_count": overdue_query[0] or 0,
            "overdue_amount": overdue_query[1] or 0,
            "rented": rented,
            "empty": empty
        }
    
@st.cache_data(ttl=300)
def get_dashboard_alerts():
    with get_safe_session() as session:
        # تنبيهات الدفعات (خلال 30 يوم قادمة)
        upcoming_pays = session.query(Payment, Tenant.name).\
            join(Contract, Payment.contract_id == Contract.id).\
            join(Tenant, Contract.tenant_id == Tenant.id).\
            filter(Payment.status != "مدفوع").\
            filter(Payment.due_date >= date.today()).\
            filter(Payment.due_date <= date.today() + timedelta(days=30)).\
            order_by(Payment.due_date).all()

        # تنبيهات انتهاء العقود (خلال 60 يوم قادمة)
        exp_date = date.today() + timedelta(days=60)
        expiring_contracts = session.query(Contract, Tenant.name).\
            join(Tenant, Contract.tenant_id == Tenant.id).\
            filter(Contract.status == "نشط").\
            filter(Contract.end_date >= date.today()).\
            filter(Contract.end_date <= exp_date).\
            order_by(Contract.end_date).all()
            
        return upcoming_pays, expiring_contracts
    
def dashboard():
    st.title("📊 لوحة المؤشرات الذكية")
    
    # جلب البيانات
    stats = get_dashboard_stats()
    upcoming_pays, expiring_contracts = get_dashboard_alerts()

    # عرض الـ KPIs (المؤشرات الرئيسية)
    c1, c2, c3, c4 = st.columns(4)
    # استخدام or 0 لتجنب أخطاء الجمع
    income = stats.get('income') or 0
    overdue_amt = stats.get('overdue_amount') or 0
    
    c1.metric("إجمالي التحصيل", f"{income:,.0f} ريال")
    c2.metric("المتأخرات الحالية", f"{overdue_amt:,.0f} ريال", f"{stats.get('overdue_count', 0)} دفعة", delta_color="inverse")
    c3.metric("الوحدات المؤجرة", stats.get('rented', 0))
    c4.metric("الوحدات الشاغرة", stats.get('empty', 0))

    st.markdown("---")
    
    col_chart, col_alerts = st.columns([1, 1.5])
    
    with col_chart:
        st.subheader("🏢 إشغال الوحدات")
        status_df = pd.DataFrame({
            'الحالة': ['مؤجرة', 'شاغرة'], 
            'العدد': [stats.get('rented', 0), stats.get('empty', 0)]
        })
        # عرض رسم بياني دائري (أفضل لحالة الوحدات)
        st.bar_chart(status_df.set_index('الحالة'), color="#3b82f6")

    with col_alerts:
        st.subheader("⏰ تنبيهات التحصيل (30 يوم)")
        if upcoming_pays:
            for item in upcoming_pays:
                # التأكد من طريقة فك الحزمة (Unpacking)
                pay, t_name = item 
                
                days = (pay.due_date - date.today()).days
                # تنسيق المبلغ والحالة
                amt = pay.total or 0
                if days == 0:
                    st.error(f"🔴 **اليوم**: {t_name} (المبلغ: {amt:,.0f} ريال)")
                elif days == 1:
                    st.warning(f"🟠 **غداً**: {t_name} (المبلغ: {amt:,.0f} ريال)")
                else:
                    st.info(f"🔵 **بعد {days} يوم**: {t_name} (المبلغ: {amt:,.0f} ريال)")
        else:
            st.success("✅ لا توجد دفعات مستحقة قريباً")

    st.markdown("---")
    
    # تنبيهات العقود
    with st.expander("📋 عقود تقترب من الانتهاء (تجديد/إخلاء)", expanded=True):
        if expiring_contracts:
            for item in expiring_contracts:
                cont, t_name = item
                days = (cont.end_date - date.today()).days
                st.warning(f"⚠️ عقد **{t_name}** (رقم: {cont.contract_number or cont.id}) - ينتهي خلال {days} يوم")
        else:
            st.success("✅ جميع العقود سارية لفترة كافية")

def manage_assets():
    st.header("🏢 إدارة الأصول والوحدات")
    
    # 1. جلب الأصول باستخدام الكاش (سريع جداً)
    assets_df = get_cached_assets() 

    if assets_df.empty:
        st.info("لا توجد أصول مُضافة بعد.")
        return
    
    # 2. جلب المؤشرات في عملية واحدة بدلاً من 3 استعلامات
    stats = get_dashboard_stats()
    
    st.subheader("📊 ملخص الأصول")
    col1, col2, col3 = st.columns(3)
    col1.metric("إجمالي الأصول", len(assets_df))
    col2.metric("إجمالي الوحدات", stats['rented'] + stats['empty'])
    col3.metric("الوحدات المؤجرة", stats['rented'])
    
    st.markdown("---")
    
    # 3. قسم الإدارة (Admin)
    if st.session_state.get('user_role') == 'Admin':
        st.subheader("⚙️ إدارة الوحدات (مدير)")
        tab1, tab2 = st.tabs(["✏️ تعديل وحدة موجودة", "➕ إضافة وحدة جديدة"])

        with tab1:
            st.markdown("#### تعديل أو حذف وحدة")
            
            # بدلاً من الاستعلام، نأخذ الأسماء من الـ DataFrame الموجود في الذاكرة
            asset_options = dict(zip(assets_df['name'], assets_df['id']))
            selected_asset_name = st.selectbox("🏢 اختر الأصل", options=list(asset_options.keys()), key='edit_asset_sel')
            selected_asset_id = asset_options[selected_asset_name]

            # جلب الوحدات لهذا الأصل فقط
            with get_safe_session() as session:
                units = session.query(Unit).filter_by(asset_id=selected_asset_id).all()
                
                if units:
                    # تحويل الوحدات لقاموس لسهولة الوصول
                    unit_map = {f"وحدة {u.unit_number} - {u.usage_type} ({u.status})": u.id for u in units}
                    selected_unit_label = st.selectbox("🔑 اختر الوحدة", options=list(unit_map.keys()))
                    unit_id = unit_map[selected_unit_label]
                    
                    # جلب بيانات الوحدة المختارة
                    unit_to_manage = session.get(Unit, unit_id)
                    
                    # فحص العقود المرتبطة (استعلام سريع)
                    has_active = session.query(Contract).filter(
                        Contract.linked_units_ids.like(f"%{unit_id}%"),
                        Contract.status == "نشط"
                    ).count() > 0

                    st.markdown("---")
                    e_tab, d_tab = st.tabs(["📝 تعديل", "🗑️ حذف"])

                    with e_tab:
                        with st.form("quick_edit_unit"):
                            col_a, col_b = st.columns(2)
                            new_floor = col_a.text_input("الدور", value=unit_to_manage.floor or "")
                            new_status = col_b.selectbox("الحالة", ["فاضي", "مؤجر", "تحت الصيانة"], 
                            index=["فاضي", "مؤجر", "تحت الصيانة"].index(unit_to_manage.status))
                            
                            if st.form_submit_button("💾 حفظ التعديلات", use_container_width=True):
                                unit_to_manage.floor = new_floor
                                unit_to_manage.status = new_status
                                session.commit()
                                st.success("✅ تم التحديث")
                                st.rerun()

                    with d_tab:
                        if has_active:
                            st.error("🚫 لا يمكن الحذف: الوحدة مرتبطة بعقد نشط")
                        else:
                            st.warning("⚠️ سيتم حذف الوحدة نهائياً")
                            if st.checkbox(f"تأكيد حذف وحدة {unit_to_manage.unit_number}"):
                                if st.button("🗑️ تنفيذ الحذف الآن"):
                                    session.delete(unit_to_manage)
                                    session.commit()
                                    st.success("Deleted!")
                                    st.rerun()
                else:
                    st.info("لا توجد وحدات في هذا الأصل")
        
        # ===================================================================
        # Tab 2: إضافة وحدة جديدة (Admin)
        # ===================================================================
        with tab2:
            st.markdown("#### إضافة وحدة جديدة للأصل")
            
            with st.form("add_unit_form", clear_on_submit=True):
                # استخدام session جديد هنا
                with get_safe_session() as session_add:
                    asset_list_add = session_add.query(Asset).all()
                    asset_names_add = [a.name for a in asset_list_add]
                
                selected_asset_add = st.selectbox(
                    "🏢 اختر الأصل",
                    asset_names_add,
                    key='add_asset_select'
                )
                
                st.markdown("---")
                st.markdown("##### 📝 بيانات الوحدة الجديدة")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    unit_num_new = st.text_input("رقم/اسم الوحدة *", placeholder="مثال: 101، A1")
                with col2:
                    floor_new = st.text_input("الدور", placeholder="مثال: 1، أرضي")
                with col3:
                    usage_new = st.selectbox("نوع الاستخدام", ["سكني", "تجاري", "حق انتفاع", "سكن عمال"], key='usage_new')
                
                area_new = st.number_input("المساحة (م²) - اختياري", min_value=0.0, value=0.0, step=0.5, key='area_new')
                
                st.markdown("---")
                submit_add = st.form_submit_button("✅ إضافة الوحدة", use_container_width=True, type="primary")
                
                if submit_add:
                    if not unit_num_new.strip():
                        st.error("⚠️ الرجاء إدخال رقم/اسم الوحدة")
                    else:
                        with get_safe_session() as session_submit:
                            selected_asset_obj = next((a for a in asset_list_add if a.name == selected_asset_add), None)
                            
                            if selected_asset_obj:
                                existing = session_submit.query(Unit).filter(
                                    Unit.asset_id == selected_asset_obj.id,
                                    Unit.unit_number == unit_num_new.strip()
                                ).first()
                                
                                if existing:
                                    st.error(f"⚠️ رقم الوحدة '{unit_num_new}' موجود بالفعل في هذا الأصل")
                                else:
                                    new_unit = Unit(
                                        asset_id=selected_asset_obj.id,
                                        unit_number=unit_num_new.strip(),
                                        usage_type=usage_new,
                                        floor=floor_new.strip() if floor_new else None,
                                        area=area_new if area_new > 0 else None,
                                        status="فاضي"
                                    )
                                    session_submit.add(new_unit)
                                    session_submit.commit()
                                    st.success(f"✅ تم إضافة الوحدة **{unit_num_new}** بنجاح!")
                                    st.rerun()

    # -------------------------------------------------------------------------
    # 2. للموظف (Employee): إضافة فقط
    # -------------------------------------------------------------------------
    elif st.session_state.get('user_role') == 'Employee':
        st.subheader("➕ إضافة وحدة جديدة")
        st.info("ℹ️ كموظف، يمكنك إضافة وحدات جديدة فقط. للتعديل أو الحذف، تواصل مع المدير.")
        
        with st.form("add_unit_form_employee", clear_on_submit=True):
            # استخدام session جديد للموظف
            with get_safe_session() as session_emp:
                asset_list_add = session_emp.query(Asset).all()
                asset_names_add = [a.name for a in asset_list_add]
            
            selected_asset_add = st.selectbox(
                "🏢 اختر الأصل",
                asset_names_add,
                key='add_asset_select_emp'
            )
            
            st.markdown("---")
            st.markdown("##### 📝 بيانات الوحدة الجديدة")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                unit_num_new = st.text_input("رقم/اسم الوحدة *", placeholder="مثال: 101، A1")
            with col2:
                floor_new = st.text_input("الدور", placeholder="مثال: 1، أرضي")
            with col3:
                usage_new = st.selectbox("نوع الاستخدام", ["سكني", "تجاري", "حق انتفاع", "سكن عمال"], key='usage_new_emp')
            
            area_new = st.number_input("المساحة (م²) - اختياري", min_value=0.0, value=0.0, step=0.5, key='area_new_emp')
            
            st.markdown("---")
            submit_add = st.form_submit_button("✅ إضافة الوحدة", use_container_width=True, type="primary")
            
            if submit_add:
                if not unit_num_new.strip():
                    st.error("⚠️ الرجاء إدخال رقم/اسم الوحدة")
                else:
                    with get_safe_session() as session_submit_emp:
                        selected_asset_obj = next((a for a in asset_list_add if a.name == selected_asset_add), None)
                        
                        if selected_asset_obj:
                            existing = session_submit_emp.query(Unit).filter(
                                Unit.asset_id == selected_asset_obj.id,
                                Unit.unit_number == unit_num_new.strip()
                            ).first()
                            
                            if existing:
                                st.error(f"⚠️ رقم الوحدة '{unit_num_new}' موجود بالفعل في هذا الأصل")
                            else:
                                new_unit = Unit(
                                    asset_id=selected_asset_obj.id,
                                    unit_number=unit_num_new.strip(),
                                    usage_type=usage_new,
                                    floor=floor_new.strip() if floor_new else None,
                                    area=area_new if area_new > 0 else None,
                                    status="فاضي"
                                )
                                session_submit_emp.add(new_unit)
                                session_submit_emp.commit()
                                st.success(f"✅ تم إضافة الوحدة **{unit_num_new}** بنجاح!")
                                st.rerun()

    # =========================================================================
    # قسم عرض تفاصيل الوحدات (للجميع)
    # =========================================================================
    st.markdown("---")
    st.subheader("🔍 عرض تفاصيل الوحدات")
    
    view_asset_names = assets_df['name'].tolist()  # استخدام assets_df بدلاً من assets
    
    if view_asset_names:
        selected_view_asset = st.selectbox(
            "اختر الأصل لعرض وحداته",
            view_asset_names,
            key='view_asset_select'
        )
        
        # العثور على ID الأصل من DataFrame
        view_asset_row = assets_df[assets_df['name'] == selected_view_asset]
        if not view_asset_row.empty:
            view_asset_id = int(view_asset_row['id'].values[0])
            
            # جلب الوحدات باستخدام session جديد
            with get_safe_session() as session_view:
                view_units = session_view.query(Unit).filter(Unit.asset_id == view_asset_id).all()
                
                if view_units:
                    # عرض إحصائيات سريعة
                    vacant = sum(1 for u in view_units if u.status == 'فاضي')
                    rented = sum(1 for u in view_units if u.status == 'مؤجر')
                    maintenance = sum(1 for u in view_units if u.status == 'تحت الصيانة')
                    
                    col1, col2, col3 = st.columns(3)
                    with col1: st.metric("🟢 فارغة", vacant)
                    with col2: st.metric("🔴 مؤجرة", rented)
                    with col3: st.metric("🟡 صيانة", maintenance)
                    
                    # إنشاء DataFrame للعرض
                    units_display_data = []
                    for u in view_units:
                        status_icon = {
                            "فاضي": "🟢",
                            "مؤجر": "🔴",
                            "تحت الصيانة": "🟡"
                        }.get(u.status, "⚪")
                        
                        units_display_data.append({
                            'رقم الوحدة': u.unit_number,
                            'الدور': u.floor if u.floor else '-',
                            'النوع': u.usage_type,
                            'الحالة': f"{status_icon} {u.status}",
                            'المساحة (م²)': u.area if u.area else '-'
                        })
                    
                    units_df = pd.DataFrame(units_display_data)
                    
                    st.dataframe(
                        units_df,
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.info("لا توجد وحدات مضافة لهذا الأصل بعد.")
        else:
            st.error("حدث خطأ في تحديد الأصل المختار.")
    else:
        st.info("لا توجد أصول لعرض وحداتها.")

def generate_contract_payments(session, contract):
    """توليد دفعات الإيجار تلقائياً بناءً على المدة والدورية"""
    from dateutil.relativedelta import relativedelta
    
    # تحديد عدد الشهور بناءً على الدورية
    freq_map = {"شهري": 1, "ربع سنوي": 3, "نصف سنوي": 6, "سنوي": 12}
    months_step = freq_map.get(contract.payment_freq, 12)
    
    # حساب عدد الدفعات الإجمالي
    total_months = (contract.end_date.year - contract.start_date.year) * 12 + (contract.end_date.month - contract.start_date.month)
    num_payments = max(1, total_months // months_step)
    
    # القيمة لكل دفعة (شاملة الضريبة إذا كان تجارياً)
    amount_per_period = (contract.rent_amount / (12 / months_step))
    vat_amount = amount_per_period * contract.vat_rate
    total_with_vat = amount_per_period + vat_amount

    for i in range(num_payments):
        payment_date = contract.start_date + relativedelta(months=(i * months_step))
        new_payment = Payment(
            contract_id=contract.id,
            amount=total_with_vat,
            due_date=payment_date,
            status="معلق"
        )
        session.add(new_payment)


def manage_contracts():
    st.header("📄 إدارة العقود")
    # الموظف يقدر يضيف عقود فقط، المدير يقدر يضيف ويعدل
    if st.session_state['user_role'] in ['Admin', 'Employee']:
        if st.session_state['user_role'] == 'Employee':
            st.info("ℹ️ كموظف، يمكنك إضافة عقود جديدة فقط. لا يمكنك حذف العقود الموجودة.")
        
        with st.expander("إنشاء عقد جديد", expanded=True):
            with st.form("new_contract"):
                tenants = session.query(Tenant).all()
                t_dict = {t.name: t.id for t in tenants}
                
                # وحدات غير مؤجرة
                all_units = session.query(Unit).all()
                u_options = {}
                for u in all_units:
                    contract_exists = session.query(Contract).filter(
                        Contract.linked_units_ids.like(f"%{u.id}%")
                    ).first()
                    
                    if u.status == 'فاضي' or (u.status == 'مؤجر' and not contract_exists):
                        u_options[f"{u.unit_number} ({u.asset.name})"] = u.id

                st.markdown("#### 📋 بيانات العقد الأساسية")
                
                # الصف الأول: رقم العقد والمستأجر ونوع العقد
                c1, c2, c3 = st.columns(3)
                contract_number = c1.text_input(
                    "رقم العقد *", 
                    placeholder="مثال: C-2024-001",
                    help="رقم مرجعي للعقد"
                )
                t_name = c2.selectbox("المستأجر *", list(t_dict.keys()))
                c_type = c3.selectbox("نوع العقد", ["سكني", "تجاري", "حق انتفاع"])
                
                # اختيار الوحدات
                sel_units = st.multiselect(
                    "🏢 اختر الوحدات *", 
                    list(u_options.keys()),
                    help="يمكنك اختيار أكثر من وحدة"
                )
                
                st.markdown("---")
                st.markdown("#### 💰 البيانات المالية والمدة")
                
                # الصف الثاني: القيمة، الدفع، مدة العقد
                r1, r2, r3 = st.columns(3)
                rent = r1.number_input(
                    "القيمة السنوية (ريال)", 
                    min_value=0.0,
                    step=1000.0,
                    help="القيمة الإجمالية للإيجار السنوي"
                )
                freq = r2.selectbox(
                    "دورية الدفع", 
                    ["سنوي", "نصف سنوي", "ربع سنوي", "شهري"]
                )
                contract_duration = r3.number_input(
                    "مدة العقد (بالسنوات)", 
                    min_value=1, 
                    max_value=10, 
                    value=1,
                    step=1,
                    help="مدة العقد بالسنوات (الافتراضي: سنة واحدة)"
                )
                
                # الصف الثالث: تاريخ البداية والنهاية (محسوبة تلقائياً)
                r4, r5 = st.columns(2)
                s_date = r4.date_input("تاريخ بداية العقد")
                
                # حساب تاريخ النهاية بناءً على المدة
                calculated_end_date = s_date.replace(year=s_date.year + int(contract_duration))
                r5.date_input(
                    "تاريخ نهاية العقد (محسوب تلقائياً)", 
                    value=calculated_end_date,
                    disabled=True,
                    help=f"سينتهي العقد في {calculated_end_date}"
                )
                
                # عرض ملخص VAT
                if c_type == "تجاري":
                    st.info("ℹ️ سيتم إضافة ضريبة القيمة المضافة 15% على الدفعات (عقد تجاري)")
                else:
                    st.info("ℹ️ لا توجد ضريبة قيمة مضافة (عقد غير تجاري)")
                
                st.markdown("---")
                
                # زر الحفظ
                col_btn1, col_btn2 = st.columns([3, 1])
                with col_btn1:
                    submitted = st.form_submit_button(
                        "✅ حفظ العقد وإنشاء الدفعات",
                        use_container_width=True,
                        type="primary"
                    )
                
                if submitted:
                    # التحقق من البيانات المطلوبة
                    errors = []
                    
                    if not contract_number.strip():
                        errors.append("⚠️ رقم العقد مطلوب")
                    else:
                        # التحقق من عدم تكرار رقم العقد
                        existing_contract = session.query(Contract).filter_by(contract_number=contract_number.strip()).first()
                        if existing_contract:
                            errors.append(f"⚠️ رقم العقد '{contract_number}' موجود بالفعل")
                    
                    if not sel_units:
                        errors.append("⚠️ يجب اختيار وحدة واحدة على الأقل")
                    
                    if rent <= 0:
                        errors.append("⚠️ القيمة السنوية يجب أن تكون أكبر من صفر")
                    
                    if errors:
                        for err in errors:
                            st.error(err)
                    else:
                        from dateutil.relativedelta import relativedelta
                        
                        # 1. حساب تاريخ النهاية بدقة (باستخدام relativedelta)
                        e_date = s_date + relativedelta(years=int(contract_duration))
                        
                        u_ids = ",".join([str(u_options[u]) for u in sel_units])
                        vat = 0.15 if c_type == "تجاري" else 0.0
                        
                        # 2. إنشاء كائن العقد
                        new_c = Contract(
                            contract_number=contract_number.strip(),
                            tenant_id=t_dict[t_name], 
                            contract_type=c_type, 
                            rent_amount=rent,
                            payment_freq=freq, 
                            start_date=s_date, 
                            end_date=e_date,
                            vat_rate=vat, 
                            linked_units_ids=u_ids,
                            status="نشط"
                        )
                        session.add(new_c)
                        session.flush()  # للحصول على معرف العقد (ID) قبل الحفظ النهائي

                        # 3. تحديث حالة الوحدات إلى مؤجر
                        for u_label in sel_units:
                            uid = u_options[u_label]
                            u_obj = session.get(Unit, uid)
                            if u_obj:
                                u_obj.status = "مؤجر"
                        
                        # 4. توليد الدفعات المالية تلقائياً
                        # ==========================================
                        freq_map = {"شهري": 1, "ربع سنوي": 3, "نصف سنوي": 6, "سنوي": 12}
                        months_step = freq_map.get(freq, 12)
                        
                        # حساب عدد الدفعات بناءً على المدة والدورية
                        total_months = int(contract_duration) * 12
                        num_payments = total_months // months_step
                        
                        # حساب قيمة الدفعة الواحدة مع الضريبة
                        base_payment = rent / (12 / months_step)
                        total_payment = base_payment * (1 + vat)

                        for i in range(num_payments):
                            p_due_date = s_date + relativedelta(months=(i * months_step))
                            new_p = Payment(
                                contract_id=new_c.id,
                                amount=total_payment,
                                due_date=p_due_date,
                                status="معلق"
                            )
                            session.add(new_p)
                        # ==========================================

                        session.commit()
                        st.success(f"✅ تم إنشاء العقد رقم {contract_number} وجدولة {num_payments} دفعات بنجاح!")
                        st.balloons()
                        st.rerun()
    # عرض العقود
    st.markdown("---")
    st.subheader("📋 قائمة العقود")
    
    # فلتر العقود
    filter_status = st.radio(
        "عرض:",
        ["العقود النشطة فقط", "العقود الملغية فقط", "جميع العقود"],
        horizontal=True
    )
    
    # جلب العقود حسب الفلتر
    if filter_status == "العقود النشطة فقط":
        contracts = session.query(Contract).filter_by(status="نشط").all()
    elif filter_status == "العقود الملغية فقط":
        contracts = session.query(Contract).filter_by(status="ملغي").all()
    else:
        contracts = session.query(Contract).all()
    
    if contracts:
        contracts_data = []
        
        # تحسين: جلب جميع الوحدات مرة واحدة وتخزينها في قاموس للسرعة
        all_units_lookup = {u.id: u.unit_number for u in session.query(Unit).all()}
        
        for c in contracts:
            status_icon = "✅" if c.status == "نشط" else "🚫"
            
            # معالجة الوحدات من القاموس مباشرة بدلاً من استعلام قاعدة البيانات لكل وحدة
            unit_names = []
            if c.linked_units_ids:
                for uid in c.linked_units_ids.split(','):
                    u_num = all_units_lookup.get(int(uid))
                    if u_num:
                        unit_names.append(u_num)
            
            contracts_data.append({
                'رقم العقد': c.contract_number or str(c.id),
                'المستأجر': c.tenant.name,
                'النوع': c.contract_type,
                'القيمة السنوية': f"{c.rent_amount:,.0f} ريال",
                'الوحدات': ' | '.join(unit_names) if unit_names else '-',
                'تاريخ البداية': c.start_date,
                'تاريخ النهاية': c.end_date,
                'الحالة': f"{status_icon} {c.status}"
            })
        
        contracts_df = pd.DataFrame(contracts_data)
        st.dataframe(contracts_df, use_container_width=True, hide_index=True)
    else:
        st.info("لا توجد عقود مطابقة للفلتر المحدد")
def cancel_contract_page():
    """صفحة إلغاء العقود (للمدير فقط)"""
    st.header("🚫 إلغاء العقد")
    
    if st.session_state['user_role'] != 'Admin':
        st.error("⚠️ هذه الصفحة متاحة للمدير فقط")
        return
    
    st.warning("⚠️ تنبيه: إلغاء العقد لا يحذفه من النظام، بل يغير حالته إلى 'ملغي' للحفاظ على السجل التاريخي.")
    
    # جلب العقود النشطة فقط
    active_contracts = session.query(Contract).filter_by(status="نشط").all()
    
    if not active_contracts:
        st.info("لا توجد عقود نشطة لإلغائها")
        return
    
    # اختيار العقد
    contract_options = {}
    for c in active_contracts:
        label = f"عقد #{c.contract_number if c.contract_number else c.id} - {c.tenant.name} ({c.contract_type})"
        contract_options[label] = c.id
    
    selected_contract_label = st.selectbox(
        "اختر العقد المراد إلغاؤه",
        list(contract_options.keys()),
        key='cancel_contract_select'
    )
    
    contract_id = contract_options[selected_contract_label]
    contract = session.get(Contract, contract_id)
    
    if contract:
        # عرض تفاصيل العقد
        with st.expander("📋 تفاصيل العقد", expanded=True):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**رقم العقد:** {contract.contract_number or contract.id}")
                st.write(f"**المستأجر:** {contract.tenant.name}")
            with col2:
                st.write(f"**النوع:** {contract.contract_type}")
                st.write(f"**القيمة السنوية:** {contract.rent_amount:,.0f} ريال")
            with col3:
                st.write(f"**من:** {contract.start_date}")
                st.write(f"**إلى:** {contract.end_date}")
            
            # عرض الوحدات المرتبطة
            if contract.linked_units_ids:
                unit_ids = contract.linked_units_ids.split(',')
                unit_names = []
                for uid in unit_ids:
                    u = session.get(Unit, int(uid))
                    if u:
                        unit_names.append(f"{u.unit_number} ({u.asset.name})")
                st.write(f"**الوحدات:** {', '.join(unit_names)}")
        
        # التحقق من وجود دفعات
        payments = session.query(Payment).filter_by(contract_id=contract.id).all()
        paid_payments = [p for p in payments if p.status == "مدفوع"]
        pending_payments = [p for p in payments if p.status != "مدفوع"]
        
        if payments:
            st.markdown("---")
            st.subheader("📊 حالة الدفعات")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("إجمالي الدفعات", len(payments))
            with col2:
                st.metric("مدفوع", len(paid_payments))
            with col3:
                st.metric("متبقي", len(pending_payments))
            
            if pending_payments:
                st.warning(f"⚠️ يوجد {len(pending_payments)} دفعة غير مدفوعة. تأكد من مراجعة الحالة المالية قبل الإلغاء.")
        
        st.markdown("---")
        
        # نموذج الإلغاء
        st.markdown("### 📝 بيانات الإلغاء")
        
        cancellation_reason_type = st.selectbox(
            "سبب الإلغاء *",
            [
                "إدخال خاطئ",
                "عقد مكرر",
                "خطأ إداري",
                "طلب المستأجر",
                "إخلاء الوحدة",
                "أخرى"
            ],
            key='cancel_reason_select'
        )
        
        additional_notes = st.text_area(
            "تفاصيل إضافية",
            placeholder="أي تفاصيل إضافية عن سبب الإلغاء...",
            height=100,
            key='cancel_notes_area'
        )
        
        st.markdown("---")
        st.markdown("### ⚠️ تأكيد الإلغاء")
        
        st.error("**تحذير:** بعد الإلغاء:")
        st.markdown("""
        - ✅ سيتم تغيير حالة العقد إلى **ملغي**
        - ✅ ستبقى جميع البيانات في النظام (لن يتم الحذف)
        - ✅ سيتم تحرير الوحدات المرتبطة (تصبح فاضية)
        - ✅ لن يظهر العقد في التقارير المالية
        - ⚠️ **الدفعات غير المدفوعة ستبقى في السجل**
        """)
        
        st.markdown("---")
        
        # تأكيد الإلغاء
        confirm = st.checkbox(
            "✅ **أؤكد إلغاء هذا العقد ومعرفتي بالعواقب**",
            help="يجب تفعيل هذا الخيار لتمكين زر الإلغاء",
            key='cancel_confirm_checkbox'
        )
        
        if not confirm:
            st.warning("⚠️ يرجى تأكيد الإلغاء بالضغط على المربع أعلاه")
        
        # زر الإلغاء خارج الـ form
        if st.button(
            "🚫 إلغاء العقد نهائياً",
            use_container_width=True,
            type="primary",
            disabled=not confirm,
            key='cancel_submit_button'
        ):
            if not confirm:
                st.error("⚠️ يجب تأكيد الإلغاء")
            else:
                # تحديث حالة العقد
                full_reason = f"{cancellation_reason_type}"
                if additional_notes.strip():
                    full_reason += f" - {additional_notes.strip()}"
                
                contract.status = "ملغي"
                contract.cancellation_reason = full_reason
                contract.cancelled_by = st.session_state['username']
                contract.cancellation_date = date.today()
                
                # تحرير الوحدات
                if contract.linked_units_ids:
                    unit_ids = contract.linked_units_ids.split(',')
                    for uid in unit_ids:
                        unit = session.get(Unit, int(uid))
                        if unit:
                            unit.status = "فاضي"
                
                # حذف الدفعات غير المدفوعة (اختياري)
                pending_payments_to_delete = session.query(Payment).filter(
                    Payment.contract_id == contract.id,
                    Payment.status != "مدفوع"
                ).all()
                
                deleted_count = 0
                if pending_payments_to_delete:
                    for payment in pending_payments_to_delete:
                        session.delete(payment)
                    deleted_count = len(pending_payments_to_delete)
                
                session.commit()
                
                st.success(f"✅ تم إلغاء العقد #{contract.contract_number or contract.id} بنجاح!")
                st.info(f"📝 السبب: {full_reason}")
                st.info(f"👤 تم الإلغاء بواسطة: {st.session_state['username']}")
                st.info(f"📅 تاريخ الإلغاء: {date.today()}")
                
                if deleted_count > 0:
                    st.info(f"🗑️ تم حذف {deleted_count} دفعة غير مدفوعة")
                
                st.balloons()
                st.rerun()
def manage_payments():
    st.header("💰 إدارة الدفعات")

    if st.session_state.get('user_role') == 'Employee':
        st.info("ℹ️ كموظف، يمكنك تسجيل الدفعات فقط")

    # ----------------------------------
    # جلب العقود النشطة مع المستأجر (تحسين الأداء)
    # ----------------------------------
    from sqlalchemy.orm import joinedload

    contracts = session.query(Contract)\
        .options(joinedload(Contract.tenant))\
        .filter(Contract.status == "نشط")\
        .all()

    if not contracts:
        st.warning("لا توجد عقود نشطة")
        return

    contract_map = {
        f"عقد #{c.contract_number or c.id} - {c.tenant.name}": c
        for c in contracts
    }

    selected_label = st.selectbox("اختر العقد", contract_map.keys())
    contract = contract_map[selected_label]

    # ----------------------------------
    # معلومات العقد
    # ----------------------------------
    with st.expander("📋 معلومات العقد"):
        c1, c2, c3 = st.columns(3)
        c1.write(f"**المستأجر:** {contract.tenant.name}")
        c1.write(f"**نوع العقد:** {contract.contract_type}")

        c2.write(f"**الإيجار السنوي:** {contract.rent_amount:,.0f} ريال")
        c2.write(f"**الدورية:** {contract.payment_freq}")

        c3.write(f"**بداية العقد:** {contract.start_date}")
        c3.write(f"**نهاية العقد:** {contract.end_date}")

    # ----------------------------------
    # جلب الدفعات
    # ----------------------------------
    payments = session.query(Payment)\
        .filter(Payment.contract_id == contract.id)\
        .order_by(Payment.due_date)\
        .all()

    # ----------------------------------
    # توليد الدفعات (لو غير موجودة)
    # ----------------------------------
    if not payments:
        st.info("لم يتم توليد دفعات لهذا العقد")

        if st.button("🔄 توليد الدفعات تلقائياً", type="primary", use_container_width=True):

            if not contract.rent_amount or contract.rent_amount <= 0:
                st.error("❌ مبلغ العقد غير صحيح")
                return

            from dateutil.relativedelta import relativedelta

            freq_map = {"شهري": 1, "ربع سنوي": 3, "نصف سنوي": 6, "سنوي": 12}
            step = freq_map.get(contract.payment_freq, 12)

            # حساب مدة العقد بالأشهر
            total_months = (contract.end_date.year - contract.start_date.year) * 12 + \
                           (contract.end_date.month - contract.start_date.month)

            num_payments = total_months // step
            amount_per_payment = float(contract.rent_amount) / num_payments

            vat_rate = float(contract.vat_rate or 0)
            if vat_rate >= 1:
                vat_rate /= 100

            payments_to_add = []
            due_date = contract.start_date

            for i in range(1, num_payments + 1):
                vat_value = round(amount_per_payment * vat_rate, 2)
                total = round(amount_per_payment + vat_value, 2)

                payments_to_add.append(Payment(
                    contract_id=contract.id,
                    payment_number=i,
                    due_date=due_date,
                    amount=round(amount_per_payment, 2),
                    vat=vat_value,
                    total=total,
                    paid_amount=0.0,
                    remaining_amount=total,
                    status="مستحق"
                ))

                due_date += relativedelta(months=step)

            session.add_all(payments_to_add)
            session.commit()

            st.success(f"✅ تم توليد {len(payments_to_add)} دفعة بنجاح")
            st.rerun()

    # ----------------------------------
    # ملخص مالي
    # ----------------------------------
    if payments:
        st.markdown("---")

        total_contract = sum(p.total or 0 for p in payments)
        total_paid = sum(p.paid_amount or 0 for p in payments)
        total_remaining = sum(p.remaining_amount or 0 for p in payments)

        c1, c2, c3 = st.columns(3)
        c1.metric("إجمالي العقد", f"{total_contract:,.0f} ر.س")
        c2.metric("المحصل", f"{total_paid:,.2f} ر.س")
        c3.metric("المتبقي", f"{total_remaining:,.2f} ر.س")

        st.progress(min(1.0, total_paid / total_contract) if total_contract else 0)

        # ----------------------------------
        # جدول الدفعات
        # ----------------------------------
        df = pd.DataFrame([{
            "رقم": p.payment_number,
            "تاريخ الاستحقاق": p.due_date,
            "الإجمالي": p.total,
            "المدفوع": p.paid_amount,
            "المتبقي": p.remaining_amount,
            "الحالة": p.status,
            "طريقة السداد": p.payment_method or "-",
        } for p in payments])

        st.dataframe(df, use_container_width=True, hide_index=True)

        # ----------------------------------
        # تسجيل تحصيل
        # ----------------------------------
        unpaid = [p for p in payments if p.remaining_amount and p.remaining_amount > 0]

        st.markdown("### 💳 تسجيل تحصيل جديد")

        if unpaid:
            with st.form("payment_form"):
                options = {
                    f"دفعة {p.payment_number} (متبقي {p.remaining_amount:,.2f})": p.id
                    for p in unpaid
                }

                label = st.selectbox("اختر الدفعة", options.keys())
                payment = session.get(Payment, options[label])

                col1, col2 = st.columns(2)
                amount = col1.number_input(
                    "المبلغ المحصل",
                    min_value=0.01,
                    max_value=float(payment.remaining_amount),
                    value=float(payment.remaining_amount)
                )

                method = col2.selectbox(
                    "طريقة السداد",
                    ["تحويل بنكي", "نقدي", "شيك", "منصة إيجار"]
                )

                if st.form_submit_button("✅ تسجيل السداد", use_container_width=True):
                    payment.paid_amount = (payment.paid_amount or 0) + amount
                    payment.remaining_amount = max(
                        0, (payment.total or 0) - payment.paid_amount
                    )
                    payment.payment_method = method
                    payment.paid_date = date.today()
                    payment.status = "مدفوع" if payment.remaining_amount == 0 else "مدفوع جزئياً"

                    session.commit()
                    st.success("✅ تم تسجيل السداد")
                    st.rerun()
        else:
            st.success("🎉 تم تحصيل جميع دفعات العقد")

def reports_page():
    st.header("📑 التقارير")

    report_type = st.radio(
        "اختر نوع التقرير",
        ["تقرير مالي شامل", "المتأخرات", "تقرير المستأجر التفصيلي"],
        horizontal=True
    )

   # ======================================================
    # 📊 التقرير المالي الشامل (النسخة المصلحة لهيكلة linked_units_ids)
    # ======================================================
    if report_type == "تقرير مالي شامل":
        assets = session.query(Asset).all()
        asset_names = ["الكل"] + [a.name for a in assets]

        col1, col2, col3 = st.columns(3)
        with col1:
            selected_asset = st.selectbox("الأصل", asset_names)
        with col2:
            selected_status = st.selectbox(
                "حالة الدفعة",
                ["الكل", "مدفوع", "مدفوع جزئياً", "مستحق"]
            )
        with col3:
            limit = st.number_input("عدد الصفوف", 100, 5000, 1000)

        # 1. استعلام الدفعات مع العقود والمستأجرين فقط (بدون الأصول حالياً)
        query = session.query(
            Payment.id.label("رقم"),
            Contract.contract_number.label("العقد"),
            Tenant.name.label("المستأجر"),
            Contract.linked_units_ids, # سنجلب هذا الحقل لنعرف الوحدة
            Payment.due_date.label("الاستحقاق"),
            Payment.total.label("الإجمالي"),
            Payment.paid_amount.label("المدفوع"),
            Payment.remaining_amount.label("المتبقي"),
            Payment.status.label("الحالة"),
            Payment.payment_method.label("طريقة السداد")
        ).select_from(Payment)\
         .join(Contract, Payment.contract_id == Contract.id)\
         .join(Tenant, Contract.tenant_id == Tenant.id)\
         .filter(Contract.status == "نشط")

        if selected_status != "الكل":
            query = query.filter(Payment.status == selected_status)

        query = query.limit(limit)
        df = pd.read_sql(query.statement, session.bind)

        if df.empty:
            st.info("لا توجد بيانات")
            return

        # 2. ربط "الأصل" برمجياً (لأن الحقل linked_units_ids نصي)
        # سنقوم بإنشاء قاموس للوحدات والأصول لتسريع العملية
        units = session.query(Unit).all()
        unit_to_asset = {str(u.id): (session.query(Asset).filter_by(id=u.asset_id).first().name if u.asset_id else "بدون أصل") for u in units}
        
        def get_asset_name(unit_ids_str):
            if not unit_ids_str: return "غير محدد"
            # نأخذ أول معرف وحدة موجود في النص
            first_unit_id = unit_ids_str.split(',')[0].strip()
            return unit_to_asset.get(first_unit_id, "غير معروف")

        df['الأصل'] = df['linked_units_ids'].apply(get_asset_name)

        # 3. التصفية حسب الأصل بعد المعالجة
        if selected_asset != "الكل":
            df = df[df['الأصل'] == selected_asset]

        # 4. معالجة القيم الفارغة للحسابات
        for col in ['الإجمالي', 'المدفوع', 'المتبقي']:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # ================= عرض النتائج =================
        if df.empty:
            st.warning("لا توجد نتائج لهذا الأصل")
            return

        c1, c2, c3 = st.columns(3)
        c1.metric("عدد الدفعات", len(df))
        c2.metric("إجمالي المبلغ", f"{df['الإجمالي'].sum():,.0f} ر.س")
        c3.metric("إجمالي المتبقي", f"{df['المتبقي'].sum():,.0f} ر.س")

        # إخفاء العمود التقني قبل العرض
        display_df = df.drop(columns=['linked_units_ids'])
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        st.download_button(
            "⬇️ تحميل CSV",
            display_df.to_csv(index=False).encode("utf-8-sig"),
            "financial_report.csv",
            "text/csv"
        )

    # ======================================================
    # ⏰ تقرير المتأخرات
    # ======================================================
    elif report_type == "المتأخرات":
        query = session.query(
            Tenant.name.label("المستأجر"),
            Tenant.phone.label("الهاتف"),
            Payment.due_date.label("تاريخ الاستحقاق"),
            Payment.remaining_amount.label("المبلغ المتأخر"),
            Payment.payment_method.label("طريقة السداد")
        ).select_from(Payment)\
         .join(Contract, Payment.contract_id == Contract.id)\
         .join(Tenant, Contract.tenant_id == Tenant.id)\
         .filter(
             Payment.remaining_amount > 0,
             Payment.due_date < date.today(),
             Contract.status == "نشط"
         )

        df = pd.read_sql(query.statement, session.bind)

        if df.empty:
            st.success("✅ لا توجد متأخرات")
            return

        st.error(f"💰 إجمالي المتأخرات: {df['المبلغ المتأخر'].sum():,.2f} ر.س")
        st.dataframe(df, use_container_width=True)

        st.download_button(
            "⬇️ تحميل تقرير المتأخرات",
            df.to_csv(index=False).encode("utf-8-sig"),
            "overdue_report.csv",
            "text/csv"
        )

    # ======================================================
    # 🧾 تقرير المستأجر التفصيلي
    # ======================================================
    else:
        tenants = session.query(Tenant).all()
        if not tenants:
            st.warning("لا يوجد مستأجرين")
            return

        tenant_name = st.selectbox("اختر المستأجر", [t.name for t in tenants])
        tenant = session.query(Tenant).filter(Tenant.name == tenant_name).first()

        contracts = session.query(Contract)\
            .filter(Contract.tenant_id == tenant.id, Contract.status == "نشط")\
            .all()

        rows = []
        for contract in contracts:
            payments = session.query(Payment).filter(Payment.contract_id == contract.id).all()
            for pay in payments:
                rows.append({
                    "العقد": contract.contract_number or contract.id,
                    "الاستحقاق": pay.due_date,
                    "الإجمالي": pay.total,
                    "المدفوع": pay.paid_amount,
                    "المتبقي": pay.remaining_amount,
                    "الحالة": pay.status,
                    "طريقة السداد": pay.payment_method
                })

        df = pd.DataFrame(rows)
        if df.empty:
            st.info("لا توجد بيانات لهذا المستأجر")
            return

        st.dataframe(df, use_container_width=True)
        st.download_button(
            "⬇️ تحميل تقرير المستأجر",
            df.to_csv(index=False).encode("utf-8-sig"),
            f"tenant_{tenant.name}.csv",
            "text/csv"
        )


def settings_page():
    st.header("⚙️ إعدادات المستخدم")
    
    if st.session_state['user_role'] == 'Admin':
        user_to_edit_name = st.selectbox("اختر المستخدم للتعديل", [u.username for u in session.query(User).all()])
        user_to_edit = session.query(User).filter_by(username=user_to_edit_name).first()

        if user_to_edit:
            with st.form("edit_user_settings"):
                st.subheader(f"تعديل بيانات {user_to_edit_name}")
                
                # تغيير اسم المستخدم
                new_username = st.text_input("اسم المستخدم الجديد", value=user_to_edit.username)
                
                # تغيير كلمة المرور
                new_password = st.text_input("كلمة المرور الجديدة (اتركها فارغة لعدم التغيير)", type="password")
                confirm_password = st.text_input("تأكيد كلمة المرور الجديدة", type="password")
                
                submitted = st.form_submit_button("حفظ التغييرات")
                
                if submitted:
                    errors = []
                    
                    # 1. تحديث اسم المستخدم
                    if new_username != user_to_edit.username:
                        if session.query(User).filter(User.username == new_username, User.id != user_to_edit.id).first():
                            errors.append("اسم المستخدم هذا محجوز مسبقاً.")
                        else:
                            user_to_edit.username = new_username
                            # تحديث الحالة الجلسة إذا كان هو المستخدم الحالي
                            if st.session_state['username'] == user_to_edit_name:
                                st.session_state['username'] = new_username 

                    # 2. تحديث كلمة المرور
                    if new_password:
                        if new_password != confirm_password:
                            errors.append("كلمة المرور وتأكيدها غير متطابقين.")
                        else:
                            user_to_edit.password_hash = hash_password(new_password)
                    
                    if errors:
                        for err in errors:
                            st.error(err)
                    else:
                        session.commit()
                        st.success("تم تحديث الإعدادات بنجاح. يرجى تسجيل الخروج والدخول مرة أخرى للتحقق من التغييرات.")
                        st.rerun()
    else:
        st.warning("هذه الصفحة متاحة للمدير فقط.")




# =================================================================
# تعديل دالة manage_tenants() لإعطاء الموظف صلاحيات الإضافة والتعديل
# =================================================================


def manage_tenants():
    st.header("👥 إدارة المستأجرين")
    
    # عرض ملخص سريع
    st.subheader("📊 ملخص المستأجرين")
    total_tenants = session.query(Tenant).count()
    active_contracts = session.query(Contract).filter(
        Contract.end_date >= date.today(),
        Contract.status == "نشط"
    ).count()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("إجمالي المستأجرين", total_tenants)
    with col2:
        st.metric("العقود النشطة", active_contracts)
    with col3:
        tenants_with_contracts = session.query(Contract.tenant_id).distinct().count()
        st.metric("مستأجرين بدون عقود", total_tenants - tenants_with_contracts)
    
    st.markdown("---")
    
    # =========================================================================
    # قسم الإدارة - متاح للمدير والموظف (مع اختلاف الصلاحيات)
    # =========================================================================
    
    # ✅ التعديل الأساسي: السماح للموظف أيضاً بالوصول لهذا القسم
    if st.session_state['user_role'] in ['Admin', 'Employee']:  # ← التغيير هنا
        
        # رسالة توضيحية للموظف
        if st.session_state['user_role'] == 'Employee':
            st.info("ℹ️ **صلاحياتك كموظف:** يمكنك إضافة وتعديل المستأجرين. الحذف متاح للمدير فقط.")
        
        st.subheader("⚙️ إدارة بيانات المستأجرين")
        
        # ✅ التعديل: تغيير عدد الـ Tabs حسب الصلاحية
        if st.session_state['user_role'] == 'Admin':
            # المدير: تعديل/عرض + إضافة
            tab1, tab2 = st.tabs(["✏️ تعديل/عرض/حذف مستأجر", "➕ إضافة مستأجر جديد"])
        else:
            # الموظف: تعديل + إضافة فقط (بدون حذف)
            tab1, tab2 = st.tabs(["✏️ تعديل مستأجر", "➕ إضافة مستأجر جديد"])
        
        # ===================================================================
        # Tab 1: تعديل/عرض/حذف مستأجر موجود
        # ===================================================================
        with tab1:
            if st.session_state['user_role'] == 'Admin':
                st.markdown("#### تعديل أو عرض أو حذف بيانات مستأجر")
            else:
                st.markdown("#### تعديل بيانات مستأجر")
            
            tenants_list = session.query(Tenant).all()
            
            if tenants_list:
                tenant_names = [f"{t.name} - {t.type or 'غير محدد'}" for t in tenants_list]
                
                selected_tenant_label = st.selectbox(
                    "🔍 اختر المستأجر",
                    tenant_names,
                    key='select_tenant_edit'
                )
                
                # العثور على المستأجر المختار
                selected_index = tenant_names.index(selected_tenant_label)
                selected_tenant = tenants_list[selected_index]
                
                # عرض بيانات المستأجر الحالية في expander
                with st.expander("📄 البيانات الحالية", expanded=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**الاسم:** {selected_tenant.name}")
                        st.write(f"**النوع:** {selected_tenant.type or '-'}")
                        st.write(f"**الهاتف:** {selected_tenant.phone or '-'}")
                        st.write(f"**البريد الإلكتروني:** {selected_tenant.email or '-'}")
                    with col2:
                        st.write(f"**رقم الهوية:** {selected_tenant.national_id or '-'}")
                        st.write(f"**العنوان:** {selected_tenant.address or '-'}")
                        st.write(f"**تاريخ الإضافة:** {selected_tenant.created_date or '-'}")
                    
                    if selected_tenant.notes:
                        st.write(f"**ملاحظات:** {selected_tenant.notes}")
                
                # عرض العقود المرتبطة
                tenant_contracts = session.query(Contract).filter_by(tenant_id=selected_tenant.id).all()
                if tenant_contracts:
                    st.markdown("##### 📑 العقود المرتبطة")
                    contracts_data = []
                    for c in tenant_contracts:
                        unit_names = []
                        if c.linked_units_ids:
                            for uid in c.linked_units_ids.split(','):
                                u = session.get(Unit, int(uid))
                                if u:
                                    unit_names.append(f"{u.unit_number} ({u.asset.name})")
                        
                        contracts_data.append({
                            'رقم العقد': c.contract_number or c.id,
                            'النوع': c.contract_type,
                            'القيمة السنوية': f"{c.rent_amount:,.0f}",
                            'الوحدات': ', '.join(unit_names) if unit_names else '-',
                            'تاريخ البداية': c.start_date,
                            'تاريخ النهاية': c.end_date,
                            'الحالة': c.status
                        })
                    
                    contracts_df = pd.DataFrame(contracts_data)
                    st.dataframe(contracts_df, use_container_width=True, hide_index=True)
                else:
                    st.info("لا توجد عقود مرتبطة بهذا المستأجر")
                
                st.markdown("---")
                
                # ✅ التعديل: Sub-tabs مختلفة حسب الصلاحية
                if st.session_state['user_role'] == 'Admin':
                    # المدير: تعديل + حذف
                    edit_tenant_tab, delete_tenant_tab = st.tabs(["✏️ تعديل البيانات", "🗑️ حذف المستأجر"])
                else:
                    # الموظف: تعديل فقط (بدون tab الحذف)
                    edit_tenant_tab = st.container()
                
                # ===== Tab/Container: تعديل البيانات (متاح للجميع) =====
                with edit_tenant_tab:
                    with st.form("edit_tenant_form"):
                        st.markdown("##### ✏️ تعديل البيانات")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            new_name = st.text_input(
                                "الاسم *",
                                value=selected_tenant.name,
                                placeholder="اسم المستأجر"
                            )
                            new_type = st.selectbox(
                                "النوع",
                                ["شركة", "مستشفى", "صيدلية", "مستثمر", "فرد", "أخرى"],
                                index=["شركة", "مستشفى", "صيدلية", "مستثمر", "فرد", "أخرى"].index(selected_tenant.type) if selected_tenant.type in ["شركة", "مستشفى", "صيدلية", "مستثمر", "فرد", "أخرى"] else 0
                            )
                            new_phone = st.text_input(
                                "رقم الهاتف",
                                value=selected_tenant.phone if selected_tenant.phone else "",
                                placeholder="+966..."
                            )
                            new_email = st.text_input(
                                "البريد الإلكتروني",
                                value=selected_tenant.email if selected_tenant.email else "",
                                placeholder="example@email.com"
                            )
                        
                        with col2:
                            new_national_id = st.text_input(
                                "رقم الهوية/السجل التجاري",
                                value=selected_tenant.national_id if selected_tenant.national_id else "",
                                placeholder="1234567890"
                            )
                            new_address = st.text_area(
                                "العنوان",
                                value=selected_tenant.address if selected_tenant.address else "",
                                placeholder="العنوان التفصيلي",
                                height=100
                            )
                        
                        new_notes = st.text_area(
                            "ملاحظات",
                            value=selected_tenant.notes if selected_tenant.notes else "",
                            placeholder="أي ملاحظات إضافية",
                            height=80
                        )
                        
                        st.markdown("---")
                        
                        submit_edit = st.form_submit_button(
                            "💾 حفظ التعديلات",
                            use_container_width=True,
                            type="primary"
                        )
                        
                        if submit_edit:
                            if not new_name.strip():
                                st.error("⚠️ الاسم مطلوب")
                            else:
                                selected_tenant.name = new_name.strip()
                                selected_tenant.type = new_type
                                selected_tenant.phone = new_phone.strip() if new_phone else None
                                selected_tenant.email = new_email.strip() if new_email else None
                                selected_tenant.national_id = new_national_id.strip() if new_national_id else None
                                selected_tenant.address = new_address.strip() if new_address else None
                                selected_tenant.notes = new_notes.strip() if new_notes else None
                                
                                session.commit()
                                st.success(f"✅ تم تحديث بيانات **{new_name}** بنجاح!")
                                st.rerun()
                
                # ===== Tab: حذف المستأجر (للمدير فقط) =====
                if st.session_state['user_role'] == 'Admin':
                    with delete_tenant_tab:
                        st.markdown("### 🗑️ حذف المستأجر")
                        
                        # جلب العقود المرتبطة
                        active_contracts = [c for c in tenant_contracts if c.status == "نشط"]
                        cancelled_contracts = [c for c in tenant_contracts if c.status == "ملغي"]
                        
                        # عرض الإحصائيات
                        with st.expander("📊 إحصائيات المستأجر", expanded=True):
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("إجمالي العقود", len(tenant_contracts))
                            with col2:
                                st.metric("عقود نشطة", len(active_contracts))
                            with col3:
                                st.metric("عقود ملغية", len(cancelled_contracts))
                        
                        # التحقق من إمكانية الحذف
                        if len(active_contracts) > 0:
                            st.error("🚫 **لا يمكن حذف هذا المستأجر!**")
                            st.error(f"السبب: المستأجر لديه **{len(active_contracts)}** عقد نشط")
                            
                            with st.expander("📋 العقود النشطة"):
                                for contract in active_contracts:
                                    unit_names = []
                                    if contract.linked_units_ids:
                                        for uid in contract.linked_units_ids.split(','):
                                            u = session.get(Unit, int(uid))
                                            if u:
                                                unit_names.append(f"{u.unit_number} ({u.asset.name})")
                                    
                                    st.write(f"- عقد #{contract.contract_number or contract.id}")
                                    st.write(f"  - النوع: {contract.contract_type}")
                                    st.write(f"  - القيمة: {contract.rent_amount:,.0f} ريال")
                                    st.write(f"  - الوحدات: {', '.join(unit_names) if unit_names else '-'}")
                                    st.markdown("---")
                            
                            st.info("💡 **للحذف:** يجب إلغاء جميع العقود النشطة من صفحة 'إلغاء عقد'")
                        
                        else:
                            # يمكن الحذف
                            if len(cancelled_contracts) > 0:
                                st.warning(f"⚠️ تنبيه: المستأجر لديه {len(cancelled_contracts)} عقد ملغي")
                                
                                delete_mode = st.radio(
                                    "اختر طريقة الحذف:",
                                    [
                                        "حذف المستأجر فقط (العقود الملغية ستبقى)",
                                        "حذف المستأجر وجميع العقود الملغية معاً"
                                    ],
                                    key='delete_mode_tenant'
                                )
                                
                                if delete_mode == "حذف المستأجر وجميع العقود الملغية معاً":
                                    st.error("⚠️ **تحذير:** سيتم حذف المستأجر وجميع العقود الملغية المرتبطة به!")
                                    
                                    with st.expander("📋 العقود التي سيتم حذفها"):
                                        for contract in cancelled_contracts:
                                            payments = session.query(Payment).filter_by(contract_id=contract.id).all()
                                            st.write(f"- عقد #{contract.contract_number or contract.id}")
                                            st.write(f"  - عدد الدفعات: {len(payments)}")
                                            st.markdown("---")
                                else:
                                    st.info("ℹ️ العقود الملغية ستبقى في النظام للسجل التاريخي")
                            else:
                                st.success("✅ هذا المستأجر ليس لديه عقود ويمكن حذفه بأمان")
                            
                            st.markdown("---")
                            st.markdown("### ⚠️ تأكيد الحذف")
                            
                            st.markdown(f"""
                            <div style="background-color: #3d1e1e; padding: 20px; border-radius: 10px; border-left: 5px solid #ff4444;">
                                <h4 style="color: #ff6b6b; margin-top: 0;">⚠️ تحذير نهائي</h4>
                                <p>أنت على وشك حذف المستأجر: <strong>{selected_tenant.name}</strong></p>
                                <p>هذا الإجراء <strong>لا يمكن التراجع عنه!</strong></p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            st.markdown("<br>", unsafe_allow_html=True)
                            
                            confirm_text = st.text_input(
                                f"للتأكيد، اكتب اسم المستأجر: **{selected_tenant.name}**",
                                placeholder=selected_tenant.name,
                                key='confirm_delete_tenant'
                            )
                            
                            if confirm_text == selected_tenant.name:
                                st.success("✅ تم التأكيد - يمكنك الآن الضغط على زر الحذف")
                                
                                if st.button(
                                    "🗑️ حذف المستأجر نهائياً",
                                    type="primary",
                                    use_container_width=True,
                                    key='final_delete_tenant_btn'
                                ):
                                    try:
                                        deleted_contracts_count = 0
                                        deleted_payments_count = 0
                                        
                                        if len(cancelled_contracts) > 0 and delete_mode == "حذف المستأجر وجميع العقود الملغية معاً":
                                            for contract in cancelled_contracts:
                                                payments = session.query(Payment).filter_by(contract_id=contract.id).all()
                                                for payment in payments:
                                                    session.delete(payment)
                                                    deleted_payments_count += 1
                                                
                                                session.delete(contract)
                                                deleted_contracts_count += 1
                                        
                                        tenant_name = selected_tenant.name
                                        session.delete(selected_tenant)
                                        session.commit()
                                        
                                        st.success(f"✅ تم حذف المستأجر **{tenant_name}** بنجاح!")
                                        
                                        if deleted_contracts_count > 0:
                                            st.info(f"🗑️ تم حذف {deleted_contracts_count} عقد ملغي")
                                        
                                        if deleted_payments_count > 0:
                                            st.info(f"🗑️ تم حذف {deleted_payments_count} دفعة")
                                        
                                        st.balloons()
                                        st.rerun()
                                        
                                    except Exception as e:
                                        session.rollback()
                                        st.error(f"❌ حدث خطأ أثناء الحذف: {str(e)}")
                            else:
                                st.warning("⚠️ يرجى كتابة اسم المستأجر بشكل صحيح للتأكيد")
            else:
                st.info("لا يوجد مستأجرين مسجلين حالياً")
        
        # ===================================================================
        # Tab 2: إضافة مستأجر جديد (متاح للجميع)
        # ===================================================================
        with tab2:
            st.markdown("#### إضافة مستأجر جديد")
            
            with st.form("add_tenant_form", clear_on_submit=True):
                st.markdown("##### 📝 بيانات المستأجر الجديد")
                
                col1, col2 = st.columns(2)
                with col1:
                    tenant_name = st.text_input(
                        "الاسم *",
                        placeholder="اسم المستأجر"
                    )
                    tenant_type = st.selectbox(
                        "النوع",
                        ["شركة", "مستشفى", "صيدلية", "مستثمر", "فرد", "أخرى"]
                    )
                    tenant_phone = st.text_input(
                        "رقم الهاتف",
                        placeholder="+966..."
                    )
                    tenant_email = st.text_input(
                        "البريد الإلكتروني",
                        placeholder="example@email.com"
                    )
                
                with col2:
                    tenant_national_id = st.text_input(
                        "رقم الهوية/السجل التجاري",
                        placeholder="1234567890"
                    )
                    tenant_address = st.text_area(
                        "العنوان",
                        placeholder="العنوان التفصيلي",
                        height=100
                    )
                
                tenant_notes = st.text_area(
                    "ملاحظات",
                    placeholder="أي ملاحظات إضافية",
                    height=80
                )
                
                st.markdown("---")
                
                submit_add = st.form_submit_button(
                    "✅ إضافة المستأجر",
                    use_container_width=True,
                    type="primary"
                )
                
                if submit_add:
                    if not tenant_name.strip():
                        st.error("⚠️ الاسم مطلوب")
                    else:
                        existing = session.query(Tenant).filter_by(name=tenant_name.strip()).first()
                        
                        if existing:
                            st.error(f"⚠️ المستأجر '{tenant_name}' موجود بالفعل")
                        else:
                            new_tenant = Tenant(
                                name=tenant_name.strip(),
                                type=tenant_type,
                                phone=tenant_phone.strip() if tenant_phone else None,
                                email=tenant_email.strip() if tenant_email else None,
                                national_id=tenant_national_id.strip() if tenant_national_id else None,
                                address=tenant_address.strip() if tenant_address else None,
                                notes=tenant_notes.strip() if tenant_notes else None,
                                created_date=date.today()
                            )
                            session.add(new_tenant)
                            session.commit()
                            st.success(f"✅ تم إضافة المستأجر **{tenant_name}** بنجاح!")
                            st.balloons()
                            st.rerun()
    
    # =========================================================================
    # قسم عرض قائمة المستأجرين (للجميع)
    # =========================================================================
    st.markdown("---")
    st.subheader("📋 قائمة المستأجرين")
    
    all_tenants = session.query(Tenant).all()
    
    if all_tenants:
        tenants_display = []
        for t in all_tenants:
            contracts_count = session.query(Contract).filter_by(tenant_id=t.id, status="نشط").count()
            
            active_contracts = session.query(Contract).filter(
                Contract.tenant_id == t.id,
                Contract.end_date >= date.today(),
                Contract.status == "نشط"
            ).count()
            
            status = "🟢 نشط" if active_contracts > 0 else "⚪ غير نشط"
            
            tenants_display.append({
                'الاسم': t.name,
                'النوع': t.type or '-',
                'الهاتف': t.phone or '-',
                'البريد الإلكتروني': t.email or '-',
                'عدد العقود': contracts_count,
                'الحالة': status
            })
        
        tenants_df = pd.DataFrame(tenants_display)
        
        search_term = st.text_input("🔍 البحث عن مستأجر", placeholder="ابحث بالاسم أو النوع...")
        
        if search_term:
            tenants_df = tenants_df[
                tenants_df['الاسم'].str.contains(search_term, case=False, na=False) |
                tenants_df['النوع'].str.contains(search_term, case=False, na=False)
            ]
        
        st.dataframe(
            tenants_df,
            use_container_width=True,
            hide_index=True
        )
        
        st.markdown("#### 📈 إحصائيات سريعة")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            companies = sum(1 for t in all_tenants if t.type == 'شركة')
            st.metric("شركات", companies)
        with col2:
            hospitals = sum(1 for t in all_tenants if t.type == 'مستشفى')
            st.metric("مستشفيات", hospitals)
        with col3:
            pharmacies = sum(1 for t in all_tenants if t.type == 'صيدلية')
            st.metric("صيدليات", pharmacies)
        with col4:
            individuals = sum(1 for t in all_tenants if t.type == 'فرد')
            st.metric("أفراد", individuals)
    else:
        st.info("لا يوجد مستأجرين مسجلين بعد")


# يفترض الكود وجود session و models (Asset, Unit, Contract) معرفة مسبقاً في التطبيق

def manage_assets_only():
    """صفحة مخصصة لإدارة الأصول فقط"""
    st.header("🏢 إدارة الأصول")
    
    # جلب جميع الأصول
    all_assets = session.query(Asset).all()
    total_assets = len(all_assets)
    
    # عرض ملخص سريع
    st.subheader("📊 ملخص الأصول")
    
    # تصنيف الأصول حسب النوع
    buildings = sum(1 for a in all_assets if a.type == "عمارة")
    warehouses = sum(1 for a in all_assets if a.type == "مستودع")
    lands = sum(1 for a in all_assets if a.type in ["أرض", "محطة وقود"])
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("إجمالي الأصول", total_assets)
    with col2:
        st.metric("عمارات", buildings)
    with col3:
        st.metric("مستودعات", warehouses)
    with col4:
        st.metric("أراضي", lands)
    
    st.markdown("---")
    
    # =========================================================================
    # للمدير: جميع الصلاحيات
    # =========================================================================
    if st.session_state.get('user_role') == 'Admin':
        st.subheader("⚙️ إدارة الأصول (مدير)")
        
        # Tabs لتقسيم الوظائف
        tab1, tab2, tab3 = st.tabs(["📋 عرض الأصول", "➕ إضافة أصل جديد", "✏️ تعديل أصل موجود"])
        
        # ===================================================================
        # Tab 1: عرض الأصول
        # ===================================================================
        with tab1:
            st.markdown("#### 📋 قائمة الأصول المسجلة")
            
            if all_assets:
                assets_display = []
                for asset in all_assets:
                    # عد الوحدات في كل أصل
                    units_count = session.query(Unit).filter_by(asset_id=asset.id).count()
                    rented_units = session.query(Unit).filter_by(asset_id=asset.id, status="مؤجر").count()
                    
                    assets_display.append({
                        'ID': asset.id,
                        'اسم الأصل': asset.name,
                        'النوع': asset.type,
                        'الموقع': asset.location or '-',
                        'عدد الوحدات': units_count,
                        'الوحدات المؤجرة': rented_units,
                        'الوصف': asset.description or '-'
                    })
                
                assets_df = pd.DataFrame(assets_display)
                st.dataframe(assets_df, use_container_width=True, hide_index=True)
            else:
                st.info("لا توجد أصول مسجلة حالياً")
        
        # ===================================================================
        # Tab 2: إضافة أصل جديد
        # ===================================================================
        with tab2:
            st.markdown("#### ➕ إضافة أصل جديد")
            
            with st.form("add_asset_form_admin", clear_on_submit=True):
                st.markdown("##### 📝 بيانات الأصل الجديد")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    asset_name = st.text_input(
                        "اسم الأصل *",
                        placeholder="مثال: عمارة 5، مستودع 3",
                        help="اسم واضح ومميز للأصل"
                    )
                    
                    asset_type = st.selectbox(
                        "نوع الأصل *",
                        ["عمارة", "مستودع", "أرض", "محطة وقود", "أخرى"],
                        help="اختر نوع الأصل"
                    )
                
                with col2:
                    asset_location = st.text_input(
                        "الموقع",
                        placeholder="مثال: حي الزهراء، شارع الملك",
                        help="الموقع الجغرافي للأصل (اختياري)"
                    )
                
                asset_description = st.text_area(
                    "الوصف/ملاحظات",
                    placeholder="معلومات إضافية عن الأصل...",
                    height=100,
                    help="أي تفاصيل إضافية عن الأصل"
                )
                
                st.markdown("---")
                
                submit_add = st.form_submit_button(
                    "✅ إضافة الأصل",
                    use_container_width=True,
                    type="primary"
                )
                
                if submit_add:
                    if not asset_name.strip():
                        st.error("⚠️ اسم الأصل مطلوب")
                    else:
                        # التحقق من عدم التكرار
                        existing_asset = session.query(Asset).filter_by(name=asset_name.strip()).first()
                        
                        if existing_asset:
                            st.error(f"⚠️ الأصل '{asset_name}' موجود بالفعل")
                        else:
                            new_asset = Asset(
                                name=asset_name.strip(),
                                type=asset_type,
                                location=asset_location.strip() if asset_location else None,
                                description=asset_description.strip() if asset_description else None
                            )
                            session.add(new_asset)
                            session.commit()
                            st.success(f"✅ تم إضافة الأصل **{asset_name}** بنجاح!")
                            st.balloons()
                            st.rerun()

        # ===================================================================
        # Tab 3: تعديل/حذف أصل موجود (المدير فقط)
        # ===================================================================
        with tab3:
            st.markdown("#### ✏️ تعديل أو حذف أصل موجود")
            
            if all_assets:
                # اختيار الأصل
                asset_names = [f"{a.name} ({a.type})" for a in all_assets]
                selected_asset_label = st.selectbox(
                    "🏢 اختر الأصل المراد تعديله أو حذفه",
                    asset_names,
                    key='edit_asset_select_admin'
                )
                
                # العثور على الأصل المختار
                selected_index = asset_names.index(selected_asset_label)
                selected_asset = all_assets[selected_index]
                
                # عرض معلومات الأصل الحالية
                with st.expander("📄 البيانات الحالية", expanded=True):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**الاسم:** {selected_asset.name}")
                        st.write(f"**النوع:** {selected_asset.type}")
                    with col2:
                        st.write(f"**الموقع:** {selected_asset.location or '-'}")
                        st.write(f"**الوصف:** {selected_asset.description or '-'}")
                    
                    # عرض إحصائيات الوحدات والعقود
                    units_in_asset = session.query(Unit).filter_by(asset_id=selected_asset.id).all()
                    units_count = len(units_in_asset)
                    rented_count = sum(1 for u in units_in_asset if u.status == "مؤجر")
                    
                    # حساب العقود المرتبطة
                    unit_ids = [str(u.id) for u in units_in_asset]
                    contracts_linked = []
                    if unit_ids:
                        all_contracts = session.query(Contract).filter(Contract.status == "نشط").all()
                        for contract in all_contracts:
                            if contract.linked_units_ids:
                                contract_unit_ids = contract.linked_units_ids.split(',')
                                if any(uid in contract_unit_ids for uid in unit_ids):
                                    contracts_linked.append(contract)
                    
                    col_stat1, col_stat2, col_stat3 = st.columns(3)
                    with col_stat1:
                        st.metric("عدد الوحدات", units_count)
                    with col_stat2:
                        st.metric("وحدات مؤجرة", rented_count)
                    with col_stat3:
                        st.metric("عقود نشطة", len(contracts_linked))
            
                st.markdown("---")
                
                # Tabs للتعديل والحذف
                edit_tab, delete_tab = st.tabs(["✏️ تعديل البيانات", "🗑️ حذف الأصل"])
                
                # ===== Tab: تعديل البيانات =====
                with edit_tab:
                    with st.form("edit_asset_form_admin"):
                        st.markdown("##### ✏️ تعديل البيانات")
                        
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            new_name = st.text_input(
                                "اسم الأصل *",
                                value=selected_asset.name,
                                help="يمكن تعديل الاسم"
                            )
                            
                            types_list = ["عمارة", "مستودع", "أرض", "محطة وقود", "أخرى"]
                            current_type_index = types_list.index(selected_asset.type) if selected_asset.type in types_list else 0
                            
                            new_type = st.selectbox(
                                "نوع الأصل *",
                                types_list,
                                index=current_type_index
                            )
                        
                        with col2:
                            new_location = st.text_input(
                                "الموقع",
                                value=selected_asset.location if selected_asset.location else "",
                                placeholder="الموقع الجغرافي"
                            )
                        
                        new_description = st.text_area(
                            "الوصف/ملاحظات",
                            value=selected_asset.description if selected_asset.description else "",
                            height=100
                        )
                        
                        if len(contracts_linked) > 0:
                            st.warning(f"⚠️ تنبيه: هذا الأصل مرتبط بـ **{len(contracts_linked)}** عقد نشط. التعديلات ستؤثر على السجلات المرتبطة.")
                        
                        st.markdown("---")
                        
                        submit_edit = st.form_submit_button(
                            "💾 حفظ التعديلات",
                            use_container_width=True,
                            type="primary"
                        )
                        
                        if submit_edit:
                            if not new_name.strip():
                                st.error("⚠️ اسم الأصل مطلوب")
                            else:
                                # التحقق من عدم تكرار الاسم
                                existing = session.query(Asset).filter(
                                    Asset.name == new_name.strip(),
                                    Asset.id != selected_asset.id
                                ).first()
                                
                                if existing:
                                    st.error(f"⚠️ الاسم '{new_name}' مستخدم بالفعل لأصل آخر")
                                else:
                                    selected_asset.name = new_name.strip()
                                    selected_asset.type = new_type
                                    selected_asset.location = new_location.strip() if new_location else None
                                    selected_asset.description = new_description.strip() if new_description else None
                                    
                                    session.commit()
                                    st.success(f"✅ تم تحديث الأصل **{new_name}** بنجاح!")
                                    st.rerun()
                
                # ===== Tab: حذف الأصل =====
                with delete_tab:
                    st.markdown("### 🗑️ حذف الأصل نهائياً")
                    
                    # عرض تحذيرات بناءً على الارتباطات
                    can_delete = True
                    
                    if len(contracts_linked) > 0:
                        can_delete = False
                        st.error(f"🚫 **لا يمكن حذف هذا الأصل!**")
                        st.error(f"السبب: يوجد **{len(contracts_linked)}** عقد نشط مرتبط بوحدات في هذا الأصل")
                        
                        with st.expander("📋 عرض العقود المرتبطة"):
                            for contract in contracts_linked:
                                st.write(f"- عقد #{contract.contract_number or contract.id} - {contract.tenant.name} ({contract.contract_type})")
                        
                        st.info("💡 **للحذف:** يجب أولاً إلغاء جميع العقود المرتبطة من صفحة 'إلغاء عقد'")
                    
                    elif units_count > 0:
                        st.warning(f"⚠️ هذا الأصل يحتوي على **{units_count}** وحدة")
                        
                        delete_mode = st.radio(
                            "اختر طريقة الحذف:",
                            [
                                "حذف الأصل فقط (الوحدات ستبقى بدون أصل)",
                                "حذف الأصل وجميع الوحدات معاً"
                            ],
                            key='delete_mode_asset'
                        )
                        
                        if delete_mode == "حذف الأصل وجميع الوحدات معاً":
                            st.error("⚠️ **تحذير خطير:** سيتم حذف الأصل و**جميع الوحدات** المرتبطة به نهائياً!")
                        else:
                            st.info("ℹ️ الوحدات ستبقى في النظام ولكن بدون أصل مرتبط")
                    else:
                        st.success("✅ هذا الأصل لا يحتوي على وحدات ويمكن حذفه بأمان")
                        delete_mode = "حذف الأصل فقط" # Default value when no units
                    
                    if can_delete:
                        st.markdown("---")
                        st.markdown("### ⚠️ تأكيد الحذف")
                        
                        st.markdown(f"""
                        <div style="background-color: #3d1e1e; padding: 20px; border-radius: 10px; border-left: 5px solid #ff4444;">
                            <h4 style="color: #ff6b6b; margin-top: 0;">⚠️ تحذير نهائي</h4>
                            <p>أنت على وشك حذف الأصل: <strong>{selected_asset.name}</strong></p>
                            <p>هذا الإجراء <strong>لا يمكن التراجع عنه!</strong></p>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        st.markdown("<br>", unsafe_allow_html=True)
                        
                        # تأكيد الحذف
                        confirm_text = st.text_input(
                            f"للتأكيد، اكتب اسم الأصل: **{selected_asset.name}**",
                            placeholder=selected_asset.name,
                            key='confirm_delete_asset'
                        )
                        
                        if confirm_text == selected_asset.name:
                            st.success("✅ تم التأكيد - يمكنك الآن الضغط على زر الحذف")
                            
                            if st.button(
                                "🗑️ حذف الأصل نهائياً",
                                type="primary",
                                use_container_width=True,
                                key='final_delete_asset_btn'
                            ):
                                try:
                                    # حذف الوحدات إذا اختار المستخدم ذلك
                                    if units_count > 0 and delete_mode == "حذف الأصل وجميع الوحدات معاً":
                                        for unit in units_in_asset:
                                            session.delete(unit)
                                        st.info(f"🗑️ تم حذف {units_count} وحدة")
                                    
                                    # حذف الأصل
                                    asset_name_deleted = selected_asset.name
                                    session.delete(selected_asset)
                                    session.commit()
                                    
                                    st.success(f"✅ تم حذف الأصل **{asset_name_deleted}** بنجاح!")
                                    st.balloons()
                                    st.rerun()
                                    
                                except Exception as e:
                                    session.rollback()
                                    st.error(f"❌ حدث خطأ أثناء الحذف: {str(e)}")
                        else:
                            st.warning("⚠️ يرجى كتابة اسم الأصل بشكل صحيح للتأكيد")
            else:
                st.info("لا توجد أصول لتعديلها أو حذفها")

    # =========================================================================
    # للموظف: عرض + إضافة فقط
    # =========================================================================
    elif st.session_state.get('user_role') == 'Employee':
        st.subheader("➕ إدارة الأصول (موظف)")
        st.info("ℹ️ كموظف، يمكنك عرض وإضافة أصول جديدة فقط. للتعديل أو الحذف، تواصل مع المدير.")
        
        # Tabs للموظف (عرض + إضافة فقط)
        tab1, tab2 = st.tabs(["📋 عرض الأصول", "➕ إضافة أصل جديد"])
        
        # ===================================================================
        # Tab 1: عرض الأصول
        # ===================================================================
        with tab1:
            st.markdown("#### 📋 قائمة الأصول المسجلة")
            
            if all_assets:
                assets_display = []
                for asset in all_assets:
                    units_count = session.query(Unit).filter_by(asset_id=asset.id).count()
                    rented_count = session.query(Unit).filter_by(asset_id=asset.id, status="مؤجر").count()
                    
                    assets_display.append({
                        'ID': asset.id,
                        'اسم الأصل': asset.name,
                        'النوع': asset.type,
                        'الموقع': asset.location or '-',
                        'عدد الوحدات': units_count,
                        'الوحدات المؤجرة': rented_count
                    })
                
                assets_df = pd.DataFrame(assets_display)
                st.dataframe(assets_df, use_container_width=True, hide_index=True)
            else:
                st.info("لا توجد أصول مسجلة حالياً")
        
        # ===================================================================
        # Tab 2: إضافة أصل جديد
        # ===================================================================
        with tab2:
            st.markdown("#### ➕ إضافة أصل جديد")
            
            with st.form("add_asset_form_employee", clear_on_submit=True):
                st.markdown("##### 📝 بيانات الأصل الجديد")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    asset_name = st.text_input(
                        "اسم الأصل *",
                        placeholder="مثال: عمارة 5، مستودع 3",
                        help="اسم واضح ومميز للأصل"
                    )
                    
                    asset_type = st.selectbox(
                        "نوع الأصل *",
                        ["عمارة", "مستودع", "أرض", "محطة وقود", "أخرى"],
                        help="اختر نوع الأصل",
                        key="asset_type_emp"
                    )
                
                with col2:
                    asset_location = st.text_input(
                        "الموقع",
                        placeholder="مثال: حي الزهراء، شارع الملك",
                        help="الموقع الجغرافي للأصل (اختياري)"
                    )
                
                asset_description = st.text_area(
                    "الوصف/ملاحظات",
                    placeholder="معلومات إضافية عن الأصل...",
                    height=100,
                    help="أي تفاصيل إضافية عن الأصل"
                )
                
                st.markdown("---")
                
                submit_add = st.form_submit_button(
                    "✅ إضافة الأصل",
                    use_container_width=True,
                    type="primary"
                )
                
                if submit_add:
                    if not asset_name.strip():
                        st.error("⚠️ اسم الأصل مطلوب")
                    else:
                        # التحقق من عدم التكرار
                        existing_asset = session.query(Asset).filter_by(name=asset_name.strip()).first()
                        
                        if existing_asset:
                            st.error(f"⚠️ الأصل '{asset_name}' موجود بالفعل")
                        else:
                            new_asset = Asset(
                                name=asset_name.strip(),
                                type=asset_type,
                                location=asset_location.strip() if asset_location else None,
                                description=asset_description.strip() if asset_description else None
                            )
                            session.add(new_asset)
                            session.commit()
                            st.success(f"✅ تم إضافة الأصل **{asset_name}** بنجاح!")
                            st.balloons()
                            st.rerun()
# ==========================================

#=================================================================
#📦 نظام النسخ الاحتياطي الكامل - جاهز للاستخدام
#=================================================================



# ============================================================
# 1️⃣ دالة النسخ الاحتياطي
# ============================================================

def create_backup():
    """
    إنشاء نسخة احتياطية من قاعدة البيانات
    
    Returns:
        tuple: (success: bool, file_path: str, message: str)
    """
    try:
        # المسار الأصلي لقاعدة البيانات
        source_db = "real_estate_v2.db"
        
        # التحقق من وجود الملف
        if not os.path.exists(source_db):
            return False, None, "❌ لم يتم العثور على قاعدة البيانات!"
        
        # مجلد النسخ الاحتياطية المؤقت
        backup_dir = "temp_backups"
        os.makedirs(backup_dir, exist_ok=True)
        
        # اسم الملف مع التاريخ والوقت
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"نسخة_احتياطية_{timestamp}.db"
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # نسخ الملف
        shutil.copy2(source_db, backup_path)
        
        # حساب حجم الملف
        file_size = os.path.getsize(backup_path)
        file_size_mb = file_size / (1024 * 1024)
        
        return True, backup_path, f"✅ تم إنشاء النسخة بنجاح ({file_size_mb:.2f} MB)"
        
    except Exception as e:
        return False, None, f"❌ حدث خطأ: {str(e)}"


# ============================================================
# 2️⃣ دالة استرجاع النسخة الاحتياطية
# ============================================================

def restore_backup(uploaded_file):
    """
    استرجاع قاعدة البيانات من ملف محمّل
    
    Args:
        uploaded_file: الملف المرفوع من st.file_uploader
        
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        # اسم قاعدة البيانات الحالية
        db_file = "real_estate_v2.db"
        
        # حفظ نسخة احتياطية من القاعدة الحالية قبل الاستبدال
        if os.path.exists(db_file):
            backup_current = f"{db_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(db_file, backup_current)
        
        # كتابة الملف الجديد
        with open(db_file, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        return True, "✅ تم استرجاع النسخة الاحتياطية بنجاح!"
        
    except Exception as e:
        return False, f"❌ حدث خطأ أثناء الاسترجاع: {str(e)}"


# ============================================================
# 3️⃣ دالة الحصول على معلومات قاعدة البيانات
# ============================================================

def get_database_info():
    """
    الحصول على معلومات وإحصائيات قاعدة البيانات
    
    Returns:
        dict: معلومات قاعدة البيانات
    """
    try:
        info = {}
        
        # حجم الملف
        if os.path.exists("real_estate_v2.db"):
            db_size = os.path.getsize("real_estate_v2.db")
            info['size_bytes'] = db_size
            info['size_mb'] = db_size / (1024 * 1024)
            info['size_kb'] = db_size / 1024
        else:
            info['size_bytes'] = 0
            info['size_mb'] = 0
            info['size_kb'] = 0
        
        # عدد السجلات
        info['total_assets'] = session.query(Asset).count()
        info['total_units'] = session.query(Unit).count()
        info['total_tenants'] = session.query(Tenant).count()
        info['total_contracts'] = session.query(Contract).count()
        info['total_payments'] = session.query(Payment).count()
        info['total_records'] = (
            info['total_assets'] + 
            info['total_units'] + 
            info['total_tenants'] + 
            info['total_contracts'] + 
            info['total_payments']
        )
        
        # تاريخ آخر تعديل
        if os.path.exists("real_estate_v2.db"):
            mod_time = os.path.getmtime("real_estate_v2.db")
            info['last_modified'] = datetime.fromtimestamp(mod_time)
        else:
            info['last_modified'] = None
        
        return info
        
    except Exception as e:
        st.error(f"خطأ في الحصول على معلومات قاعدة البيانات: {str(e)}")
        return {}


# ============================================================
# 4️⃣ دالة تصدير البيانات إلى Excel (نسخة احتياطية إضافية)
# ============================================================

def export_to_excel():
    """
    تصدير جميع البيانات إلى ملف Excel (نسخة احتياطية قابلة للقراءة)
    
    Returns:
        tuple: (success: bool, file_path: str, message: str)
    """
    try:
        # إنشاء مجلد مؤقت
        export_dir = "temp_exports"
        os.makedirs(export_dir, exist_ok=True)
        
        # اسم الملف
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        excel_filename = f"تصدير_البيانات_{timestamp}.xlsx"
        excel_path = os.path.join(export_dir, excel_filename)
        
        # جلب البيانات
        assets_df = pd.read_sql(session.query(Asset).statement, session.bind)
        units_df = pd.read_sql(session.query(Unit).statement, session.bind)
        tenants_df = pd.read_sql(session.query(Tenant).statement, session.bind)
        contracts_df = pd.read_sql(session.query(Contract).statement, session.bind)
        payments_df = pd.read_sql(session.query(Payment).statement, session.bind)
        
        # كتابة إلى Excel
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            assets_df.to_excel(writer, sheet_name='الأصول', index=False)
            units_df.to_excel(writer, sheet_name='الوحدات', index=False)
            tenants_df.to_excel(writer, sheet_name='المستأجرين', index=False)
            contracts_df.to_excel(writer, sheet_name='العقود', index=False)
            payments_df.to_excel(writer, sheet_name='الدفعات', index=False)
        
        return True, excel_path, "✅ تم التصدير بنجاح"
        
    except Exception as e:
        return False, None, f"❌ حدث خطأ: {str(e)}"


# ============================================================
# 5️⃣ صفحة إدارة النسخ الاحتياطية (الواجهة الكاملة)
# ============================================================

def backup_page():
    """صفحة إدارة النسخ الاحتياطية - الواجهة الرئيسية"""
    
    st.header("💾 إدارة النسخ الاحتياطية")
    
    # التحقق من الصلاحيات
    if st.session_state.get('user_role') != 'Admin':
        st.error("⚠️ هذه الصفحة متاحة للمدير فقط")
        return
    
    # رسالة تحذيرية مهمة
    st.markdown("""
    <div style="background-color: #3d1e1e; padding: 20px; border-radius: 10px; border-left: 5px solid #ff4444; margin-bottom: 20px;">
            <strong style="color: #ffd700;">⭐ احفظ نسخة احتياطية كل أسبوع على الأقل!</strong>
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # الحصول على معلومات قاعدة البيانات
    db_info = get_database_info()
    
    # عرض إحصائيات قاعدة البيانات
    st.markdown("---")
    st.subheader("📊 معلومات قاعدة البيانات")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "📦 حجم قاعدة البيانات",
            f"{db_info.get('size_mb', 0):.2f} MB",
            help=f"{db_info.get('size_kb', 0):.0f} KB"
        )
    
    with col2:
        st.metric(
            "📝 إجمالي السجلات",
            f"{db_info.get('total_records', 0):,}",
            help="مجموع كل السجلات في النظام"
        )
    
    with col3:
        st.metric("🏢 الأصول", db_info.get('total_assets', 0))
    
    with col4:
        st.metric("👥 المستأجرين", db_info.get('total_tenants', 0))
    
    # صف ثاني من الإحصائيات
    col5, col6, col7, col8 = st.columns(4)
    
    with col5:
        st.metric("🏠 الوحدات", db_info.get('total_units', 0))
    
    with col6:
        st.metric("📄 العقود", db_info.get('total_contracts', 0))
    
    with col7:
        st.metric("💰 الدفعات", db_info.get('total_payments', 0))
    
    with col8:
        if db_info.get('last_modified'):
            last_mod = db_info['last_modified'].strftime('%Y-%m-%d')
            st.metric("📅 آخر تعديل", last_mod)
    
    # =========================================================================
    # قسم 1: حفظ نسخة احتياطية
    # =========================================================================
    st.markdown("---")
    st.subheader("📤 حفظ نسخة احتياطية")
    
    st.info("""
    💡 **كيفية الحفظ:**
    1. اضغط على زر "تحميل نسخة احتياطية"
    2. سيتم تنزيل ملف `.db` على جهازك
    3. احفظ الملف في مكان آمن (Google Drive، OneDrive، أو جهازك)
    4. كرر العملية كل أسبوع أو عند إجراء تغييرات مهمة
    """)
    
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        # زر تحميل نسخة احتياطية (قاعدة بيانات)
        if st.button(
            "📥 تحميل نسخة احتياطية (Database)", 
            type="primary", 
            use_container_width=True,
            help="حفظ ملف قاعدة البيانات الكامل"
        ):
            with st.spinner("جاري إنشاء النسخة الاحتياطية..."):
                success, backup_path, message = create_backup()
                
                if success:
                    # قراءة الملف لتحميله
                    with open(backup_path, "rb") as f:
                        file_data = f.read()
                    
                    # زر التحميل
                    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
                    st.download_button(
                        label="⬇️ اضغط هنا لتحميل الملف",
                        data=file_data,
                        file_name=f"نسخة_احتياطية_{timestamp}.db",
                        mime="application/octet-stream",
                        use_container_width=True,
                        type="primary"
                    )
                    
                    st.success(message)
                    st.balloons()
                    
                    # حذف الملف المؤقت بعد التحميل
                    try:
                        os.remove(backup_path)
                    except:
                        pass
                else:
                    st.error(message)
    
    with col_btn2:
        # زر تصدير إلى Excel
        if st.button(
            "📊 تصدير إلى Excel",
            use_container_width=True,
            help="تصدير البيانات في ملف Excel قابل للقراءة"
        ):
            with st.spinner("جاري تصدير البيانات..."):
                success, excel_path, message = export_to_excel()
                
                if success:
                    with open(excel_path, "rb") as f:
                        excel_data = f.read()
                    
                    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
                    st.download_button(
                        label="⬇️ اضغط هنا لتحميل ملف Excel",
                        data=excel_data,
                        file_name=f"تصدير_البيانات_{timestamp}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                    
                    st.success(message)
                    
                    # حذف الملف المؤقت
                    try:
                        os.remove(excel_path)
                    except:
                        pass
                else:
                    st.error(message)
    
    # =========================================================================
    # قسم 2: استرجاع نسخة احتياطية
    # =========================================================================
    st.markdown("---")
    st.subheader("📥 استرجاع نسخة احتياطية")
    
    st.warning("""
    ⚠️ **تحذير مهم:**
    - سيتم **استبدال جميع البيانات الحالية** بالنسخة المحملة
    - تأكد من حفظ نسخة من البيانات الحالية قبل الاسترجاع
    - استخدم هذه الميزة فقط عند الضرورة
    """)
    
    uploaded_file = st.file_uploader(
        "📁 اختر ملف النسخة الاحتياطية (.db)",
        type=['db'],
        help="ارفع ملف قاعدة البيانات الذي حفظته سابقاً",
        key='backup_uploader'
    )
    
    if uploaded_file:
        # عرض معلومات الملف المحمل
        st.markdown("---")
        st.markdown("### 📋 معلومات الملف المحمل")
        
        col_info1, col_info2, col_info3 = st.columns(3)
        
        with col_info1:
            st.info(f"📄 **الاسم:** {uploaded_file.name}")
        
        with col_info2:
            file_size_mb = uploaded_file.size / (1024 * 1024)
            st.info(f"📊 **الحجم:** {file_size_mb:.2f} MB")
        
        with col_info3:
            st.info(f"📦 **النوع:** Database File")
        
        st.markdown("---")
        
        # خطوات التأكيد
        st.markdown("### ⚠️ تأكيد الاسترجاع")
        
        # Checkbox للتأكيد الأول
        confirm_1 = st.checkbox(
            "✅ أؤكد أنني حفظت نسخة احتياطية من البيانات الحالية",
            key='confirm_backup_1'
        )
        
        # Checkbox للتأكيد الثاني
        confirm_2 = st.checkbox(
            "✅ أؤكد استرجاع النسخة الاحتياطية واستبدال جميع البيانات الحالية",
            key='confirm_backup_2',
            disabled=not confirm_1
        )
        
        # زر الاسترجاع
        if confirm_1 and confirm_2:
            st.markdown("<br>", unsafe_allow_html=True)
            
            col_restore1, col_restore2, col_restore3 = st.columns([1, 2, 1])
            
            with col_restore2:
                if st.button(
                    "🔄 استرجاع النسخة الآن",
                    type="primary",
                    use_container_width=True,
                    key='restore_btn'
                ):
                    with st.spinner("⏳ جاري استرجاع النسخة الاحتياطية..."):
                        success, message = restore_backup(uploaded_file)
                        
                        if success:
                            st.success(message)
                            st.balloons()
                            
                            st.markdown("---")
                            st.info("""
                            ℹ️ **الخطوات التالية:**
                            1. انتظر 5 ثواني
                            2. سيتم تحديث الصفحة تلقائياً
                            3. سجل دخول مرة أخرى للتأكد من التغييرات
                            """)
                            
                            # إعادة تحميل الصفحة بعد 5 ثواني
                            import time
                            time.sleep(5)
                            st.rerun()
                        else:
                            st.error(message)
        else:
            st.warning("⚠️ يرجى تأكيد كلا الخيارين أعلاه لتفعيل زر الاسترجاع")
    
    # =========================================================================
    # قسم 3: نصائح وإرشادات
    # =========================================================================
    st.markdown("---")
    st.subheader("💡 نصائح مهمة")
    
    with st.expander("📚 كيفية حفظ النسخ الاحتياطية بشكل صحيح", expanded=False):
        st.markdown("""
        ### ✅ أفضل الممارسات:
        
        1. **التكرار:**
           - احفظ نسخة احتياطية **كل أسبوع** على الأقل
            - بعد إضافة عقود جديدة مهمة
            - قبل أي تحديث للنظام
        
        2. **التخزين:**
           - احفظ في **3 أماكن مختلفة**:
            - 📱 Google Drive
            - 💻 جهازك المحلي
            - ☁️ OneDrive أو Dropbox
        
        3. **التسمية:**
            - استخدم أسماء واضحة مثل:
            - `نسخة_احتياطية_2024-01-15.db`
            - `backup_before_update.db`
        
        4. **الاختبار:**
            - جرب استرجاع النسخة كل شهر للتأكد من صلاحيتها
        
        ### ⚠️ تحذيرات:
        
        - ❌ لا تحذف النسخ القديمة - احتفظ بآخر 5 نسخ على الأقل
        - ❌ لا تعتمد على مكان واحد فقط للحفظ
        - ❌ لا تنسى حفظ نسخة قبل أي تحديث كبير
        """)
    
    with st.expander("🔧 استكشاف الأخطاء وحلها", expanded=False):
        st.markdown("""
        ### مشاكل شائعة وحلولها:
        
        **1. "لم يتم العثور على قاعدة البيانات"**
        - الحل: تأكد من وجود ملف `real_estate_v2.db` في مجلد التطبيق
        
        **2. "حدث خطأ أثناء الاسترجاع"**
        - الحل: تأكد من أن الملف المحمل هو نسخة احتياطية صحيحة (.db)
        - جرب تحميل الملف مرة أخرى
        
        **3. "البيانات ضاعت بعد التحديث"**
        - الحل: استرجع آخر نسخة احتياطية من صفحة "النسخ الاحتياطي"
        
        **4. "الملف كبير جداً"**
        - الحل: صدّر البيانات إلى Excel وحمّل الملفات القديمة
        """)
    
    with st.expander("📅 جدول النسخ الاحتياطي الموصى به", expanded=False):
        st.markdown("""
        | الفترة | الإجراء | الأولوية |
        |--------|---------|---------|
        | **يومياً** | إذا كان هناك إدخال بيانات كثير | 🟡 متوسطة |
        | **أسبوعياً** | نسخة احتياطية روتينية | 🟢 عالية |
        | **شهرياً** | نسخة احتياطية كاملة مع اختبار | 🔴 حرجة |
        | **قبل التحديثات** | نسخة احتياطية إلزامية | 🔴 حرجة |
        | **بعد عقود مهمة** | نسخة احتياطية فورية | 🟢 عالية |
        """)


# ============================================================
# 6️⃣ إضافة الصفحة للقائمة الرئيسية
# ============================================================

def main():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    
    if st.session_state['logged_in']:
        
        with st.sidebar:
            st.title("القائمة الرئيسية")
            
            st.markdown(f"**المستخدم:** {st.session_state['username']} ({st.session_state['user_role']})")
            
            role = st.session_state['user_role']
            
            if role == 'Admin':
                pages = {
                    "لوحة المؤشرات": dashboard,
                    "إدارة الأصول": manage_assets_only,  # ← جديد
                    "إدارة الوحدات": manage_assets,
                    "إدارة المستأجرين": manage_tenants,
                    "إدارة العقود": manage_contracts,
                    "إلغاء عقد": cancel_contract_page,
                    "إدارة الدفعات": manage_payments,
                    "التقارير": reports_page,
                    "💾 النسخ الاحتياطي": backup_page,
                    "الإعدادات": settings_page
                }
            else: # Employee role
                pages = {
                    "لوحة المؤشرات": dashboard,
                    "إدارة الأصول": manage_assets_only,  # ← جديد (عرض فقط)
                    "إدارة الوحدات": manage_assets,
                    "إدارة المستأجرين": manage_tenants,
                    "إدارة العقود": manage_contracts,
                    "إدارة الدفعات": manage_payments,
                    "التقارير": reports_page
                }
            selection = st.radio("اختر الصفحة", list(pages.keys()))
            
            if st.button("تسجيل الخروج", type="primary"):
                st.session_state['logged_in'] = False
                st.session_state['user_role'] = None
                st.session_state['username'] = None
                st.rerun()

        # عرض الصفحة المختارة
        pages[selection]()
        
    else:
        login_page()

if __name__ == "__main__":
    main()
