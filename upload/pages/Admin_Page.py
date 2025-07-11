import streamlit as st
import json
import os
import bcrypt # Şifreleri hashlemek için
import datetime # Loglama için zaman bilgisi

# --- Sayfa Ayarları ---
st.set_page_config(
    page_title="Yönetici Paneli",
    page_icon="⚙️", # Yönetici paneli için güzel bir ikon
    layout="wide"
)

# --- Dosya Yolları ---
USERS_FILE = os.path.join(os.path.dirname(__file__), 'users.json')
LOG_FILE = os.path.join(os.path.dirname(__file__), 'user_activity.log')

# --- Yardımcı Fonksiyonlar ---
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_users(users_data):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users_data, f, indent=4)

# --- Yönetici Oturum Kontrolü ---
# Eğer yönetici girişi yapılmamışsa veya yetkisi yoksa ana sayfaya yönlendir
if not st.session_state.get('logged_in', False) or not st.session_state.get('is_admin', False):
    st.warning("Bu sayfaya erişim yetkiniz yok. Lütfen yönetici olarak giriş yapın.")
    st.switch_page("Home_Page.py")
    st.stop() # Sayfanın geri kalanını çalıştırmayı durdur

# --- Admin Paneli İçeriği ---
st.title("⚙️ Admin Paneli")
st.write(f"Hoş Geldin Yönetici {st.session_state.username}! 👋")
st.write("Bu panelden uygulamanın ayarlarını yapabilir, kullanıcıları yönetebilir ve aktivite loglarını görebilirsin.")

# --- Tab Navigasyonu ---
tab1, tab2, tab3 = st.tabs(["👥 Kullanıcı Yönetimi", "📋 Aktivite Logları", "📊 Genel Ayarlar"])

with tab1:
    st.subheader("👥 Kullanıcı Yönetimi")
    st.write("Yeni kullanıcı ekleyebilir veya mevcut kullanıcıları yönetebilirsin.")

    # Yeni Kullanıcı Ekle Formu
    with st.form("add_user_form", clear_on_submit=True):
        st.write("Yeni Kullanıcı Ekle")
        new_username = st.text_input("Yeni Kullanıcı Adı", key="new_user_username").strip()
        new_password = st.text_input("Yeni Şifre", type="password", key="new_user_password")
        new_password_confirm = st.text_input("Şifreyi Tekrar Gir", type="password", key="new_user_password_confirm")
        
        submitted = st.form_submit_button("Kullanıcı Ekle")

        if submitted:
            users = load_users()
            if not new_username or not new_password or not new_password_confirm:
                st.error("Kullanıcı adı ve şifre alanları boş bırakılamaz.")
            elif new_password != new_password_confirm:
                st.error("Şifreler uyuşmuyor.")
            elif new_username in users:
                st.error(f"'{new_username}' kullanıcı adı zaten mevcut.")
            else:
                # Yeni şifreyi hash'le ve kaydet
                hashed_new_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                users[new_username] = hashed_new_password
                save_users(users)
                st.success(f"'{new_username}' kullanıcısı başarıyla eklendi.")
                # Kullanıcıları yeniden yükle
                users = load_users()


    st.markdown("---")
    st.subheader("Mevcut Kullanıcılar")
    users = load_users() # Güncel kullanıcı listesini al
    if users:
        user_list_display = [{"Kullanıcı Adı": u} for u in users.keys()]
        st.dataframe(user_list_display, use_container_width=True)

        # Kullanıcı silme (İsteğe bağlı, dikkatli kullanılmalı)
        user_to_delete = st.selectbox("Silmek İstediğin Kullanıcıyı Seç", options=[""] + list(users.keys()), key="user_delete_select")
        if user_to_delete and st.button(f"'{user_to_delete}' Kullanıcısını Sil", key="delete_user_button"):
            if user_to_delete == "admin":
                st.error("Admin kullanıcısı silinemez.")
            else:
                del users[user_to_delete]
                save_users(users)
                st.success(f"'{user_to_delete}' kullanıcısı başarıyla silindi.")
                st.rerun()
    else:
        st.info("Henüz hiç kullanıcı yok.")


with tab2:
    st.subheader("📋 Aktivite Logları")
    st.write("Kullanıcıların giriş ve çıkış hareketlerini buradan takip edebilirsin.")

    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            log_entries = f.readlines()
        
        if log_entries:
            # Logları tersten sıralayarak en yeni girişleri başta göster
            st.text_area("Kullanıcı Aktivite Logları", "".join(reversed(log_entries)), height=400)
            if st.button("Logları Temizle", key="clear_logs_button"):
                open(LOG_FILE, 'w', encoding='utf-8').close() # Dosyayı boşalt
                st.success("Aktivite logları temizlendi.")
                st.rerun()
        else:
            st.info("Henüz hiç aktivite logu yok.")
    else:
        st.info("Aktivite log dosyası bulunamadı.")

with tab3:
    st.subheader("📊 Genel Ayarlar")
    st.write("Burada uygulamanın genel davranışını etkileyen ayarları yapabilirsin.")

    # Örnek: Ana sayfa bilgi mesajını değiştirme
    # Bu mesajı dinamik olarak kaydetmek için daha gelişmiş bir mekanizma (örn. json dosyası) gerekebilir
    st.markdown("---")
    st.info("Bu bölümdeki ayarlar için kalıcı depolama (örneğin bir ayarlar.json dosyası) kurmanız gerekebilir.")
    st.write("Buraya uygulamanın varsayılan para birimi, varsayılan senaryo sayısı gibi ayarları ekleyebiliriz.")

    # Örnek: Kaydedilmiş finans girdilerini görüntüleme/silme
    st.subheader("💾 Kaydedilmiş Finans Girdileri")
    FINANS_INPUTS_FILE = os.path.join(os.path.dirname(__file__), 'finans_inputs.json') # Growth&WACC'teki SAVE_FILE_NAME
    DCF_INPUTS_FILE = os.path.join(os.path.dirname(__file__), 'dcf_streamlit_inputs.json') # Growth Payback'teki SAVE_FILE_NAME

    if os.path.exists(FINANS_INPUTS_FILE):
        with open(FINANS_INPUTS_FILE, 'r', encoding='utf-8') as f:
            finans_data = f.read()
        st.text_area(f"{FINANS_INPUTS_FILE} İçeriği", finans_data, height=200)
        if st.button(f"'{FINANS_INPUTS_FILE}' Dosyasını Sil", key="delete_finans_inputs"):
            os.remove(FINANS_INPUTS_FILE)
            st.success(f"'{FINANS_INPUTS_FILE}' dosyası silindi.")
            st.rerun()
    else:
        st.info(f"'{FINANS_INPUTS_FILE}' dosyası bulunamadı.")

    if os.path.exists(DCF_INPUTS_FILE):
        with open(DCF_INPUTS_FILE, 'r', encoding='utf-8') as f:
            dcf_data = f.read()
        st.text_area(f"{DCF_INPUTS_FILE} İçeriği", dcf_data, height=200)
        if st.button(f"'{DCF_INPUTS_FILE}' Dosyasını Sil", key="delete_dcf_inputs"):
            os.remove(DCF_INPUTS_FILE)
            st.success(f"'{DCF_INPUTS_FILE}' dosyası silindi.")
            st.rerun()
    else:
        st.info(f"'{DCF_INPUTS_FILE}' dosyası bulunamadı.")

st.sidebar.markdown("---")
st.sidebar.button("Ana Sayfaya Dön", on_click=lambda: st.switch_page("Home_Page.py"), key="back_to_home_from_admin")