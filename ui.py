import streamlit as st
import logging
import re

from ollama import OllamaClient
from agent import KubernetesAgent

# --- Logger Kurulumu ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Sayfa Yapılandırması ---
st.set_page_config(
    page_title="KUBEX Asistanı",
    page_icon="🧩",
    layout="wide"
)

if "agent" not in st.session_state:
    st.session_state.agent = None
    st.session_state.connected = False
    st.session_state.messages = []
    st.session_state.pending_action = None

def parse_and_display_response(full_response: str):
    thinking_pattern = re.compile(r"<think>(.*?)</think>", re.DOTALL)
    thinking_content = ""
    main_content = full_response

    match = thinking_pattern.search(full_response)
    if match:
        thinking_content = match.group(1).strip()
        # Ana metinden <think> bloğunu temizle
        main_content = thinking_pattern.sub("", full_response).strip()

    # Sadece içerik varsa markdown olarak yazdır
    if main_content:
        st.markdown(main_content)
    # Sadece düşünce adımları varsa expander içinde göster
    if thinking_content:
        with st.expander("Modelin Düşünce Adımları 🧠"):
            st.markdown(f"```\n{thinking_content}\n```")

# --- Kenar Çubuğu (Sidebar) ---
with st.sidebar:
    st.header("⚙️ Yapılandırma")
    base_url = st.text_input("Ollama URL", value="http://ai.ikaganacar.com")
    model_name = st.text_input("Model Adı", value="qwen3:4b")

    if st.button("Bağlan", type="primary"):
        with st.spinner("Bağlanılıyor..."):
            try:
                client = OllamaClient(base_url=base_url, model_name=model_name)
                # Bağlantıyı test et
                if client.test_connection():
                    st.session_state.agent = KubernetesAgent(client)
                    st.session_state.connected = True
                    st.success(f"Başarıyla bağlanıldı!\n\n**Model:** {model_name}")
                    st.rerun()
                else:
                    st.error("Sunucuya ulaşıldı ancak API yanıt vermiyor. Ollama'nın çalıştığından emin olun.")
            except Exception as e:
                st.error(f"Bağlanırken bir hata oluştu: {e}")
                logger.error(f"Bağlantı hatası: {e}")

    if st.session_state.connected:
        st.divider()
        
        # Parametre bekleme durumunu göster
        if st.session_state.agent and st.session_state.agent.waiting_for_parameters:
            st.warning("⏳ Parametre bekleniyor...")
            if st.session_state.agent.current_tool_context:
                tool_name = st.session_state.agent.current_tool_context["tool_name"]
                missing = st.session_state.agent.current_tool_context["missing_params"]
                st.caption(f"Araç: `{tool_name}`")
                st.caption(f"Eksik: {', '.join(missing)}")
        
        if st.button("Sohbeti Temizle"):
            st.session_state.messages = []
            st.session_state.pending_action = None
            # Ajanın tüm durumunu sıfırla
            if st.session_state.agent:
                st.session_state.agent.reset_context()
            st.rerun()

# --- Ana Sohbet Arayüzü ---
st.title("KUBEX Asistanı")

# Geçmiş sohbet mesajlarını ekrana yazdır
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        parse_and_display_response(message["content"])

if st.session_state.connected:
    # DURUM 1: Eksik parametreleri toplama formu
    if st.session_state.pending_action:
        pending = st.session_state.pending_action
        with st.form("parameter_form"):
            st.warning("İşlemi tamamlamak için ek bilgilere ihtiyacım var:")
            st.info(f"**Araç:** {pending['tool_name']}")
            
            collected_params = {}
            for i, param in enumerate(pending["missing_params"]):
                question = pending["questions"][i] if i < len(pending["questions"]) else f"{param} nedir?"
                collected_params[param] = st.text_input(question, key=f"param_{param}_{i}")

            col1, col2 = st.columns([1, 1])
            with col1:
                submitted = st.form_submit_button("Bilgileri Gönder", type="primary")
            with col2:
                cancelled = st.form_submit_button("İptal Et")
            
            if cancelled:
                # İşlemi iptal et ve durumu sıfırla
                st.session_state.pending_action = None
                if st.session_state.agent:
                    st.session_state.agent.waiting_for_parameters = False
                    st.session_state.agent.current_tool_context = None
                st.rerun()
                
            if submitted:
                # Form gönderildikten sonra asistan mesaj baloncuğu oluştur
                with st.chat_message("assistant"):
                    response_generator = st.session_state.agent.finalize_request(
                        pending["tool_name"],
                        pending["extracted_params"],
                        collected_params
                    )
                    full_response_content = st.write_stream(response_generator)

                # Tamamlanan yanıtı sohbet geçmişine ekle
                st.session_state.messages.append({"role": "assistant", "content": full_response_content})
                st.session_state.pending_action = None
                st.rerun()

    # DURUM 2: Normal sohbet girişi
    if prompt := st.chat_input("Kubernetes ile ilgili bir soru sorun..."):
        # Kullanıcı mesajını geçmişe ve ekrana ekle
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            response = st.session_state.agent.process_request(prompt)

            if isinstance(response, dict) and response.get("status") == "needs_parameters":
                st.session_state.pending_action = response
                st.info("Eksik parametreler tespit edildi. Form hazırlanıyor...")
                st.rerun() 
            else:
                response_placeholder = st.empty()
                full_response_content = ""
                for chunk in response:
                    full_response_content += chunk
                    with response_placeholder.container():
                        parse_and_display_response(full_response_content)

                # Tamamlanan yanıtı sohbet geçmişine ekle
                st.session_state.messages.append({"role": "assistant", "content": full_response_content})
else:
    st.info("👈 Lütfen önce kenar çubuğundan Ollama sunucusuna bağlanın.")