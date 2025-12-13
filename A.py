import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, ForeignKey, Text
from sqlalchemy.orm import sessionmaker, declarative_base, relationship
from datetime import date, datetime
import hashlib
import io
import base64

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
    /* الخط العام */
    body {direction: rtl; text-align: right;}
    h1, h2, h3, h4, h5 {text-align: right; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;}
    .reportview-container .main .block-container {max-width: 95%;}
    
    /* تكبير حجم الخط في النص العادي والجداول */
    html, body, .stText, .stMarkdown, .dataframe, .stTable {
        font-size: 16px; 
    }
    
    /* تكبير المدخلات والأزرار */
    .stTextInput>div>div>input, .stSelectbox>div>div, .stButton>button {
        font-size: 16px;
        padding: 10px;
    }

    /* *** التعديل الجديد: تحسين الشريط الجانبي بالكامل *** */
    div[data-testid="stSidebar"] {
        text-align: right; 
        font-size: 18px; /* حجم خط إجمالي أكبر */
    }
    
    /* تكبير خط عنوان القائمة الجانبية */
    div[data-testid="stSidebar"] .st-emotion-cache-1215bdr h1 {
        font-size: 24px !important; /* حجم كبير للعنوان "القائمة الرئيسية" */
    }

    /* تكبير خط بيانات المستخدم */
    div[data-testid="stSidebar"] .st-emotion-cache-1cypcdb {
        font-size: 18px !important; /* حجم أكبر لـ "المستخدم: admin (Admin)" */
        margin-bottom: 15px;
    }

    /* تكبير الخط والتباعد بين خيارات الصفحات */
    .stRadio > label {
        font-size: 18px !important; 
        padding: 8px 0 !important;
        margin-bottom: 5px; 
    }
    
    /* مقاييس الأداء */
    div[data-testid="stMetricValue"] {text-align: right; font-size: 24px !important;}
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. قاعدة البيانات والنماذج
# ==========================================
Base = declarative_base()
engine = create_engine('sqlite:///real_estate_v2.db', connect_args={'check_same_thread': False})
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

class Contract(Base):
    __tablename__ = 'contracts'
    id = Column(Integer, primary_key=True)
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
    due_date = Column(Date)
    paid_date = Column(Date, nullable=True)
    amount = Column(Float)
    vat = Column(Float)
    total = Column(Float)
    status = Column(String)
    beneficiary = Column(String)
    contract = relationship("Contract")

Base.metadata.create_all(engine)

# ==========================================
# 3. دوال مساعدة والبيانات الأولية (Seed Data)
# ==========================================
def hash_password(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_login(username, password):
    user = session.query(User).filter_by(username=username).first()
    if user and user.password_hash == hash_password(password):
        return user
    return None

def init_seed_data():
    """تهيئة البيانات المطلوبة عند التشغيل الأول"""
    if not session.query(User).first():
        # 1. المستخدمين
        admin = User(username="admin", password_hash=hash_password("admin123"), role="Admin")
        emp = User(username="emp", password_hash=hash_password("emp123"), role="Employee")
        session.add_all([admin, emp])

        # 2. المستأجرين (حسب الطلب)
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

        # 3. الأصول (العمارات، الأراضي، المستودعات)
        assets_list = []
        
        # العمارات
        b1 = Asset(name="عمارة 1", type="عمارة", description="5 أدوار – ميزانين – ملحق – معارض")
        b2 = Asset(name="عمارة 2", type="عمارة", description="5 أدوار + ملحق")
        b3 = Asset(name="عمارة 3", type="عمارة", description="3 أدوار – 6 شقق لكل دور + ملحق (تسلسل 311-336)")
        b4 = Asset(name="عمارة 4", type="عمارة", description="3 أدوار – الدور الأول مؤجر بالكامل (تسلسل 401-436)")
        
        # المستودعات
        w1 = Asset(name="مستودع 1", type="مستودع", description="تجاري / مؤجر")
        w2 = Asset(name="مستودع 2", type="مستودع", description="تجاري / مؤجر")
        
        # الأراضي والمحطات
        l1 = Asset(name="أرض شارع حراء (محطة)", type="محطة وقود", location="شارع حراء", description="2500م – محطة")
        l2 = Asset(name="أرض الميزانين", type="أرض", description="1500م – حق انتفاع")
        l3 = Asset(name="أرض كيلو 14", type="أرض", location="كيلو 14", description="12000م – غير مستغلة")
        
        assets_list.extend([b1, b2, b3, b4, w1, w2, l1, l2, l3])
        session.add_all(assets_list)
        session.commit()

        # 4. الوحدات (Units Generation)
        units_list = []

        # --- عمارة 1 (5 أدوار، ميزانين، معارض، ملحق) ---
        # معارض
        for i in range(1, 4):
            units_list.append(Unit(asset_id=b1.id, unit_number=f"100-{i} (معرض)", floor="أرضي", usage_type="تجاري"))
        # ميزانين
        units_list.append(Unit(asset_id=b1.id, unit_number="100-ميزانين", floor="ميزانين", usage_type="تجاري"))
        # شقق (الدور 1 إلى 5) - نفترض شقتين في الدور
        for f in range(1, 6):
            units_list.append(Unit(asset_id=b1.id, unit_number=f"10{f}A", floor=str(f), usage_type="سكني"))
            units_list.append(Unit(asset_id=b1.id, unit_number=f"10{f}B", floor=str(f), usage_type="سكني"))
        # ملحق
        units_list.append(Unit(asset_id=b1.id, unit_number="10-ملحق", floor="سطح", usage_type="سكن عمال"))

        # --- عمارة 2 (5 أدوار + ملحق) ---
        # معارض (كما في الصورة)
        for i in range(1, 4):
            units_list.append(Unit(asset_id=b2.id, unit_number=f"200-{i} (معرض)", floor="أرضي", usage_type="تجاري"))
        # شقق (الدور 1 إلى 5)
        for f in range(1, 6):
            units_list.append(Unit(asset_id=b2.id, unit_number=f"20{f}-1", floor=str(f), usage_type="سكني"))
            units_list.append(Unit(asset_id=b2.id, unit_number=f"20{f}-2", floor=str(f), usage_type="سكني"))
        units_list.append(Unit(asset_id=b2.id, unit_number="20-ملحق", floor="سطح", usage_type="سكني"))

        # --- عمارة 3 (3 أدوار - 6 شقق لكل دور + ملحق) ---
        # شقق 311 -> 336
        counter = 311
        for f in range(1, 4):
            for _ in range(8): # 8 شقق بالدور لتغطية 24 شقة (336-311=25)
                if counter <= 336:
                    units_list.append(Unit(asset_id=b3.id, unit_number=str(counter), floor=str(f), usage_type="سكني"))
                    counter += 1
                else: break
        units_list.append(Unit(asset_id=b3.id, unit_number="30-ملحق", floor="سطح", usage_type="سكني"))

        # --- عمارة 4 (3 أدوار - الدور الأول مؤجر بالكامل) ---
        # شقق 401 -> 436 (تقريباً 12 شقة في كل دور)
        counter_4 = 401
        for f in range(1, 4):
            status = "مؤجر" if f == 1 else "فاضي" 
            
            # إنشاء 12 شقة لكل دور (لتغطية 36 رقم)
            for _ in range(12): 
                if counter_4 <= 436:
                    units_list.append(Unit(asset_id=b4.id, unit_number=str(counter_4), floor=str(f), usage_type="سكني", status=status))
                    counter_4 += 1
                else: break
        
        # لتغطية الوصف "الدور الأول مؤجر بالكامل" لوحدة واحدة
        units_list.append(Unit(asset_id=b4.id, unit_number="40-الدور الأول (إجمالي)", floor="1", usage_type="تجاري/سكني", status="مؤجر"))


        # --- المستودعات والأراضي ---
        units_list.append(Unit(asset_id=w1.id, unit_number="مستودع رئيسي 1", usage_type="تجاري", status="مؤجر"))
        units_list.append(Unit(asset_id=w2.id, unit_number="مستودع رئيسي 2", usage_type="تجاري", status="مؤجر"))
        units_list.append(Unit(asset_id=l1.id, unit_number="أرض المحطة", area=2500, usage_type="تجاري"))
        units_list.append(Unit(asset_id=l2.id, unit_number="أرض حق انتفاع", area=1500, usage_type="حق انتفاع"))

        session.add_all(units_list)
        session.commit()

init_seed_data()
# ==========================================
# 4. مكونات الواجهة
# ==========================================

def login_page():
    st.markdown("## 🔐 تسجيل الدخول")
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        username = st.text_input("اسم المستخدم")
        password = st.text_input("كلمة المرور", type="password")
        if st.button("دخول"):
            user = check_login(username, password)
            if user:
                st.session_state['logged_in'] = True
                st.session_state['user_role'] = user.role
                st.session_state['username'] = user.username
                st.rerun()
            else:
                st.error("خطأ في البيانات")
        st.info("حسابات تجريبية: admin/admin123 | emp/emp123")

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
    with col_chart1:
        st.subheader("توزيع حالة الوحدات")
        status_df = pd.DataFrame({'الحالة': ['مؤجر', 'فاضي'], 'العدد': [rented_units, empty_units]})
        st.bar_chart(status_df.set_index('الحالة'))
    
    with col_chart2:
        st.subheader("تنبيهات العقود")
        # عقود تنتهي خلال 60 يوم
        alert_date = date.today() + pd.Timedelta(days=60)
        expiring = session.query(Contract).filter(Contract.end_date <= alert_date, Contract.end_date >= date.today()).all()
        if expiring:
            for exp in expiring:
                st.warning(f"العقد {exp.id} للمستأجر {exp.tenant.name} ينتهي في {exp.end_date}")
        else:
            st.success("لا توجد عقود قريبة الانتهاء")

    st.markdown("---")
    
    # --- الرسم البياني الجديد ---
    st.subheader("مقارنة الدفعات المتأخرة حسب المستفيد")
    if overdue_payments:
        overdue_df = pd.DataFrame([{'المبلغ': p.total, 'المستفيد': p.beneficiary} for p in overdue_payments])
        
        # تجميع حسب المستفيد
        beneficiary_summary = overdue_df.groupby('المستفيد')['المبلغ'].sum().reset_index()
        beneficiary_summary.columns = ['المستفيد', 'إجمالي المتأخرات']
        
        st.bar_chart(beneficiary_summary.set_index('المستفيد'), use_container_width=True)
    else:
        st.info("لا توجد دفعات متأخرة حالياً لعرض هذا التقرير.")

def manage_assets():
    st.header("🏢 الأصول والوحدات")
    assets = pd.read_sql(session.query(Asset).statement, session.bind)
    st.dataframe(assets[['name', 'type', 'description']], use_container_width=True)
    
    # --- إضافة واجهة إضافة وحدات جديدة (للمدير فقط) ---
    if st.session_state['user_role'] == 'Admin':
        st.subheader("➕ إضافة وحدة جديدة")
        with st.form("add_new_unit"):
            c1, c2, c3 = st.columns(3)
            asset_opts = {a.name: a.id for a in session.query(Asset).all()}
            selected_asset_name = c1.selectbox("اختر الأصل", list(asset_opts.keys()))
            
            unit_num = c2.text_input("رقم/اسم الوحدة")
            usage = c3.selectbox("نوع الاستخدام", ["سكني", "تجاري", "حق انتفاع", "سكن عمال"])
            
            c4, c5 = st.columns(2)
            floor = c4.text_input("الدور (مثال: أرضي، 1، ميزانين)")
            area = c5.number_input("المساحة (متر مربع - اختياري)", min_value=0.0, value=0.0)
            
            submitted = st.form_submit_button("حفظ الوحدة")
            
            if submitted:
                asset_id = asset_opts[selected_asset_name]
                new_unit = Unit(
                    asset_id=asset_id,
                    unit_number=unit_num,
                    usage_type=usage,
                    floor=floor,
                    area=area if area > 0 else None,
                    status="فاضي"
                )
                session.add(new_unit)
                session.commit()
                st.success(f"تم إضافة الوحدة **{unit_num}** للأصل **{selected_asset_name}** بنجاح.")
                st.rerun()
    
    st.markdown("---")
    
    st.subheader("تفاصيل الوحدات")
    if not assets.empty:
        selected_asset = st.selectbox("اختر الأصل لعرض وحداته", assets['name'].unique())
        asset_id = assets[assets['name'] == selected_asset]['id'].values[0]
        
        units = pd.read_sql(session.query(Unit).filter_by(asset_id=asset_id).statement, session.bind)
        st.dataframe(units[['unit_number', 'floor', 'usage_type', 'status', 'area']], use_container_width=True)
    else:
         st.info("لا توجد أصول مُضافة بعد.")

def manage_contracts():
    st.header("📄 إدارة العقود")
    if st.session_state['user_role'] == 'Admin':
        with st.expander("إنشاء عقد جديد"):
            with st.form("new_contract"):
                tenants = session.query(Tenant).all()
                t_dict = {t.name: t.id for t in tenants}
                
                # وحدات غير مؤجرة
                free_units = session.query(Unit).filter_by(status='فاضي').all()
                u_options = {f"{u.unit_number} ({u.asset.name})": u.id for u in free_units}
                
                c1, c2 = st.columns(2)
                t_name = c1.selectbox("المستأجر", list(t_dict.keys()))
                c_type = c2.selectbox("نوع العقد", ["سكني", "تجاري", "حق انتفاع"])
                
                sel_units = st.multiselect("اختر الوحدات", list(u_options.keys()))
                
                r1, r2, r3 = st.columns(3)
                rent = r1.number_input("القيمة السنوية", min_value=0.0)
                freq = r2.selectbox("الدفع", ["سنوي", "نصف سنوي", "ربع سنوي", "شهري"])
                s_date = r3.date_input("تاريخ البداية")
                
                submitted = st.form_submit_button("حفظ العقد")
                if submitted and sel_units:
                    e_date = s_date.replace(year=s_date.year + 1) # افتراضي سنة
                    u_ids = ",".join([str(u_options[u]) for u in sel_units])
                    vat = 0.15 if c_type == "تجاري" else 0.0
                    
                    new_c = Contract(
                        tenant_id=t_dict[t_name], contract_type=c_type, rent_amount=rent,
                        payment_freq=freq, start_date=s_date, end_date=e_date,
                        vat_rate=vat, linked_units_ids=u_ids
                    )
                    session.add(new_c)
                    
                    # تحديث الوحدات
                    for u_label in sel_units:
                        uid = u_options[u_label]
                        u_obj = session.query(Unit).get(uid)
                        u_obj.status = "مؤجر"
                    
                    session.commit()
                    st.success("تم إنشاء العقد")
                    st.rerun()

    # عرض العقود
    contracts = pd.read_sql(session.query(Contract).statement, session.bind)
    if not contracts.empty:
        # تحسين العرض بدمج اسم المستأجر
        t_names = dict(session.query(Tenant.id, Tenant.name).all())
        contracts['المستأجر'] = contracts['tenant_id'].map(t_names)
        st.dataframe(contracts[['id', 'المستأجر', 'contract_type', 'rent_amount', 'start_date', 'end_date']], use_container_width=True)


def manage_payments():
    st.header("💰 الدفعات (القواعد الخاصة)")
    
    st.info("💡 قاعدة محطة الوقود: الإيرادات قبل 1/8 للجمعية، وبعد 1/8 للمستثمر.")
    
    contracts = session.query(Contract).all()
    c_opts = {f"عقد #{c.id} - {c.tenant.name}": c for c in contracts}
    
    sel_c_label = st.selectbox("اختر العقد", list(c_opts.keys()))
    if sel_c_label:
        contract = c_opts[sel_c_label]
        
        # عرض الدفعات
        payments = session.query(Payment).filter_by(contract_id=contract.id).all()
        
        if not payments:
            if st.button("توليد الدفعات (تلقائي)"):
                # تحديد نوع الأصل لتطبيق قاعدة المحطة
                u_ids = contract.linked_units_ids.split(',') if contract.linked_units_ids else []
                is_gas_station = False
                if u_ids:
                    first_unit = session.query(Unit).get(int(u_ids[0]))
                    if first_unit and first_unit.asset.type == "محطة وقود":
                        is_gas_station = True
                
                # منطق التوليد
                freq_map = {"شهري": 1, "ربع سنوي": 3, "نصف سنوي": 6, "سنوي": 12}
                step = freq_map.get(contract.payment_freq, 12)
                amount_per_pay = contract.rent_amount / (12/step)
                
                curr = contract.start_date
                while curr < contract.end_date:
                    # تطبيق الشرط الخاص بالمحطة
                    beneficiary = "الجمعية"
                    if is_gas_station:
                        cutoff = date(curr.year, 8, 1) # الأول من أغسطس
                        # نفترض السنة الحالية أو سنة العقد، هنا نقارن الشهر واليوم بشكل مبسط
                        # إذا كان التاريخ الحالي للدفع >= 1/8 في أي سنة
                        if (curr.month > 8) or (curr.month == 8 and curr.day >= 1):
                            beneficiary = "المستثمر"
                    
                    vat_val = amount_per_pay * contract.vat_rate
                    
                    p = Payment(
                        contract_id=contract.id, due_date=curr, amount=amount_per_pay,
                        vat=vat_val, total=amount_per_pay + vat_val,
                        status="مستحق", beneficiary=beneficiary
                    )
                    session.add(p)
                    
                    # زيادة التاريخ
                    new_month = curr.month + step
                    new_year = curr.year + (new_month - 1) // 12
                    new_month = (new_month - 1) % 12 + 1
                    curr = date(new_year, new_month, min(curr.day, 28))
                
                session.commit()
                st.success("تم توليد الدفعات حسب القواعد")
                st.rerun()
        
        # جدول الدفعات
        if payments:
            p_df = pd.DataFrame([{
                'ID': p.id, 'تاريخ الاستحقاق': p.due_date, 'المبلغ': p.total,
                'المستفيد': p.beneficiary, 'الحالة': p.status
            } for p in payments])
            
            # تلوين المستفيد للتمييز
            def highlight_beneficiary(val):
                color = '#d4edda' if val == 'المستثمر' else ''
                return f'background-color: {color}'
            
            st.dataframe(p_df.style.applymap(highlight_beneficiary, subset=['المستفيد']), use_container_width=True)
            
            # سداد
            to_pay = [p for p in payments if p.status != "مدفوع"]
            if to_pay:
                pay_id = st.selectbox("تسجيل سداد دفعة رقم", [p.id for p in to_pay])
                if st.button("تأكيد السداد"):
                    p_obj = session.query(Payment).get(pay_id)
                    p_obj.status = "مدفوع"
                    p_obj.paid_date = date.today()
                    session.commit()
                    st.success("تم الحفظ")
                    st.rerun()

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
        query = session.query(
            Payment.id.label("رقم الدفعة"), Contract.id.label("رقم العقد"), Tenant.name.label("المستأجر"),
            Payment.due_date.label("تاريخ الاستحقاق"), Payment.total.label("المبلغ الإجمالي"), Payment.status.label("الحالة"), Payment.beneficiary.label("المستفيد")
        ).select_from(Payment).join(Contract).join(Tenant)
        
        df = pd.read_sql(query.statement, session.bind)
        st.dataframe(df, use_container_width=True)
        
        csv_data = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("⬇️ تحميل CSV للتقرير الشامل", csv_data, "financial_report.csv", "text/csv")

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
                            u = session.query(Unit).get(int(uid))
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
                            st.session_state['username'] = new_username # تحديث الحالة الجلسة إذا كان هو المستخدم الحالي

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
                        if new_username != user_to_edit_name:
                             st.info("سيتم تسجيل خروجك لإكمال التحديث.")
                        st.rerun()

    else:
        st.warning("ليس لديك صلاحية الوصول إلى هذه الإعدادات.")

# ==========================================
# 5. التشغيل الرئيسي (main)
# ==========================================
def main():
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    
    if not st.session_state['logged_in']:
        login_page()
    else:
        user_role = st.session_state['user_role']
        
        # 1. تحديد خيارات القائمة حسب الدور
        if user_role == 'Admin':
            menu_options = [
                "لوحة التحكم", 
                "الأصول والوحدات", 
                "إدارة المستأجرين", 
                "العقود", 
                "الدفعات المالية", 
                "التقارير", 
                "الإعدادات"
            ]
        elif user_role == 'Employee':
            # تقييد الموظف بالصلاحيات المطلوبة فقط
            menu_options = [
                "لوحة التحكم", 
                "الأصول والوحدات", 
                "إدارة المستأجرين"
            ]
        else:
             menu_options = ["لوحة التحكم"] # حالة افتراضية
        
        with st.sidebar:
            st.title("القائمة الرئيسية")
            st.write(f"المستخدم: {st.session_state['username']} ({user_role})")
            
            # عرض القائمة المفلترة
            page = st.radio("الذهاب إلى", menu_options)
            
            if st.button("تسجيل خروج"):
                st.session_state['logged_in'] = False
                st.rerun()
        
        # 2. توجيه المستخدم للصفحة المختارة
        if page == "لوحة التحكم": dashboard()
        elif page == "الأصول والوحدات": manage_assets()
        elif page == "إدارة المستأجرين": 
            st.header("إدارة المستأجرين")
            df = pd.read_sql(session.query(Tenant).statement, session.bind)
            st.dataframe(df, use_container_width=True)
            # إضافة المستأجرين متاحة للمدير فقط
            if user_role == 'Admin':
                with st.expander("إضافة مستأجر"):
                    with st.form("add_t"):
                        name = st.text_input("الاسم")
                        ttype = st.text_input("النوع")
                        phone = st.text_input("الهاتف")
                        if st.form_submit_button("حفظ"):
                            session.add(Tenant(name=name, type=ttype, phone=phone))
                            session.commit()
                            st.rerun()
        # هذه الصفحات لن تظهر للموظف الآن
        elif page == "العقود": manage_contracts()
        elif page == "الدفعات المالية": manage_payments()
        elif page == "التقارير": reports_page()
        elif page == "الإعدادات": settings_page()

if __name__ == '__main__':
    main()