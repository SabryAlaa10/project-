import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, ForeignKey, Text, text
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from datetime import date, datetime
import hashlib
import io
import base64
import os

# ==========================================
# 1. إعدادات الصفحة والتهيئة
# ==========================================
st.set_page_config(
    page_title="نظام إدارة الجمعية العقارية",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# تنسيق الواجهة العربية وتكبير الخط وتحسين الشريط الجانبي
st.markdown("""
    <style>
    /* ============ تنسيق حقول الإدخال بشكل صحيح ============ */
    
    /* لون النص المكتوب داخل Text Input */
    input[type="text"],
    input[type="number"],
    input[type="date"],
    textarea {
        background-color: #2a2d3e !important;
        color: #e5e7eb !important;
        border: 2px solid #60a5fa !important;
        border-radius: 6px !important;
        padding:  12px !important;
        font-size: 16px !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
    }
    
    /* Placeholder - النص الفاتح عند الحقل الفارغ */
    input::placeholder,
    textarea::placeholder {
        color: #9ca3af !important;
        opacity: 0.8 !important;
    }
    
    /* عند التركيز على الحقل */
    input[type="text"]:focus,
    input[type="number"]: focus,
    input[type="date"]:focus,
    textarea:focus {
        background-color: #3a3f55 !important;
        color: #a7f3d0 !important;
        border-color: #a7f3d0 !important;
        outline: none !important;
        box-shadow: 0 0 10px rgba(167, 243, 208, 0.4) !important;
    }
    
    /* Select / Dropdown */
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
    
    /* Streamlit specific inputs */
    . stTextInput input {
        background-color: #2a2d3e !important;
        color: #e5e7eb !important;
        border: 2px solid #60a5fa !important;
    }
    
    .stNumberInput input {
        background-color: #2a2d3e !important;
        color: #e5e7eb !important;
        border: 2px solid #60a5fa !important;
    }
    
    . stSelectbox select {
        background-color: #2a2d3e !important;
        color: #e5e7eb !important;
        border: 2px solid #60a5fa !important;
    }
    
    /* Label styling - لون الكلمة فوق الحقل */
    label {
        color: #e5e7eb !important;
        font-weight: 600 !important;
        font-size: 15px !important;
    }
    
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. قاعدة البيانات والنماذج
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "real_estate_v2.db")
Base = declarative_base()
engine = create_engine(f'sqlite:///{DB_PATH}', connect_args={'check_same_thread': False})
Session = sessionmaker(bind=engine)
session = Session()

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
    contract_number = Column(String, unique=True)  # جديد
    tenant_id = Column(Integer, ForeignKey('tenants.id'))
    contract_type = Column(String)
    rent_amount = Column(Float)
    payment_freq = Column(String)
    start_date = Column(Date)
    end_date = Column(Date)
    vat_rate = Column(Float, default=0.0)
    linked_units_ids = Column(String)
    tenant = relationship("Tenant")

class Payment(Base):
    __tablename__ = 'payments'
    id = Column(Integer, primary_key=True)
    contract_id = Column(Integer, ForeignKey('contracts.id'))
    payment_number = Column(Integer)  # ← جديد: رقم الدفعة داخل العقد
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

Base.metadata.create_all(engine)
# إضافة رقم الدفعة لكل عقد
try:
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    existing_columns = [col['name'] for col in inspector.get_columns('payments')]
    
    if 'payment_number' not in existing_columns:
        with engine.connect() as conn:
            conn.execute(text('ALTER TABLE payments ADD COLUMN payment_number INTEGER'))
            conn.commit()
            print("✅ تم إضافة عمود payment_number")
            
            # تحديث الدفعات الموجودة بأرقام تسلسلية
            contracts = session.query(Contract).all()
            for contract in contracts:
                payments = session.query(Payment).filter_by(contract_id=contract.id).order_by(Payment.due_date).all()
                for idx, payment in enumerate(payments, start=1):
                    payment.payment_number = idx
            
            session.commit()
            print("✅ تم ترقيم الدفعات الموجودة")
except Exception as e:
    print(f"تنبيه: {e}")
    pass
# تحديث جدول العقود لإضافة رقم العقد
try:
    from sqlalchemy import inspect
    inspector = inspect(engine)
    existing_columns = [col['name'] for col in inspector.get_columns('contracts')]
    
    if 'contract_number' not in existing_columns:
        with engine.connect() as conn:
            conn.execute('ALTER TABLE contracts ADD COLUMN contract_number VARCHAR')
            conn.commit()
except:
    pass
# تحديث جدول المستأجرين إذا لزم الأمر
try:
    from sqlalchemy import inspect
    inspector = inspect(engine)
    existing_columns = [col['name'] for col in inspector.get_columns('tenants')]
    
    if 'email' not in existing_columns:
        with engine.connect() as conn:
            conn.execute('ALTER TABLE tenants ADD COLUMN email VARCHAR')
            conn.execute('ALTER TABLE tenants ADD COLUMN national_id VARCHAR')
            conn.execute('ALTER TABLE tenants ADD COLUMN address TEXT')
            conn.execute('ALTER TABLE tenants ADD COLUMN notes TEXT')
            conn.execute('ALTER TABLE tenants ADD COLUMN created_date DATE')
            conn.commit()
except:
    pass


# تحديث جدول الدفعات لإضافة الحقول الجديدة وإصلاح البيانات
try:
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    existing_columns = [col['name'] for col in inspector.get_columns('payments')]
    
    with engine.connect() as conn:
        if 'paid_amount' not in existing_columns:
            conn.execute(text('ALTER TABLE payments ADD COLUMN paid_amount FLOAT DEFAULT 0.0'))
            print("✅ تم إضافة عمود paid_amount")
        
        if 'remaining_amount' not in existing_columns:
            conn.execute(text('ALTER TABLE payments ADD COLUMN remaining_amount FLOAT DEFAULT 0.0'))
            print("✅ تم إضافة عمود remaining_amount")
        
        conn.commit()
        
        # تحديث الدفعات الموجودة مرة واحدة فقط
        result = conn.execute(text("SELECT COUNT(*) FROM payments WHERE paid_amount IS NULL OR remaining_amount IS NULL"))
        needs_update = result.scalar()
        
        if needs_update > 0:
            # تحديث جميع الدفعات الموجودة بشكل صحيح
            result = conn.execute(text("SELECT id, total, status FROM payments"))
            all_payments = result.fetchall()
            
            for payment in all_payments:
                payment_id, total, status = payment
                
                if status == 'مدفوع':
                    conn.execute(
                        text("UPDATE payments SET paid_amount = :paid, remaining_amount = 0 WHERE id = :id"),
                        {"paid": total, "id": payment_id}
                    )
                else:
                    conn.execute(
                        text("UPDATE payments SET paid_amount = 0, remaining_amount = :remaining WHERE id = :id"),
                        {"remaining": total, "id": payment_id}
                    )
            
            conn.commit()
            print(f"✅ تم تحديث {len(all_payments)} دفعة بنجاح")
        
except Exception as e:
    print(f"خطأ في التحديث: {e}")
    pass
# ==========================================
# 3. دوال مساعدة والبيانات الأولية (Seed Data) - تم توحيدها وتصحيحها
# ==========================================
def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_login(username, password):
    username = username.strip().lower()
    password = password.strip()
    user = session.query(User).filter_by(username=username).first()
    if user and user.password_hash == hash_password(password):
        return user
    return None

def generate_units_from_list(asset_obj, unit_list, usage_type="سكني"):
    """دالة مساعدة لإنشاء الوحدات من قائمة (رقم الشقة، رقم الدور)"""
    units = []
    asset_id = asset_obj.id # استخدام الـ ID المأخوذ من قاعدة البيانات
    
    for unit_number, floor_num in unit_list:
        status = "فاضي"
        # استثناء خاص لعمارة 4 - الدور الأول مؤجر بالكامل
        # هذا الشرط يعتمد على أن الدور الأول في عمارة 4 مؤجر في البداية
        if asset_obj.name == "عمارة 4" and floor_num == 1 and unit_number != 0:
            status = "مؤجر"
        
        # استثناء خاص للملحق والمعرض
        if floor_num == "معرض": # حالة معرض (تم تمريرها كـ (1، "معرض"))
            u_num = f"معرض {unit_number}"
            u_floor = "أرضي"
            usage = "تجاري"
        elif unit_number == 0: # حالة ملحق (في الإكسل رقم الشقة 0)
            u_num = "ملحق"
            u_floor = "سطح"
            usage = usage_type
        else: # حالة شقة عادية
            u_num = str(unit_number)
            u_floor = str(floor_num)
            usage = usage_type

        units.append(Unit(
            asset_id=asset_id, 
            unit_number=u_num, 
            floor=u_floor, 
            usage_type=usage, 
            status=status
        ))
    return units

def init_seed_data():
    """تهيئة البيانات المطلوبة عند التشغيل الأول"""
    
    # تحقق من وجود مستخدمين
    if session.query(User).first():
        return # البيانات الأولية موجودة بالفعل، لا تقم بالتهيئة

    # 1. المستخدمين (Admin و Employee)
    admin = User(username="admin", password_hash=hash_password("admin123"), role="Admin")
    emp = User(username="emp", password_hash=hash_password("emp123"), role="Employee")
    session.add_all([admin, emp])
    session.commit() # حفظ المستخدمين لضمان تسجيلهم

    # 2. المستأجرين
    tenants_data = [
        ("مستشفى الأندلسية", "مستشفى"),
        ("مستشفى السقاف", "مستشفى"),
        ("نظارات الصاحب", "شركة"),
        ("سنابل السلام", "شركة"),
        ("صيدلية الدواء", "صيدلية"),
        ("مستثمر محطة الوقود", "مستثمر")
    ]
    for t_name, t_type in tenants_data:
        session.add(Tenant(name=t_name, type=t_type))
    session.commit()

    # 3. الأصول
    assets_map = {
        "عمارة 1": Asset(name="عمارة 1", type="عمارة", description="تم تحديث الوحدات حسب ملف الإكسل"),
        "عمارة 2": Asset(name="عمارة 2", type="عمارة", description="تم تحديث الوحدات حسب ملف الإكسل"),
        "عمارة 3": Asset(name="عمارة 3", type="عمارة", description="تم تحديث الوحدات حسب ملف الإكسل"),
        "عمارة 4": Asset(name="عمارة 4", type="عمارة", description="تم تحديث الوحدات حسب ملف الإكسل (الدور الأول مؤجر بالكامل)"),
        "مستودع 1": Asset(name="مستودع 1", type="مستودع", description="تجاري / مؤجر"),
        "مستودع 2": Asset(name="مستودع 2", type="مستودع", description="تجاري / مؤجر"),
        "أرض شارع حراء (محطة)": Asset(name="أرض شارع حراء (محطة)", type="محطة وقود", location="شارع حراء", description="2500م – محطة"),
        "أرض الميزان": Asset(name="أرض الميزان", type="أرض", description="1500م – حق انتفاع"),
        "أرض كيلو 14": Asset(name="أرض كيلو 14", type="أرض", location="كيلو 14", description="12000م – غير مستغلة")
    }
    
    session.add_all(assets_map.values())
    session.commit()
    
    # جلب الأصول مع IDs الصحيحة
    b1 = session.query(Asset).filter_by(name="عمارة 1").first()
    b2 = session.query(Asset).filter_by(name="عمارة 2").first()
    b3 = session.query(Asset).filter_by(name="عمارة 3").first()
    b4 = session.query(Asset).filter_by(name="عمارة 4").first()
    w1 = session.query(Asset).filter_by(name="مستودع 1").first()
    w2 = session.query(Asset).filter_by(name="مستودع 2").first()
    l1 = session.query(Asset).filter_by(name="أرض شارع حراء (محطة)").first()
    l2 = session.query(Asset).filter_by(name="أرض الميزان").first()
    l3 = session.query(Asset).filter_by(name="أرض كيلو 14").first()
    
    # 4. الوحدات (Units Generation) - بناءً على صور الإكسل
    units_list = []
    
    # --- عمارة 1 (ID=b1.id) ---
    b1_units_data = [
        (111, 1), (112, 1), (113, 1), (114, 1), (115, 1), (116, 1),
        (121, 2), (122, 2), (123, 2), (124, 2), (125, 2), (126, 2),
        (131, 3), (132, 3), (133, 3), (134, 3), (135, 3), (136, 3),
        (141, 4), (112, 4), (113, 4), (114, 4), (115, 4), (116, 4),
        (121, 5), (122, 5), (123, 5), (124, 5), (125, 5), (126, 5),
        (131, 6), (132, 6), (133, 6), (134, 6), (135, 6), (136, 6),
        (0, 0), # ملحق
        (1, "معرض") # معرض 1
    ]
    units_list.extend(generate_units_from_list(b1, b1_units_data))

    # --- عمارة 2 (ID=b2.id) ---
    b2_units_data = [
        (211, 1), (212, 1), (213, 1), (214, 1), (215, 1), (216, 1),
        (221, 2), (222, 2), (223, 2), (224, 2), (225, 2), (226, 2),
        (231, 3), (232, 3), (233, 3), (234, 3), (235, 3), (236, 3),
        (241, 4), (242, 4), (243, 4), (245, 4), (116, 4), 
        (251, 5), (252, 5), (253, 5), (254, 5), (255, 5), (256, 5),
        (261, 6), (262, 6), (263, 6), (264, 6), (265, 6), (266, 6),
        (0, 0), # ملحق
        (1, "معرض") # معرض 1
    ]
    units_list.extend(generate_units_from_list(b2, b2_units_data))

    # --- عمارة 3 (ID=b3.id) ---
    b3_units_data = [
        (311, 1), (312, 1), (313, 1), (314, 1), (315, 1), (316, 1),
        (321, 2), (322, 2), (323, 2), (324, 2), (325, 2), (326, 2),
        (331, 3), (332, 3), (333, 3), (334, 3), (335, 3), (336, 3),
        (0, 0), # ملحق
    ]
    units_list.extend(generate_units_from_list(b3, b3_units_data))

    # --- عمارة 4 (ID=b4.id) ---
    b4_units_data = [
        (411, 1), (412, 1), (413, 1), (414, 1), (415, 1), (416, 1),
        (421, 2), (422, 2), (423, 2), (424, 2), (425, 2), (426, 2),
        (431, 3), (432, 3), (433, 3), (434, 3), (435, 3), (436, 3),
        (0, 0), # ملحق
    ]
    units_list.extend(generate_units_from_list(b4, b4_units_data))


    # --- الأصول الأخرى (الحالة مؤجر كما طلب) ---
    # مؤجر: مستودع 1, مستودع 2, أرض المحطة, أرض الميزان
    units_list.append(Unit(asset_id=w1.id, unit_number="مستودع 1", usage_type="تجاري", status="مؤجر"))
    units_list.append(Unit(asset_id=w2.id, unit_number="مستودع 2", usage_type="تجاري", status="مؤجر"))
    units_list.append(Unit(asset_id=l1.id, unit_number="أرض المحطة", area=2500, usage_type="تجاري", status="مؤجر"))
    units_list.append(Unit(asset_id=l2.id, unit_number="أرض الميزان (حق انتفاع)", area=1500, usage_type="حق انتفاع", status="مؤجر"))
    
    # فاضي: أرض كيلو 14
    units_list.append(Unit(asset_id=l3.id, unit_number="أرض كيلو 14", area=12000, usage_type="أرض", status="فاضي"))

    session.add_all(units_list)
    session.commit()
    
# تشغيل دالة البيانات الأولية لإنشاء الجداول والمستخدمين والوحدات عند بدء التشغيل
init_seed_data()


# ==========================================
# 4. مكونات الواجهة
# ==========================================

def login_page():
    # إضافة مسافة فارغة في الأعلى
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # إنشاء 3 أعمدة للتوسيط
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        # عرض الشعار (إذا كان موجود في نفس المجلد)
        # يمكنك وضع ملف الصورة في نفس مجلد المشروع باسم "logo.png"
        try:
            st.image("logo.png", use_container_width=True)
        except:
            # إذا لم يكن الشعار موجود، عرض اسم الجمعية فقط
            st.markdown("""
                <div style="text-align: center; padding: 20px;">
                    <h1 style="color: #6B9B7A; font-size: 48px; margin-bottom: 0;">زواج</h1>
                    <p style="color: #E07A7A; font-size: 20px; margin-top: 10px;">
                        الجمعية الخيرية لمساعدة الشباب<br>
                        على الزواج والتوجيه الأسري بجدة
                    </p>
                </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # بطاقة تسجيل الدخول
        st.markdown("""
            <div style="
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                padding: 3px;
                border-radius: 15px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.1);
            ">
                <div style="
                    background: #1E1E1E;
                    padding: 30px;
                    border-radius: 13px;
                    text-align: center;
                ">
                    <h2 style="color: #FFFFFF; margin-bottom: 10px;">🔐 تسجيل الدخول</h2>
                    <p style="color: #B0B0B0; font-size: 14px;">نظام إدارة الأصول العقارية</p>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        # حقول الإدخال
        with st.container():
            username = st.text_input(
                "👤 اسم المستخدم",
                placeholder="أدخل اسم المستخدم",
                key="login_username"
            ).strip().lower()
            
            password = st.text_input(
                "🔒 كلمة المرور",
                type="password",
                placeholder="أدخل كلمة المرور",
                key="login_password"
            ).strip()
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            # زر الدخول بتصميم مميز
            if st.button("🚀 دخول", use_container_width=True, type="primary"):
                if not username or not password:
                    st.error("⚠️ الرجاء إدخال اسم المستخدم وكلمة المرور")
                else:
                    user = check_login(username, password)
                    if user:
                        st.session_state['logged_in'] = True
                        st.session_state['user_role'] = user.role
                        st.session_state['username'] = user.username
                        st.success("✅ تم تسجيل الدخول بنجاح!")
                        st.rerun()
                    else:
                        st.error("❌ اسم المستخدم أو كلمة المرور غير صحيحة")
        
        # معلومات إضافية في الأسفل
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("""
            <div style="text-align: center; color: #808080; font-size: 12px; padding: 20px;">
                <hr style="border: 1px solid #333; margin: 20px 0;">
                <p>
                    جميع الحقوق محفوظة © 2024<br>
                    <strong style="color: #6B9B7A;">جمعية زواج الخيرية</strong>
                </p>
            </div>
        """, unsafe_allow_html=True)


def dashboard():
    st.title("📊 لوحة المؤشرات (الأسبوعي)")
    
    # KPIs
    total_income = session.query(Payment).filter_by(status='مدفوع').with_entities(Payment.total).all()
    income_val = sum([x[0] for x in total_income])
    
    # الحصول على المتأخرات لتحديث KPIs والشارت الجديد
    overdue_payments = session.query(Payment).filter(Payment.status != 'مدفوع', Payment.due_date < date.today()).all()
    overdue_count = len(overdue_payments)
    overdue_amount = sum([p.total for p in overdue_payments])

    empty_units = session.query(Unit).filter_by(status='فاضي').count()
    rented_units = session.query(Unit).filter_by(status='مؤجر').count()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("إجمالي الدخل المحصل", f"{income_val:,.0f} ريال")
    c2.metric("المبالغ المتأخرة", f"{overdue_amount:,.0f} ريال", f"{overdue_count} دفعة", delta_color="inverse")
    c3.metric("الوحدات المؤجرة", rented_units)
    c4.metric("الوحدات الفاضية", empty_units)

    st.markdown("---")
    
    col_chart1, col_chart2 = st.columns(2)
    col_chart1, col_chart2 = st.columns(2)
    with col_chart1:
        st.subheader("توزيع حالة الوحدات")
        status_df = pd.DataFrame({'الحالة': ['مؤجر', 'فاضي'], 'العدد': [rented_units, empty_units]})
        st.bar_chart(status_df.set_index('الحالة'))
    
    with col_chart2:
        st.subheader("⏰ تنبيهات الدفعات القادمة")
        # دفعات قادمة خلال 5 أيام (غير مدفوعة)
        alert_payment_date = date.today() + pd.Timedelta(days=5)
        upcoming_payments = session.query(Payment).filter(
            Payment.status != 'مدفوع',
            Payment.due_date >= date.today(),
            Payment.due_date <= alert_payment_date
        ).all()
        
        if upcoming_payments:
            for pay in upcoming_payments:
                days_left = (pay.due_date - date.today()).days
                
                # تحديد لون التنبيه حسب الأيام المتبقية
                if days_left == 0:
                    st.error(f"🔴 **اليوم!** دفعة {pay.contract.tenant.name} بمبلغ {pay.total:,.0f} ريال - العقد #{pay.contract_id}")
                elif days_left == 1:
                    st.error(f"🔴 **غداً** دفعة {pay.contract.tenant.name} بمبلغ {pay.total:,.0f} ريال - العقد #{pay.contract_id}")
                elif days_left <= 3:
                    st.warning(f"🟡 **بعد {days_left} أيام** دفعة {pay.contract.tenant.name} بمبلغ {pay.total:,.0f} ريال ({pay.due_date})")
                else:
                    st.info(f"🔵 **بعد {days_left} أيام** دفعة {pay.contract.tenant.name} بمبلغ {pay.total:,.0f} ريال ({pay.due_date})")
        else:
            st.success("✅ لا توجد دفعات مستحقة خلال الأيام القادمة")
    
    # إضافة قسم جديد للعقود القريبة من الانتهاء
    st.markdown("---")
    with st.expander("📋 تنبيهات العقود القريبة من الانتهاء (60 يوم)", expanded=False):
        alert_date = date.today() + pd.Timedelta(days=60)
        expiring = session.query(Contract).filter(
            Contract.end_date <= alert_date, 
            Contract.end_date >= date.today()
        ).all()
        
        if expiring:
            for exp in expiring:
                days_left = (exp.end_date - date.today()).days
                
                if days_left <= 15:
                    st.error(f"🔴 **عاجل!** العقد #{exp.id} للمستأجر **{exp.tenant.name}** ينتهي بعد {days_left} يوم ({exp.end_date})")
                elif days_left <= 30:
                    st.warning(f"🟡 العقد #{exp.id} للمستأجر **{exp.tenant.name}** ينتهي بعد {days_left} يوم ({exp.end_date})")
                else:
                    st.info(f"🔵 العقد #{exp.id} للمستأجر **{exp.tenant.name}** ينتهي بعد {days_left} يوم ({exp.end_date})")
        else:
            st.success("✅ لا توجد عقود قريبة الانتهاء")

def manage_assets():
    st.header("🏢 إدارة الأصول والوحدات")
    
    # تحميل الأصول
    assets = pd.read_sql(session.query(Asset).statement, session.bind)
    
    if assets.empty:
        st.info("لا توجد أصول مُضافة بعد.")
        return
    
    # عرض ملخص سريع للأصول
    st.subheader("📊 ملخص الأصول")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("إجمالي الأصول", len(assets))
    with col2:
        total_units = session.query(Unit).count()
        st.metric("إجمالي الوحدات", total_units)
    with col3:
        rented_units = session.query(Unit).filter(Unit.status == "مؤجر").count()
        st.metric("الوحدات المؤجرة", rented_units)
    
    st.markdown("---")
    
    # عرض الأصول في جدول
    with st.expander("📋 عرض جميع الأصول", expanded=False):
        st.dataframe(
            assets[['name', 'type', 'description']], 
            use_container_width=True,
            hide_index=True
        )
    
    st.markdown("---")
    
    # =========================================================================
    # قسم الإدارة
    # =========================================================================
    if st.session_state['user_role'] == 'Admin':
        st.subheader("⚙️ إدارة الوحدات")
        
        # Tabs لتقسيم الوظائف - المدير فقط
        tab1, tab2 = st.tabs(["✏️ تعديل وحدة موجودة", "➕ إضافة وحدة جديدة"])

        # ===================================================================
        # Tab 1: تعديل وحدة موجودة
        # ===================================================================
        with tab1:
            st.markdown("#### تعديل بيانات أو حالة وحدة")
            
            # اختيار الأصل
            asset_list = session.query(Asset).all()
            asset_names = [a.name for a in asset_list]
            
            if asset_names:
                selected_asset_name = st.selectbox(
                    "🏢 اختر الأصل",
                    asset_names,
                    key='edit_asset_select'
                )
                
                # العثور على الأصل المختار
                selected_asset = None
                for a in asset_list:
                    if a.name == selected_asset_name:
                        selected_asset = a
                        break
                
                if selected_asset:
                    # جلب جميع الوحدات للأصل المحدد
                    all_units = session.query(Unit).filter(
                        Unit.asset_id == selected_asset.id
                    ).all()
                    
                    if all_units:
                        with st.form("edit_unit_form", clear_on_submit=False):
                            # إنشاء قائمة الوحدات
                            unit_labels = []
                            unit_ids = []
                            for u in all_units:
                                label = f"وحدة {u.unit_number} - الدور {u.floor or 'غير محدد'} ({u.usage_type}) - {u.status}"
                                unit_labels.append(label)
                                unit_ids.append(u.id)
                            
                            selected_unit_label = st.selectbox(
                                "🔑 اختر الوحدة المراد تعديلها",
                                unit_labels,
                                key='edit_unit_select'
                            )
                            
                            # العثور على الوحدة المختارة
                            selected_index = unit_labels.index(selected_unit_label)
                            selected_unit_id = unit_ids[selected_index]
                            unit_to_update = session.get(Unit, selected_unit_id)
                            
                            if unit_to_update:
                                st.markdown("---")
                                st.markdown("##### 📝 البيانات الأساسية")
                                
                                col1, col2 = st.columns(2)
                                with col1:
                                    new_floor = st.text_input(
                                        "الدور",
                                        value=unit_to_update.floor if unit_to_update.floor else "",
                                        placeholder="مثال: 1، 2، أرضي"
                                    )
                                    new_usage = st.selectbox(
                                        "نوع الاستخدام",
                                        ["سكني", "تجاري", "حق انتفاع", "سكن عمال"],
                                        index=["سكني", "تجاري", "حق انتفاع", "سكن عمال"].index(unit_to_update.usage_type)
                                    )
                                
                                with col2:
                                    new_area = st.number_input(
                                        "المساحة (م²)",
                                        min_value=0.0,
                                        value=float(unit_to_update.area) if unit_to_update.area else 0.0,
                                        step=0.5
                                    )
                                    new_status = st.selectbox(
                                        "حالة الوحدة",
                                        ["فاضي", "مؤجر", "تحت الصيانة"],
                                        index=["فاضي", "مؤجر", "تحت الصيانة"].index(unit_to_update.status)
                                    )
                                
                                st.markdown("---")
                                
                                submit_edit = st.form_submit_button(
                                    "💾 حفظ التعديلات",
                                    use_container_width=True,
                                    type="primary"
                                )
                                
                                if submit_edit:
                                    unit_to_update.floor = new_floor if new_floor else None
                                    unit_to_update.area = new_area if new_area > 0 else None
                                    unit_to_update.usage_type = new_usage
                                    unit_to_update.status = new_status
                                    session.commit()
                                    st.success(f"✅ تم تحديث الوحدة **{unit_to_update.unit_number}** بنجاح!")
                                    st.rerun()
                    else:
                        st.info("ℹ️ لا توجد وحدات في هذا الأصل حالياً. يمكنك إضافة وحدات جديدة من تبويب 'إضافة وحدة جديدة'.")

        # ===================================================================
        # Tab 2: إضافة وحدة جديدة
        # ===================================================================
        with tab2:
            st.markdown("#### إضافة وحدة جديدة للأصل")
            
            with st.form("add_unit_form", clear_on_submit=True):
                # اختيار الأصل
                asset_list_add = session.query(Asset).all()
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
                    unit_num_new = st.text_input(
                        "رقم/اسم الوحدة *",
                        placeholder="مثال: 101، A1"
                    )
                with col2:
                    floor_new = st.text_input(
                        "الدور",
                        placeholder="مثال: 1، أرضي"
                    )
                with col3:
                    usage_new = st.selectbox(
                        "نوع الاستخدام",
                        ["سكني", "تجاري", "حق انتفاع", "سكن عمال"],
                        key='usage_new'
                    )
                
                area_new = st.number_input(
                    "المساحة (م²) - اختياري",
                    min_value=0.0,
                    value=0.0,
                    step=0.5,
                    key='area_new'
                )
                
                st.markdown("---")
                
                submit_add = st.form_submit_button(
                    "✅ إضافة الوحدة",
                    use_container_width=True,
                    type="primary"
                )
                
                if submit_add:
                    if not unit_num_new.strip():
                        st.error("⚠️ الرجاء إدخال رقم/اسم الوحدة")
                    else:
                        # العثور على الأصل المختار
                        selected_asset_obj = None
                        for a in asset_list_add:
                            if a.name == selected_asset_add:
                                selected_asset_obj = a
                                break
                        
                        if selected_asset_obj:
                            # التحقق من عدم التكرار
                            existing = session.query(Unit).filter(
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
                                session.add(new_unit)
                                session.commit()
                                st.success(f"✅ تم إضافة الوحدة **{unit_num_new}** بنجاح!")
                                st.rerun()

    elif st.session_state['user_role'] == 'Employee':
        st.subheader("➕ إضافة وحدة جديدة")
        st.info("ℹ️ كموظف، يمكنك إضافة وحدات جديدة فقط. للتعديل أو الحذف، تواصل مع المدير.")
        
        # نموذج إضافة مبسط للموظف
        with st.form("add_unit_form_employee", clear_on_submit=True):
            asset_list_add = session.query(Asset).all()
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
                unit_num_new = st.text_input(
                    "رقم/اسم الوحدة *",
                    placeholder="مثال: 101، A1"
                )
            with col2:
                floor_new = st.text_input(
                    "الدور",
                    placeholder="مثال: 1، أرضي"
                )
            with col3:
                usage_new = st.selectbox(
                    "نوع الاستخدام",
                    ["سكني", "تجاري", "حق انتفاع", "سكن عمال"],
                    key='usage_new_emp'
                )
            
            area_new = st.number_input(
                "المساحة (م²) - اختياري",
                min_value=0.0,
                value=0.0,
                step=0.5,
                key='area_new_emp'
            )
            
            st.markdown("---")
            
            submit_add = st.form_submit_button(
                "✅ إضافة الوحدة",
                use_container_width=True,
                type="primary"
            )
            
            if submit_add:
                if not unit_num_new.strip():
                    st.error("⚠️ الرجاء إدخال رقم/اسم الوحدة")
                else:
                    # العثور على الأصل المختار
                    selected_asset_obj = None
                    for a in asset_list_add:
                        if a.name == selected_asset_add:
                            selected_asset_obj = a
                            break
                    
                    if selected_asset_obj:
                        # التحقق من عدم التكرار
                        existing = session.query(Unit).filter(
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
                            session.add(new_unit)
                            session.commit()
                            st.success(f"✅ تم إضافة الوحدة **{unit_num_new}** بنجاح!")
                            st.rerun()
        
        
    
    # =========================================================================
    # قسم عرض تفاصيل الوحدات (للجميع)
    # =========================================================================
    st.markdown("---")
    st.subheader("🔍 عرض تفاصيل الوحدات")
    
    # قائمة الأصول
    view_asset_names = assets['name'].tolist()
    
    if view_asset_names:
        selected_view_asset = st.selectbox(
            "اختر الأصل لعرض وحداته",
            view_asset_names,
            key='view_asset_select'
        )
        
        # العثور على الأصل
        view_asset_id = assets[assets['name'] == selected_view_asset]['id'].values[0]
        
        # جلب الوحدات
        view_units = session.query(Unit).filter(Unit.asset_id == view_asset_id).all()
        
        if view_units:
            # عرض إحصائيات سريعة
            vacant = sum(1 for u in view_units if u.status == 'فاضي')
            rented = sum(1 for u in view_units if u.status == 'مؤجر')
            maintenance = sum(1 for u in view_units if u.status == 'تحت الصيانة')
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("🟢 فارغة", vacant)
            with col2:
                st.metric("🔴 مؤجرة", rented)
            with col3:
                st.metric("🟡 صيانة", maintenance)
            
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
        st.info("لا توجد أصول لعرض وحداتها.")

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
                        # حساب تاريخ النهاية
                        e_date = s_date.replace(year=s_date.year + int(contract_duration))
                        
                        u_ids = ",".join([str(u_options[u]) for u in sel_units])
                        vat = 0.15 if c_type == "تجاري" else 0.0
                        
                        new_c = Contract(
                            contract_number=contract_number.strip(),
                            tenant_id=t_dict[t_name], 
                            contract_type=c_type, 
                            rent_amount=rent,
                            payment_freq=freq, 
                            start_date=s_date, 
                            end_date=e_date,
                            vat_rate=vat, 
                            linked_units_ids=u_ids
                        )
                        session.add(new_c)
                        
                        # تحديث حالة الوحدات إلى مؤجر
                        for u_label in sel_units:
                            uid = u_options[u_label]
                            u_obj = session.get(Unit, uid)
                            u_obj.status = "مؤجر"
                        
                        session.commit()
                        st.success(f"✅ تم إنشاء العقد رقم **{contract_number}** بنجاح! مدة العقد: **{contract_duration} سنة**")
                        st.balloons()
                        st.rerun()
def manage_payments():
    st.header("💰 إدارة الدفعات")
     # تنبيه للموظف
    if st.session_state['user_role'] == 'Employee':
        st.info("ℹ️ كموظف، يمكنك تسجيل الدفعات وتوليدها فقط. لا يمكنك تعديل أو حذف الدفعات الموجودة.")
    
    contracts = session.query(Contract).all()
    c_opts = {f"عقد #{c.contract_number if c.contract_number else c.id} - {c.tenant.name}": c for c in contracts}
    
    if not c_opts:
        st.warning("لا توجد عقود مضافة لتوليد دفعات.")
        return

    sel_c_label = st.selectbox("اختر العقد", list(c_opts.keys()))
    if sel_c_label:
        contract = c_opts[sel_c_label]
        
        # عرض معلومات العقد
        with st.expander("📋 معلومات العقد", expanded=False):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**المستأجر:** {contract.tenant.name}")
                st.write(f"**نوع العقد:** {contract.contract_type}")
            with col2:
                st.write(f"**القيمة السنوية:** {contract.rent_amount:,.0f} ريال")
                st.write(f"**دورية الدفع:** {contract.payment_freq}")
            with col3:
                st.write(f"**من:** {contract.start_date}")
                st.write(f"**إلى:** {contract.end_date}")
        
        # عرض الدفعات
        payments = session.query(Payment).filter_by(contract_id=contract.id).all()
        
        if not payments:
            st.info("ℹ️ لم يتم توليد دفعات لهذا العقد بعد")
            
            if st.button("🔄 توليد الدفعات تلقائياً", type="primary", use_container_width=True):
                # منطق التوليد
                freq_map = {"شهري": 1, "ربع سنوي": 3, "نصف سنوي": 6, "سنوي": 12}
                step = freq_map.get(contract.payment_freq, 12)
                amount_per_pay = contract.rent_amount / (12/step)
                
                curr = contract.start_date
                
                # توليد الدفعات
                # توليد الدفعات
                payments_to_add = []
                payment_counter = 1  # عداد الدفعات يبدأ من 1
                
                while curr < contract.end_date:
                    vat_val = amount_per_pay * contract.vat_rate
                    total_amount = amount_per_pay + vat_val
                    
                    payments_to_add.append(Payment(
                        contract_id=contract.id, 
                        payment_number=payment_counter,  # ← رقم الدفعة
                        due_date=curr, 
                        amount=amount_per_pay,
                        vat=vat_val, 
                        total=total_amount,
                        paid_amount=0.0,
                        remaining_amount=total_amount,
                        status="مستحق", 
                        beneficiary="الجمعية",
                        payment_method=None
                    ))
                    
                    payment_counter += 1  # زيادة العداد
                    
                    # زيادة التاريخ
                    new_month = curr.month + step
                    new_year = curr.year + (new_month - 1) // 12
                    new_month = (new_month - 1) % 12 + 1
                    day_to_use = min(curr.day, 28) 
                    
                    next_date = date(new_year, new_month, day_to_use)
                    if next_date > contract.end_date:
                        break
                        
                    curr = next_date
                    vat_val = amount_per_pay * contract.vat_rate
                    total_amount = amount_per_pay + vat_val
                    
                    payments_to_add.append(Payment(
                        contract_id=contract.id, 
                        due_date=curr, 
                        amount=amount_per_pay,
                        vat=vat_val, 
                        total=total_amount,
                        paid_amount=0.0,
                        remaining_amount=total_amount,
                        status="مستحق", 
                        beneficiary="الجمعية",
                        payment_method=None
                    ))
                    
                    # زيادة التاريخ
                    new_month = curr.month + step
                    new_year = curr.year + (new_month - 1) // 12
                    new_month = (new_month - 1) % 12 + 1
                    day_to_use = min(curr.day, 28) 
                    
                    next_date = date(new_year, new_month, day_to_use)
                    if next_date > contract.end_date:
                        break
                        
                    curr = next_date
                
                session.add_all(payments_to_add)
                session.commit()
                st.success(f"✅ تم توليد {len(payments_to_add)} دفعة بنجاح!")
                st.rerun()
        
        # جدول الدفعات
        if payments:
            st.markdown("---")
            st.subheader("📊 قائمة الدفعات")
            
            # إحصائيات سريعة
            # إحصائيات سريعة
            total_payments = len(payments)
            paid_payments = len([p for p in payments if p.status == "مدفوع"])
            partial_payments = len([p for p in payments if p.status == "مدفوع جزئياً"])
            pending_payments = len([p for p in payments if p.status == "مستحق"])
            
            # حساب المبالغ بشكل صحيح
            total_paid_amount = 0
            total_remaining_amount = 0
            total_contract_amount = 0
            
            for p in payments:
                total_contract_amount += p.total
                
                # التأكد من القيم
                paid = p.paid_amount if p.paid_amount else 0.0
                remaining = p.remaining_amount if p.remaining_amount else (p.total if p.status != 'مدفوع' else 0.0)
                
                # إذا كانت مدفوعة ولكن remaining_amount فارغ، نصفره
                if p.status == 'مدفوع':
                    remaining = 0.0
                    paid = p.total
                
                total_paid_amount += paid
                total_remaining_amount += remaining
            
            col1, col2, col3, col4, col5 = st.columns(5)
            col1.metric("إجمالي الدفعات", total_payments)
            col2.metric("✅ مدفوع كامل", paid_payments)
            col3.metric("🟡 مدفوع جزئياً", partial_payments)
            col4.metric("⏳ مستحق", pending_payments)
            col5.metric("المتبقي الكلي", f"{total_remaining_amount:,.0f} ريال")
            
            # شريط التقدم
            payment_progress = (total_paid_amount / total_contract_amount * 100) if total_contract_amount > 0 else 0
            st.progress(payment_progress / 100)
            st.caption(f"تم سداد {payment_progress:.1f}% من إجمالي قيمة العقد ({total_paid_amount:,.0f} من {total_contract_amount:,.0f} ريال)")
            
            # إنشاء DataFrame للعرض
            # إنشاء DataFrame للعرض
            # إنشاء DataFrame للعرض
            p_data = []
            for p in payments:
                # التأكد من القيم
                paid = p.paid_amount if p.paid_amount else 0.0
                remaining = p.remaining_amount if p.remaining_amount else (p.total if p.status != 'مدفوع' else 0.0)
                
                # تصحيح البيانات إذا كانت الحالة مدفوع
                if p.status == 'مدفوع':
                    paid = p.total
                    remaining = 0.0
                
                # تحديد أيقونة الحالة
                if p.status == "مدفوع":
                    status_icon = "✅"
                elif p.status == "مدفوع جزئياً":
                    status_icon = "🟡"
                elif p.due_date < date.today():
                    status_icon = "🔴"
                else:
                    status_icon = "⏳"
                
                # تحويل تاريخ الدفع لنص لتجنب مشكلة Arrow
                payment_date_str = str(p.paid_date) if p.paid_date else '-'
                
                p_data.append({
                    'رقم الدفعة': p.payment_number if p.payment_number else p.id,  # استخدام payment_number
                    'تاريخ الاستحقاق': str(p.due_date),  # تحويل لنص
                    'المبلغ الكلي': f"{p.total:,.0f}",
                    'المدفوع': f"{paid:,.0f}",
                    'المتبقي': f"{remaining:,.0f}",
                    'الحالة': f"{status_icon} {p.status}",
                    'تاريخ الدفع': payment_date_str,
                    'طريقة الدفع': p.payment_method if p.payment_method else '-'
                })
            
            p_df = pd.DataFrame(p_data)
            st.dataframe(p_df, use_container_width=True, hide_index=True)
            
            # قسم تسجيل السداد
            st.markdown("---")
            st.subheader("💳 تسجيل سداد دفعة")
            
            to_pay = [p for p in payments if p.status != "مدفوع"]
            if to_pay:
                with st.form("payment_form"):
                    # اختيار الدفعة
                    pay_options = {}
                    for p in to_pay:
                        payment_num = p.payment_number if p.payment_number else p.id
                        
                        if p.status == "مدفوع جزئياً":
                            label = f"دفعة #{payment_num} - استحقاق {p.due_date} | المتبقي: {p.remaining_amount:,.0f} ريال (مدفوع جزئياً)"
                        else:
                            label = f"دفعة #{payment_num} - استحقاق {p.due_date} | المطلوب: {p.total:,.0f} ريال"
                        pay_options[label] = p.id
                    
                    selected_pay = st.selectbox(
                        "اختر الدفعة المراد تسجيلها",
                        list(pay_options.keys())
                    )
                    pay_id = pay_options[selected_pay]
                    
                    # جلب الدفعة المختارة
                    selected_payment = session.get(Payment, pay_id)
                    
                    st.markdown("---")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # عرض معلومات الدفعة
                        remaining = selected_payment.remaining_amount if selected_payment.remaining_amount else selected_payment.total
                        paid_before = selected_payment.paid_amount if selected_payment.paid_amount else 0.0
                        
                        st.info(f"""
                        **تفاصيل الدفعة:**
                        - المبلغ الكلي: {selected_payment.total:,.0f} ريال
                        - المدفوع سابقاً: {paid_before:,.0f} ريال
                        - المتبقي: {remaining:,.0f} ريال
                        """)
                        
                        # إدخال المبلغ المدفوع
                        max_amount = float(remaining) if remaining > 0 else float(selected_payment.total)
                        
                        paid_now = st.number_input(
                            "المبلغ المدفوع الآن *",
                            min_value=0.01,
                            max_value=max_amount,
                            value=max_amount,
                            step=100.0,
                            help=f"الحد الأقصى: {max_amount:,.0f} ريال"
                        )
                    
                    with col2:
                        payment_method = st.selectbox(
                            "طريقة الدفع *",
                            ["تحويل بنكي", "منصة إيجار"],
                            help="اختر طريقة الدفع المستخدمة"
                        )
                        
                        payment_date = st.date_input(
                            "تاريخ الدفع",
                            value=date.today(),
                            help="تاريخ استلام المبلغ"
                        )
                    
                    notes = st.text_area(
                        "ملاحظات (اختياري)",
                        placeholder="أي ملاحظات على الدفعة..."
                    )
                    
                    # عرض الحالة الجديدة المتوقعة
                    new_paid_amount = selected_payment.paid_amount + paid_now
                    new_remaining = selected_payment.remaining_amount - paid_now
                    
                    if new_remaining <= 0:
                        expected_status = "✅ مدفوع كامل"
                        status_color = "green"
                    elif new_paid_amount > 0:
                        expected_status = "🟡 مدفوع جزئياً"
                        status_color = "orange"
                    else:
                        expected_status = "⏳ مستحق"
                        status_color = "blue"
                    
                    st.markdown(f"""
                    <div style="background-color: #1E1E1E; padding: 15px; border-radius: 10px; border-left: 5px solid {status_color};">
                        <h4>📊 ملخص بعد الدفع:</h4>
                        <ul>
                            <li>إجمالي المدفوع: <strong>{new_paid_amount:,.0f} ريال</strong></li>
                            <li>المتبقي: <strong>{new_remaining:,.0f} ريال</strong></li>
                            <li>الحالة الجديدة: <strong>{expected_status}</strong></li>
                        </ul>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown("---")
                    
                    col_btn1, col_btn2 = st.columns([3, 1])
                    with col_btn1:
                        submit_payment = st.form_submit_button(
                            "✅ تأكيد السداد",
                            type="primary",
                            use_container_width=True
                        )
                    
                    if submit_payment:
                        if paid_now <= 0:
                            st.error("⚠️ المبلغ المدفوع يجب أن يكون أكبر من صفر")
                        else:
                            # تحديث الدفعة
                            p_obj = session.get(Payment, pay_id)
                            
                            # التأكد من القيم الحالية
                            current_paid = p_obj.paid_amount if p_obj.paid_amount else 0.0
                            current_remaining = p_obj.remaining_amount if p_obj.remaining_amount else p_obj.total
                            
                            # التحقق من عدم تجاوز المتبقي
                            if paid_now > current_remaining:
                                st.error(f"⚠️ المبلغ المدفوع ({paid_now:,.0f}) أكبر من المبلغ المتبقي ({current_remaining:,.0f})")
                            else:
                                # تحديث المبالغ
                                p_obj.paid_amount = current_paid + paid_now
                                p_obj.remaining_amount = current_remaining - paid_now
                                p_obj.paid_date = payment_date
                                p_obj.payment_method = payment_method
                                
                                # تحديد الحالة
                                if p_obj.remaining_amount <= 0.01:
                                    p_obj.status = "مدفوع"
                                    p_obj.remaining_amount = 0
                                    p_obj.paid_amount = p_obj.total
                                else:
                                    p_obj.status = "مدفوع جزئياً"
                                
                                session.commit()
                                session.refresh(p_obj)  # تحديث الكائن من قاعدة البيانات
                                
                                payment_display_num = p_obj.payment_number if p_obj.payment_number else pay_id
                                
                                if p_obj.status == "مدفوع":
                                    st.success(f"✅ تم تسجيل سداد كامل للدفعة #{payment_display_num} بمبلغ {paid_now:,.0f} ريال عبر {payment_method}")
                                    st.balloons()
                                else:
                                    st.success(f"🟡 تم تسجيل سداد جزئي للدفعة #{payment_display_num} بمبلغ {paid_now:,.0f} ريال. المتبقي: {new_remaining:,.0f} ريال")
                                st.rerun()
            else:
                st.success("✅ تم سداد جميع الدفعات لهذا العقد بالكامل!")

def get_csv_download_link(df, filename, label):
    # دالة مساعدة لتحميل البيانات إلى CSV
    csv = df.to_csv(index=False, encoding='utf-8-sig')
    b64 = base64.b64encode(csv.encode()).decode()  
    href = f'<a href="data:file/csv;charset=utf-8-sig;base64,{b64}" download="{filename}">{label}</a>'
    return href

def reports_page():
    st.header("📑 التقارير الرسمية")
    
    rtype = st.radio("اختر التقرير", ["تقرير مالي شامل", "تقرير المستأجر التفصيلي", "المتأخرات"], horizontal=True)
    
    if rtype == "تقرير مالي شامل":
        st.markdown("#### 🔍 فلترة التقرير")
        
        # الفلاتر
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # فلتر الأصول
            all_assets = session.query(Asset).all()
            asset_options = ["الكل"] + [a.name for a in all_assets]
            selected_asset = st.selectbox("اختر الأصل", asset_options, key="report_asset_filter")
        
        with col2:
            # فلتر الوحدات (بناءً على الأصل المختار)
            if selected_asset != "الكل":
                selected_asset_obj = session.query(Asset).filter_by(name=selected_asset).first()
                if selected_asset_obj:
                    units_in_asset = session.query(Unit).filter_by(asset_id=selected_asset_obj.id).all()
                    unit_options = ["الكل"] + [u.unit_number for u in units_in_asset]
                    selected_unit = st.selectbox("اختر الوحدة", unit_options, key="report_unit_filter")
                else:
                    selected_unit = "الكل"
            else:
                selected_unit = "الكل"
                st.selectbox("اختر الوحدة", ["الكل (اختر أصل أولاً)"], disabled=True, key="report_unit_disabled")
        
        with col3:
            # فلتر الحالة
            status_options = ["الكل", "مدفوع", "مدفوع جزئياً", "مستحق"]
            selected_status = st.selectbox("حالة الدفعة", status_options, key="report_status_filter")
        
        st.markdown("---")
        
        # بناء الاستعلام مع الفلاتر
        query = session.query(
            Payment.id.label("رقم الدفعة"), 
            Contract.contract_number.label("رقم العقد"),
            Tenant.name.label("المستأجر"),
            Payment.due_date.label("تاريخ الاستحقاق"), 
            Payment.total.label("المبلغ الإجمالي"),
            Payment.paid_amount.label("المبلغ المدفوع"),
            Payment.remaining_amount.label("المتبقي"),
            Payment.status.label("الحالة"), 
            Payment.beneficiary.label("المستفيد")
        ).select_from(Payment).join(Contract).join(Tenant)
        
        # تطبيق الفلاتر
        if selected_asset != "الكل":
            # الحصول على IDs الوحدات في الأصل المختار
            asset_obj = session.query(Asset).filter_by(name=selected_asset).first()
            if asset_obj:
                if selected_unit != "الكل":
                    # وحدة محددة
                    unit_obj = session.query(Unit).filter_by(
                        asset_id=asset_obj.id,
                        unit_number=selected_unit
                    ).first()
                    if unit_obj:
                        # البحث عن العقود المرتبطة بهذه الوحدة
                        query = query.filter(Contract.linked_units_ids.like(f"%{unit_obj.id}%"))
                else:
                    # كل الوحدات في الأصل
                    units_ids = [u.id for u in session.query(Unit).filter_by(asset_id=asset_obj.id).all()]
                    if units_ids:
                        # البحث عن العقود المرتبطة بأي وحدة في هذا الأصل
                        filters = [Contract.linked_units_ids.like(f"%{uid}%") for uid in units_ids]
                        from sqlalchemy import or_
                        query = query.filter(or_(*filters))
        
        if selected_status != "الكل":
            query = query.filter(Payment.status == selected_status)
        
        df = pd.read_sql(query.statement, session.bind)
        
        if not df.empty:
            # عرض الإحصائيات
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            with col_stat1:
                st.metric("إجمالي الدفعات", len(df))
            with col_stat2:
                total_amount = df["المبلغ الإجمالي"].sum()
                st.metric("إجمالي المبلغ", f"{total_amount:,.0f} ريال")
            with col_stat3:
                total_remaining = df["المتبقي"].sum() if "المتبقي" in df.columns else 0
                st.metric("إجمالي المتبقي", f"{total_remaining:,.0f} ريال")
            
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            csv_data = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                "⬇️ تحميل CSV للتقرير الشامل", 
                csv_data, 
                f"financial_report_{selected_asset}_{selected_unit}.csv", 
                "text/csv"
            )
        else:
            st.info("لا توجد بيانات تطابق الفلاتر المحددة")

    elif rtype == "المتأخرات":
        query = session.query(
            Tenant.name.label("المستأجر"), Tenant.phone.label("هاتف المستأجر"), Payment.due_date.label("تاريخ الاستحقاق"), Payment.total.label("المبلغ المتأخر")
        ).select_from(Payment).join(Contract).join(Tenant).filter(Payment.status != 'مدفوع', Payment.due_date < date.today())
        
        df = pd.read_sql(query.statement, session.bind)
        if not df.empty:
            st.error(f"إجمالي المتأخرات: {df['المبلغ المتأخر'].sum():,.2f} ريال")
            st.dataframe(df)
            csv_data = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("⬇️ تحميل CSV لتقرير المتأخرات", csv_data, "overdue_report.csv", "text/csv")
        else:
            st.success("لا توجد متأخرات")

    elif rtype == "تقرير المستأجر التفصيلي":
        tenants = session.query(Tenant).all()
        t_sel = st.selectbox("اختر المستأجر", [t.name for t in tenants])
        
        if t_sel:
            t_obj = session.query(Tenant).filter_by(name=t_sel).first()
            st.markdown(f"### 👤 {t_obj.name}")
            st.text(f"النوع: {t_obj.type} | الهاتف: {t_obj.phone}")
            
            all_payments_data = [] 
            
            # عقود المستأجر
            contracts = session.query(Contract).filter_by(tenant_id=t_obj.id).all()
            for c in contracts:
                with st.expander(f"عقد رقم {c.id} ({c.contract_type}) - يبدأ {c.start_date}"):
                    # الوحدات
                    u_ids = c.linked_units_ids.split(',') if c.linked_units_ids else []
                    if u_ids:
                        u_names = []
                        for uid in u_ids:
                            u = session.get(Unit, int(uid))
                            if u: u_names.append(f"{u.unit_number} ({u.asset.name})")
                        st.write(f"**الوحدات:** {', '.join(u_names)}")
                    
                    # ملخص مالي للعقد
                    pays_query = session.query(Payment).filter_by(contract_id=c.id)
                    pays = pays_query.all()
                    
                    paid = sum([p.total for p in pays if p.status=='مدفوع'])
                    remaining = sum([p.total for p in pays if p.status!='مدفوع'])
                    
                    c1, c2 = st.columns(2)
                    c1.metric("مدفوع", f"{paid:,.2f}")
                    c2.metric("متبقي/متأخر", f"{remaining:,.2f}")
                    
                    # جدول الدفعات
                    p_data_df = pd.DataFrame([{
                        'رقم العقد': c.id,
                        'تاريخ الاستحقاق': p.due_date, 
                        'المبلغ الإجمالي': p.total, 
                        'المبلغ (بدون VAT)': p.amount,
                        'VAT': p.vat,
                        'تاريخ الدفع': p.paid_date,
                        'الحالة': p.status
                    } for p in pays])
                    st.dataframe(p_data_df)
                    
                    all_payments_data.append(p_data_df)
            
            st.markdown("---")
            # --- زر التحميل لملف اكسل (CSV) ---
            if all_payments_data:
                combined_df = pd.concat(all_payments_data, ignore_index=True)
                csv_data = combined_df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label=f"⬇️ تحميل تقرير الدفعات لـ {t_sel} (CSV)",
                    data=csv_data,
                    file_name=f"تقرير_دفعات_{t_sel}.csv",
                    mime="text/csv"
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



def manage_tenants():
    st.header("👥 إدارة المستأجرين")
    
    # عرض ملخص سريع
    st.subheader("📊 ملخص المستأجرين")
    total_tenants = session.query(Tenant).count()
    active_contracts = session.query(Contract).filter(Contract.end_date >= date.today()).count()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("إجمالي المستأجرين", total_tenants)
    with col2:
        st.metric("العقود النشطة", active_contracts)
    with col3:
        # حساب المستأجرين بدون عقود
        tenants_with_contracts = session.query(Contract.tenant_id).distinct().count()
        st.metric("مستأجرين بدون عقود", total_tenants - tenants_with_contracts)
    
    st.markdown("---")
    
    # =========================================================================
    # قسم الإدارة (للمسؤولين فقط)
    # =========================================================================
    if st.session_state['user_role'] == 'Admin':
        st.subheader("⚙️ إدارة بيانات المستأجرين")
        
        tab1, tab2 = st.tabs(["✏️ تعديل/عرض مستأجر", "➕ إضافة مستأجر جديد"])
        
        # ===================================================================
        # Tab 1: تعديل/عرض مستأجر موجود
        # ===================================================================
        with tab1:
            st.markdown("#### تعديل أو عرض بيانات مستأجر")
            
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
                        # جلب أسماء الوحدات
                        unit_names = []
                        if c.linked_units_ids:
                            for uid in c.linked_units_ids.split(','):
                                u = session.get(Unit, int(uid))
                                if u:
                                    unit_names.append(f"{u.unit_number} ({u.asset.name})")
                        
                        contracts_data.append({
                            'رقم العقد': c.id,
                            'النوع': c.contract_type,
                            'القيمة السنوية': f"{c.rent_amount:,.0f}",
                            'الوحدات': ', '.join(unit_names) if unit_names else '-',
                            'تاريخ البداية': c.start_date,
                            'تاريخ النهاية': c.end_date
                        })
                    
                    contracts_df = pd.DataFrame(contracts_data)
                    st.dataframe(contracts_df, use_container_width=True, hide_index=True)
                else:
                    st.info("لا توجد عقود مرتبطة بهذا المستأجر")
                
                st.markdown("---")
                
                # نموذج التعديل
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
                    
                    col_btn1, col_btn2 = st.columns([3, 1])
                    with col_btn1:
                        submit_edit = st.form_submit_button(
                            "💾 حفظ التعديلات",
                            use_container_width=True,
                            type="primary"
                        )
                    with col_btn2:
                        delete_tenant = st.form_submit_button(
                            "🗑️ حذف",
                            use_container_width=True
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
                    
                    if delete_tenant:
                        # التحقق من وجود عقود مرتبطة
                        if tenant_contracts:
                            st.error("⚠️ لا يمكن حذف المستأجر لأنه مرتبط بعقود. يرجى حذف العقود أولاً.")
                        else:
                            session.delete(selected_tenant)
                            session.commit()
                            st.success(f"✅ تم حذف المستأجر **{selected_tenant.name}** بنجاح!")
                            st.rerun()
            else:
                st.info("لا يوجد مستأجرين مسجلين حالياً")
        
        # ===================================================================
        # Tab 2: إضافة مستأجر جديد
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
                        # التحقق من عدم التكرار
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
                            st.rerun()
    
    # =========================================================================
    # قسم عرض قائمة المستأجرين (للجميع)
    # =========================================================================
    st.markdown("---")
    st.subheader("📋 قائمة المستأجرين")
    
    all_tenants = session.query(Tenant).all()
    
    if all_tenants:
        # إنشاء DataFrame للعرض
        tenants_display = []
        for t in all_tenants:
            # عدد العقود
            contracts_count = session.query(Contract).filter_by(tenant_id=t.id).count()
            
            # حالة العقود
            active_contracts = session.query(Contract).filter(
                Contract.tenant_id == t.id,
                Contract.end_date >= date.today()
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
        
        # إضافة خيار بحث
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
        
        # إحصائيات سريعة
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
# ==========================================
# 5. التحكم في التنقل والصفحة الرئيسية
# ==========================================

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
                    "إدارة الأصول والوحدات": manage_assets,
                    "إدارة المستأجرين": manage_tenants,
                    "إدارة العقود": manage_contracts,
                    "إدارة الدفعات": manage_payments,
                    "التقارير": reports_page,
                    "الإعدادات": settings_page
                }
            else: # Employee role
                pages = {
                    "لوحة المؤشرات": dashboard,
                    "إدارة الأصول والوحدات": manage_assets,
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