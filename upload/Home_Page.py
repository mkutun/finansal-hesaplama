import streamlit as st
import os
import json
from dotenv import load_dotenv
import bcrypt

# --- Sayfa Ayarları ---
st.set_page_config(
    page_title="Finansal Dashboard'um",
    page_icon="📊", # Finans için güzel bir ikon
    layout="wide"
)

# --- Ortam Değişkenlerini Yükle ---
# admin.env dosyasının Home_Page.py ile aynı dizinde olduğunu varsayıyoruz
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), 'admin.env'))

SECRET_KEY = os.getenv('SECRET_KEY')

# Kullanıcı veritabanı dosyasının yolu
USERS_FILE = os.path.join(os.path.dirname(__file__), 'users.json')
LOG_FILE = os.path.join(os.path.dirname(__file__), 'user_activity.log') # Kullanıcı aktivite log dosyası

# Kullanıcıları yükle veya boş bir sözlük oluştur
# ... (dosyanın başındaki import'lar ve st.set_page_config kısmı aynı kalacak) ...

# Kullanıcı veritabanı dosyasının yolu
USERS_FILE = os.path.join(os.path.dirname(__file__), 'users.json')
LOG_FILE = os.path.join(os.path.dirname(__file__), 'user_activity.log') # Kullanıcı aktivite log dosyası

# Kullanıcıları yükle veya boş bir sözlük oluştur
def load_users():
    users = {}
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            try:
                users = json.load(f)
            except json.JSONDecodeError:
                # Dosya var ama içi boş veya bozuksa, boş sözlük olarak başlat
                users = {}
    
    # 'admin' kullanıcısı yoksa, admin.env dosyasındaki şifre ile oluştur
    if "admin" not in users:
        admin_password_plain = os.getenv('ADMIN_PASSWORD')
        if admin_password_plain:
            # Şifreyi hash'le ve admin kullanıcısını ekle
            hashed_admin_password = bcrypt.hashpw(admin_password_plain.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            users["admin"] = hashed_admin_password
            save_users(users) # Admin kullanıcısını hemen kaydet
            st.info("Admin kullanıcısı ilk kez otomatik olarak oluşturuldu. Lütfen admin.env dosyasındaki şifreyi kullanın.")
        else:
            st.error("HATA: 'ADMIN_PASSWORD' ortam değişkeni 'admin.env' dosyasında bulunamadı. Lütfen kontrol edin.")
            st.stop() # Uygulamanın daha fazla çalışmasını engelle
    
    return users

def save_users(users_data):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users_data, f, indent=4)

# ... (geri kalan kod aynı kalacak) ...
# Loglama fonksiyonu
def log_activity(username, activity_type):
    current_time = st.session_state.current_time.strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"{current_time} - {username} - {activity_type}\n"
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_entry)

# --- Session State Başlatma ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False
if 'show_login_form' not in st.session_state:
    st.session_state.show_login_form = True # Başlangıçta giriş formunu göster
if 'current_time' not in st.session_state:
    import datetime
    st.session_state.current_time = datetime.datetime.now()

# --- Kullanıcı Girişi Formu ---
def show_login_form():
    st.sidebar.subheader("Giriş Yap")
    username_input = st.sidebar.text_input("Kullanıcı Adı", key="username_input")
    password_input = st.sidebar.text_input("Şifre", type="password", key="password_input")

    if st.sidebar.button("Giriş Yap", key="login_button"):
        users = load_users()
        if username_input in users:
            # Kullanıcının girdiği şifreyi hashlenmiş şifre ile karşılaştır
            if bcrypt.checkpw(password_input.encode('utf-8'), users[username_input].encode('utf-8')):
                st.session_state.logged_in = True
                st.session_state.username = username_input
                st.session_state.is_admin = (username_input == "admin") # 'admin' kullanıcısı yönetici yetkili
                st.session_state.show_login_form = False # Giriş yapınca formu gizle
                log_activity(username_input, "Giriş Yaptı")
                st.rerun()
            else:
                st.sidebar.error("Hatalı kullanıcı adı veya şifre.")
        else:
            st.sidebar.error("Hatalı kullanıcı adı veya şifre.")

# --- Ana Dashboard İçeriği ---
def main_dashboard_content():
    st.title("Finansal Hesaplamalar ve Analiz Dashboard'ı")

    st.write(
        """
        Merhaba Murat! 👋 Bu dashboard, finansal projeksiyonlarını, kredi hesaplamalarını
        ve büyüme/indirgeme analizlerini tek bir yerden kolayca yapabilmen için tasarlandı.
        Soldaki menüden istediğin araca ulaşabilirsin.
        """
    )

    # Resim hatasını düzeltmek için kendi yerel resimlerinden birini kullanıyoruz
    # veya bu satırı tamamen silebilirsin.
    # st.image("b.png", width=150) # 'b.png' resmini kullandık, dosyanın aynı dizinde olduğundan emin ol.

    st.write("---") # Ayırıcı bir çizgi

    st.subheader("Başlamak İçin:")
    st.write("- Soldaki menüden bir hesaplama aracı seç.")
    st.write("- Gerekli bilgileri gir ve sonuçları anında gör.")
    st.write("- İhtiyaç duydukça verilerini güncelleyebilirsin.")

    st.info("Unutma: Bu dashboard sürekli geliştirilecek ve yeni özelliklerle zenginleşecektir!")

# ... (Home_Page.py dosyasının başındaki ve ortasındaki kodlar aynı kalacak) ...

# --- Ana Uygulama Akışı ---
if not st.session_state.logged_in:
    main_dashboard_content() # Giriş yapılmadıysa ana dashboard içeriğini göster
    if st.session_state.show_login_form:
        show_login_form()
    # Giriş formu gizlendiyse tekrar göstermek için buton
    if not st.session_state.show_login_form:
        st.sidebar.button("Giriş Formunu Göster", on_click=lambda: st.session_state.update(show_login_form=True), key="toggle_login_form_button")
else:
    st.sidebar.success(f"Hoş Geldin, {st.session_state.username}! 👋")
    if st.session_state.is_admin:
        # DÜZELTİLDİ: Admin_Page.py artık pages klasöründe
        st.sidebar.page_link("pages/Admin_Page.py", label="⚙️ Yönetici Paneli", icon="⚙️")
    
    st.sidebar.button("Çıkış Yap", on_click=lambda: (log_activity(st.session_state.username, "Çıkış Yaptı"), st.session_state.update(logged_in=False, username=None, is_admin=False, show_login_form=True)), key="logout_button")

    main_dashboard_content() # Giriş yapıldıktan sonra da ana içeriği gösterebiliriz.
    
    # DÜZELTİLDİ: Tüm sayfa linklerine 'pages/' öneki eklendi
    st.sidebar.page_link("pages/Growth&WACC.py", label="📈 Büyüme & WACC", icon="📈")
    # 'dcf_streamlit_app.py' diye bir dosya olmadığı için 'Growth Payback.py' dosyasını kullandık
    st.sidebar.page_link("pages/Growth Payback.py", label="💰 Büyüme Geri Ödeme (DCF)", icon="💰") 
    st.sidebar.page_link("pages/Credit Calculation.py", label="💳 Kredi Hesaplama", icon="💳")
    