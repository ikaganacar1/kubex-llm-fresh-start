import streamlit as st
import logging
import re

from ollama import OllamaClient
from agent_manager import AgentManager

# --- Logger Kurulumu ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Sayfa Yapılandırması ---
st.set_page_config(
    page_title="KUBEX Multi-Agent Asistanı",
    page_icon="🧩",
    layout="wide"
)

if "agent_manager" not in st.session_state:
    st.session_state.agent_manager = None
    st.session_state.connected = False
    st.session_state.messages = []
    st.session_state.pending_action = None
    st.session_state.show_debug = False  # YENI: Debug panel toggle

def parse_and_display_response(full_response: str):
    thinking_pattern = re.compile(r"<think>(.*?)</think>", re.DOTALL)
    thinking_content = ""
    main_content = full_response

    match = thinking_pattern.search(full_response)
    if match:
        thinking_content = match.group(1).strip()
        main_content = thinking_pattern.sub("", full_response).strip()

    if main_content:
        st.markdown(main_content)
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
                if client.test_connection():
                    st.session_state.agent_manager = AgentManager(client)
                    st.session_state.connected = True
                    st.success(f"Başarıyla bağlanıldı!\n\n**Model:** {model_name}")
                    st.rerun()
                else:
                    st.error("Sunucuya ulaşıldı ancak API yanıt vermiyor. Ollama'nın çalıştığından emin olun.")
            except Exception as e:
                st.error(f"Bağlanırken bir hata oluştu: {e}")
                logger.error(f"Bağlantı hatası: {e}")

    if st.session_state.connected and st.session_state.agent_manager:
        st.divider()
        
        # YENI: Debug panel toggle
        st.session_state.show_debug = st.checkbox("🔍 Debug Panel", value=st.session_state.show_debug)
        
        # Mevcut durumu göster - YENI: Geliştirilmiş status display
        status = st.session_state.agent_manager.get_current_status()
        if status["active_agent"]:
            st.success(f"🤖 **Aktif Agent:** {status['active_agent']}")
            
            if status["waiting_for_parameters"]:
                st.warning("⏳ Parametre bekleniyor...")
                if status["tool_context"]:
                    tool_name = status["tool_context"]["tool_name"]
                    missing = status["tool_context"]["missing_params"]
                    st.caption(f"Araç: `{tool_name}`")
                    st.caption(f"Eksik: {', '.join(missing)}")
            
            # YENI: Context information
            if st.session_state.show_debug:
                st.caption(f"🧠 Global Context: {status['global_context_size']} etkileşim")
                st.caption(f"🔧 Tool Etkileşimleri: {status['last_interactions']}")
        else:
            st.info("🎯 **Router Modu:** İstek kategorisi bekleniyor")
        
        # YENI: Debug panel
        if st.session_state.show_debug:
            with st.expander("🔍 Memory Debug Panel", expanded=False):
                if hasattr(st.session_state.agent_manager, 'get_conversation_summary'):
                    summary = st.session_state.agent_manager.get_conversation_summary()
                    st.text_area("Conversation Memory", summary, height=200)
                
                # Current agent memory
                if st.session_state.agent_manager.current_agent:
                    agent = st.session_state.agent_manager.current_agent
                    if hasattr(agent, 'conversation_context') and agent.conversation_context:
                        st.subheader(f"{agent.category} Local Context")
                        for i, ctx in enumerate(agent.conversation_context[-3:]):
                            st.caption(f"**Etkileşim {i+1}:**")
                            st.caption(f"👤 User: {ctx['user'][:100]}...")
                            st.caption(f"🤖 Agent: {ctx['assistant'][:100]}...")
        
        # Mevcut kategoriler
        categories = st.session_state.agent_manager.get_available_categories()
        st.subheader("📂 Mevcut Kategoriler")
        for category in categories:
            agent = st.session_state.agent_manager.agents[category]
            st.caption(f"• **{agent.category}**")
            st.caption(f"  {agent.description}", unsafe_allow_html=True)
        
        st.divider()
        
        # YENI: Reset seçenekleri
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔄 Soft Reset"):
                if st.session_state.agent_manager:
                    st.session_state.agent_manager.soft_reset_contexts()
                st.success("İşlem durumu sıfırlandı, memory korundu!")
                st.rerun()
        
        with col2:
            if st.button("🗑️ Full Reset"):
                st.session_state.messages = []
                st.session_state.pending_action = None
                if st.session_state.agent_manager:
                    st.session_state.agent_manager.reset_all_contexts()
                st.success("Tüm bağlamlar temizlendi!")
                st.rerun()

# --- Ana Sohbet Arayüzü ---
st.title("🧩 KUBEX Multi-Agent Asistanı")

# YENI: Memory durumu göstergesi
if st.session_state.connected and st.session_state.agent_manager:
    status = st.session_state.agent_manager.get_current_status()
    if status["global_context_size"] > 0:
        st.info(f"💾 **Memory:** {status['global_context_size']} etkileşim | "
                f"🤖 **Aktif Agent:** {status['active_agent'] or 'Router'}")

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
            
            # Aktif agent bilgisi
            status = st.session_state.agent_manager.get_current_status()
            if status["active_agent"]:
                st.info(f"**Aktif Agent:** {status['active_agent']}")
                st.info(f"**Araç:** {pending['tool_name']}")
            
            # YENI: Original request bilgisini göster
            if "original_request" in pending.get("extracted_params", {}):
                original = pending["extracted_params"]["original_request"]
                st.caption(f"📝 **Orijinal İstek:** {original[:100]}...")
            
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
                # İşlemi iptal et ve soft reset yap
                st.session_state.pending_action = None
                if st.session_state.agent_manager:
                    st.session_state.agent_manager.soft_reset_contexts()  # YENI: Soft reset
                st.rerun()
                
            if submitted:
                # Form gönderildikten sonra asistan mesaj baloncuğu oluştur
                with st.chat_message("assistant"):
                    response_generator = st.session_state.agent_manager.finalize_request(
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
    if prompt := st.chat_input("Kubernetes ile ilgili bir soru sorun... (örn: cluster listesi, namespace oluştur, deployment durumu)"):
        # Kullanıcı mesajını geçmişe ve ekrana ekle
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            # Router üzerinden işlemi başlat
            response = st.session_state.agent_manager.route_request(prompt)

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

    # Yardımcı örnekler - YENI: Context-aware examples
    st.divider()
    
    with st.expander("💡 Örnek Komutlar & Test Senaryoları"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🏗️ Cluster İşlemleri")
            st.code("cluster listesi göster")
            st.code("yeni cluster oluştur")
            st.code("cluster detaylarını göster")
            st.code("cluster özet bilgisi ver")
            
            st.subheader("🧠 Memory Test")
            st.code("Bu liste kaç cluster gösteriyor?")
            st.code("Hangisi en yenisi?")
            st.code("Önceki sonuçta hangi cluster'lar vardı?")
            
        with col2:
            st.subheader("📦 Namespace İşlemleri")
            st.code("namespace listesini göster")
            st.code("production namespace'i oluştur")
            st.code("test namespace'ini sil")
            st.code("namespace durumları nedir")
            
            st.subheader("🔄 Context Takip")
            st.code("Bu namespacelar hangi cluster'da?")
            st.code("Bunları nasıl yönetebilirim?")
            st.code("Daha detay bilgi ver")

else:
    st.info("👈 Lütfen önce kenar çubuğundan Ollama sunucusuna bağlanın.")
    
    # Bağlantı yokken sistem açıklaması göster
    st.divider()
    st.subheader("🤖 Multi-Agent Mimarisi")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        **🎯 Router Agent**
        - Kullanıcı isteklerini analiz eder
        - Uygun kategoriye yönlendirir
        - Genel sohbet soularını yanıtlar
        - **🆕 Global context yönetimi**
        """)
        
        st.markdown("""
        **🏗️ Cluster Agent**
        - Kubernetes cluster yönetimi
        - Cluster oluşturma/listeleme
        - Cluster güncelleme işlemleri
        - **🆕 Context-aware responses**
        """)
        
    with col2:
        st.markdown("""
        **📦 Namespace Agent**
        - Namespace yönetimi
        - Namespace oluşturma/silme
        - Namespace durum kontrolü
        - **🆕 Memory integration**
        """)
        
        st.markdown("""
        **🧠 İyileştirmeler**
        - ✅ Orijinal soru hatırlanır
        - ✅ Tool sonuçları context-aware
        - ✅ Agent'lar arası memory paylaşımı
        - ✅ Önceki yanıtlar referans edilir
        """)
    
    st.info("Her agent kendi özel alanında uzmanlaşmış ve **conversation memory** ile donatılmıştır!")