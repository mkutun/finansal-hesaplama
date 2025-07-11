import streamlit as st
import os
import json
from dotenv import load_dotenv
import bcrypt
import datetime # Loglama için zaman bilgisini de buraya ekledik

# --- Sayfa Ayarları ---
st.set_page_config(
    page_title="Finansal Dashboard'um",
    page_icon="📊", # Finans için güzel bir ikon
    layout="wide"
)

# --- Ortam Değişkenlerini Yükle ---
# admin.env dosyasının Home_Page.py ile aynı dizinde olduğunu varsayıyoruz
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), 'admin.env'))

SECRET_KEY = os.getenv('SECRET_KEY') # SECRET_KEY kullanılıyor mu kontrol edelim, yoksa silebiliriz.

# Kullanıcı veritabanı dosyasının yolu
# Dikkat: Bu USERS_FILE ve LOG_FILE yolları 'pages' klasöründe değil, ana dizinde olması daha uygun
# Senin gönderdiğin Home_Page.py'da bu dosyaların pages içinde olduğu varsayılmış.
# Eğer ana dizinde (upload klasöründe) bulunuyorlarsa yolları aşağıdaki gibi ayarlayalım:
# USERS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'users.json')
# LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'user_activity.log')

# Şimdilik senin kodundaki yolları koruyalım, ama ileride bu paths meselesini konuşabiliriz Murat
USERS_FILE = os.path.join(os.path.dirname(__file__), 'users.json')
LOG_FILE = os.path.join(os.path.dirname(__file__), 'user_activity.log') 

# Kullanıcıları yükle veya boş bir sözlük oluştur
def load_users():
    users = {}
    # Eğer USERS_FILE dosyası pages klasöründe değilse ve bir üst dizindeyse bu kontrolü yapalım
    # Örneğin, 'upload/users.json' olarak
    # Bu kısmı senin current directory yapına göre düzenleyebiliriz.
    # Şimdilik, Home_Page.py ile aynı dizinde arıyor.
    
    # Kullanıcı dosyasının bir üst dizinde olup olmadığını kontrol etmek için:
    # parent_dir_users_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'users.json')
    # if os.path.exists(parent_dir_users_file):
    #     with open(parent_dir_users_file, 'r', encoding='utf-8') as f:
    #         try:
    #             users = json.load(f)
    #         except json.JSONDecodeError:
    #             users = {}

    # Yoksa, mevcut path'te ara (Home_Page.py ile aynı dizinde)
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            try:
                users = json.load(f)
            except json.JSONDecodeError:
                users = {}
    
    # 'admin' kullanıcısı yoksa, admin.env dosyasındaki şifre ile oluştur
    if "admin" not in users:
        admin_password_plain = os.getenv('ADMIN_PASSWORD')
        if admin_password_plain:
            hashed_admin_password = bcrypt.hashpw(admin_password_plain.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            users["admin"] = hashed_admin_password
            save_users(users)
            st.info("Admin kullanıcısı ilk kez otomatik olarak oluşturuldu. Lütfen admin.env dosyasındaki şifreyi kullanın.")
        else:
            st.error("HATA: 'ADMIN_PASSWORD' ortam değişkeni 'admin.env' dosyasında bulunamadı. Lütfen kontrol edin.")
            st.stop()
    
    return users

def save_users(users_data):
    # Kaydetme işlemini de doğru PATH'e yapalım
    # parent_dir_users_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'users.json')
    # with open(parent_dir_users_file, 'w', encoding='utf-8') as f:
    #     json.dump(users_data, f, indent=4)
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users_data, f, indent=4)


# Loglama fonksiyonu
def log_activity(username, activity_type):
    # Log dosyasının da doğru PATH'te olduğundan emin olalım
    # parent_dir_log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'user_activity.log')
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") # st.session_state.current_time yerine anlık zaman
    log_entry = f"{current_time} - {username} - {activity_type}\n"
    # with open(parent_dir_log_file, 'a', encoding='utf-8') as f:
    #     f.write(log_entry)
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_entry)

# --- Session State Başlatma ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False
# 'show_login_form' state'ine artık gerek kalmadı, çünkü logged_in durumu doğrudan belirleyici olacak
# if 'show_login_form' not in st.session_state:
#     st.session_state.show_login_form = True 

# --- Kullanıcı Girişi Formu ---
def show_login_form():
    st.sidebar.subheader("Giriş Yap")
    username_input = st.sidebar.text_input("Kullanıcı Adı", key="username_input")
    password_input = st.sidebar.text_input("Şifre", type="password", key="password_input")

    if st.sidebar.button("Giriş Yap", key="login_button"):
        users = load_users()
        if username_input in users:
            if bcrypt.checkpw(password_input.encode('utf-8'), users[username_input].encode('utf-8')):
                st.session_state.logged_in = True
                st.session_state.username = username_input
                st.session_state.is_admin = (username_input == "admin")
                log_activity(username_input, "Giriş Yaptı")
                st.rerun() # Giriş yapıldıktan sonra sayfayı yeniden yükle
            else:
                st.sidebar.error("Hatalı kullanıcı adı veya şifre.")
        else:
            st.sidebar.error("Hatalı kullanıcı adı veya şifre.")

# --- Ana Dashboard İçeriği (Giriş Yapılmasa Bile Görülecek Kısım) ---
def main_dashboard_content():
    st.title("Finansal Hesaplamalar ve Analiz Dashboard'ı")

    st.write(
        """
        Merhaba Murat! 👋 Bu dashboard, finansal projeksiyonlarını, kredi hesaplamalarını
        ve büyüme/indirgeme analizlerini tek bir yerden kolayca yapabilmen için tasarlandı.
        Giriş yaptıktan sonra soldaki menüden istediğin araca ulaşabilirsin.
        """
    )

    # Resim hatasını düzeltmek için kendi yerel resimlerinden birini kullanıyoruz
    # veya bu satırı tamamen silebilirsin.
    # st.image("b.png", width=150) # 'b.png' resmini kullandık, dosyanın aynı dizinde olduğundan emin ol.

    st.write("---") # Ayırıcı bir çizgi

    st.subheader("Başlamak İçin:")
    st.write("- Lütfen sol taraftaki menüden giriş yapın.")
    st.write("- Giriş yaptıktan sonra hesaplama araçları menüde belirecektir.")

    st.info("Unutma: Bu dashboard sürekli geliştirilecek ve yeni özelliklerle zenginleşecektir!")

# --- Ana Uygulama Akışı ---
main_dashboard_content() # Ana dashboard içeriği her zaman gösterilecek

if not st.session_state.logged_in:
    # Giriş yapılmadıysa sadece giriş formunu göster
    show_login_form()
else:
    # Giriş yapıldıysa kullanıcıya hoş geldin mesajı ve çıkış butonu
    st.sidebar.success(f"Hoş Geldin, {st.session_state.username}! 👋")
    
    if st.session_state.is_admin:
        # Adminse Yönetici Paneli linkini göster
        st.sidebar.page_link("pages/Admin_Page.py", label="⚙️ Yönetici Paneli", icon="⚙️")
    
    # Yeni yapıya uygun olarak kategorize edilmiş menüler
    st.sidebar.markdown("---") # Menü ayırıcısı
    st.sidebar.subheader("Finansal Hesaplama")
    st.sidebar.page_link("pages/Growth Payback.py", label="💰 Büyüme Geri Ödeme (DCF)", icon="💰")
    st.sidebar.page_link("pages/Growth&WACC.py", label="📈 Büyüme & WACC", icon="📈")
    st.sidebar.page_link("pages/Net Operating Capital.py", label="🏗️ Net İşletme Sermayesi", icon="🏗️") # Yeni eklendi

    st.sidebar.markdown("---")
    st.sidebar.subheader("Calculations")
    st.sidebar.page_link("pages/Credit Calculation.py", label="💳 Kredi Hesaplama", icon="💳")
    st.sidebar.page_link("pages/Tax Calculation.py", label="📊 Vergi Hesaplama", icon="📊") # Yeni eklendi

    st.sidebar.markdown("---")
    st.sidebar.subheader("Graphic Scenario")
    st.sidebar.page_link("pages/Chart Wizard.py", label="📈 Grafik Sihirbazı", icon="📈") # Yeni eklendi

    st.sidebar.markdown("---") # Menü ayırıcısı
    # Çıkış butonu
    st.sidebar.button(
        "Çıkış Yap", 
        on_click=lambda: (log_activity(st.session_state.username, "Çıkış Yaptı"), 
                          st.session_state.update(logged_in=False, username=None, is_admin=False)), 
        key="logout_button"
    )