import streamlit as st
import logging
import re, json
from typing import Dict, Any # Ekleme: Tip denetimi için

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

# --- Session State Başlatma ---
if "agent_manager" not in st.session_state:
    st.session_state.agent_manager = None
    st.session_state.connected = False
    st.session_state.messages = []
    st.session_state.pending_action = None
    st.session_state.show_debug = False
    st.session_state.cluster_list = [] # Cluster listesini saklamak için
    st.session_state.cluster_list_data = [] # İşlenmiş veriyi saklamak için yeni state

def parse_and_display_response(full_response: str):
    """LLM yanıtını ayrıştırır ve 'think' etiketlerini expander içine alır."""
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
    ollama_url = st.text_input("Ollama URL", value="http://ai.ikaganacar.com")
    kubex_url = st.text_input("Kubex URL", value="http://10.67.67.195:8000")
    model_name = st.text_input("Model Adı", value="qwen3:4b")

    if st.button("Bağlan", type="primary"):
        with st.spinner("Bağlanılıyor..."):
            try:
                client = OllamaClient(ollama_url=ollama_url,kubex_url=kubex_url, model_name=model_name)
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

        # 1. Cluster listesini sadece bir kez çek
        if not st.session_state.cluster_list_data:
            with st.spinner("Cluster listesi alınıyor..."):
                try:
                    clusters_raw = st.session_state.agent_manager.get_cluster_list_for_ui()
                    
                    
                    if isinstance(clusters_raw, list):
                        st.session_state.cluster_list_data = clusters_raw
                    else:
                        st.session_state.cluster_list_data = []
                        logger.warning("get_cluster_list_for_ui fonksiyonundan beklenen liste formatında veri alınamadı.")



                except Exception as e:
                    logger.error(f"Cluster listesi alınırken veya işlenirken hata oluştu: {e}")
                    st.session_state.cluster_list_data = []

        # 2. Cluster seçme arayüzünü göster
        if st.session_state.cluster_list_data:
            try:
                # API'nizin döndürdüğü gerçek "id" ve "name" alan adlarını kullanın.
                # JSON çıktınıza göre anahtarlar doğru görünüyor ('name' ve 'id').
                cluster_options = {cluster['name']: cluster['id'] for cluster in st.session_state.cluster_list_data}
                
                active_cluster_name = getattr(st.session_state.agent_manager, 'active_cluster_name', None)
                if not active_cluster_name and cluster_options:
                     active_cluster_name = list(cluster_options.keys())[0]

                current_index = list(cluster_options.keys()).index(active_cluster_name) if active_cluster_name in cluster_options else 0

                selected_cluster_name = st.selectbox(
                    "Aktif Cluster Seçin",
                    options=list(cluster_options.keys()), # Seçeneklerin liste olduğundan emin olalım
                    index=current_index,
                    key="cluster_selector"
                )
                
                selected_id = cluster_options[selected_cluster_name]
                if st.session_state.agent_manager.active_cluster_id != selected_id:
                    st.session_state.agent_manager.set_active_cluster(selected_id, selected_cluster_name)
                    st.rerun()

            except KeyError as e:
                st.error(f"Cluster verisi ayrıştırılırken hata: '{e}' anahtarı bulunamadı.")
                logger.error(f"KeyError: API verisindeki anahtarlar UI koduyla eşleşmiyor. Veri: {st.session_state.cluster_list_data}")
            except Exception as e:
                st.error(f"Cluster dropdown oluşturulurken beklenmedik hata: {e}")
        elif st.session_state.connected:
             st.warning("API'den cluster listesi alınamadı veya liste boş.")

        # --- Debug ve Agent Bilgileri ---
        st.divider()
        st.session_state.show_debug = st.checkbox("🔍 Debug Panel", value=st.session_state.show_debug)
        status = st.session_state.agent_manager.get_current_status()

        if status["waiting_for_parameters"]:
            st.warning("⏳ Parametre bekleniyor...")
            if status["tool_context"]:
                tool_name = status["tool_context"]["tool_name"]
                missing = status["tool_context"]["missing_params"]
                st.caption(f"Araç: `{tool_name}` | Eksik: {', '.join(missing)}")

        if st.session_state.show_debug:
            with st.expander("🔍 Memory Debug Panel", expanded=False):
                if hasattr(st.session_state.agent_manager, 'get_conversation_summary'):
                    summary = st.session_state.agent_manager.get_conversation_summary()
                    st.text_area("Conversation Memory", summary, height=200)
                
                # Current agent memory detail
                if st.session_state.agent_manager.current_agent:
                    agent = st.session_state.agent_manager.current_agent
                    if hasattr(agent, 'conversation_context') and agent.conversation_context:
                        st.subheader(f"{agent.category} Local Context")
                        for i, ctx in enumerate(agent.conversation_context[-3:]):
                            st.caption(f"**Etkileşim {i+1}:** User: {ctx['user'][:50]}...")

        # Mevcut kategoriler
        categories = st.session_state.agent_manager.get_available_categories()
        st.subheader("📂 Mevcut Agent Kategorileri")
        for category in categories:
            agent = st.session_state.agent_manager.agents[category]
            st.caption(f"• **{agent.category}**: {agent.description}")
        
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Soft Reset"):
                if st.session_state.agent_manager:
                    st.session_state.agent_manager.soft_reset_contexts()
                st.success("İşlem durumu sıfırlandı!")
                st.rerun()
        with col2:
            if st.button("🗑️ Full Reset"):
                st.session_state.messages = []
                st.session_state.pending_action = None
                if st.session_state.agent_manager:
                    st.session_state.agent_manager.reset_all_contexts()
                # Cluster listesini de sıfırla ki tekrar çekilsin
                st.session_state.cluster_list = [] 
                st.success("Tüm bağlamlar temizlendi!")
                st.rerun()

# --- Ana Sohbet Arayüzü ---
st.title("🧩 KUBEX Multi-Agent Asistanı")

# Durum Bilgisi (Birleştirilmiş)
if st.session_state.connected and st.session_state.agent_manager:
    active_cluster_name = getattr(st.session_state.agent_manager, 'active_cluster_name', None)
    if active_cluster_name:
        status = st.session_state.agent_manager.get_current_status()
        memory_size = status['global_context_size']
        st.info(f"Seçili Cluster: **{active_cluster_name}**")
    else:
        st.warning("Lütfen kenar çubuğundan bir cluster seçerek başlayın.")

# Geçmiş sohbet mesajlarını ekrana yazdır
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        parse_and_display_response(message["content"])

# --- Sohbet Girişi ve Form Yönetimi ---
if st.session_state.connected:
    # DURUM 1: Eksik parametreleri toplama formu
    if st.session_state.pending_action:
        pending = st.session_state.pending_action
        
        # Debug bilgisi göster
        if st.session_state.show_debug:
            st.json(pending)
        
        with st.form("parameter_form", clear_on_submit=True):
            st.warning("İşlemi tamamlamak için ek bilgilere ihtiyacım var:")
            
            status = st.session_state.agent_manager.get_current_status()
            if status["active_agent"]:
                st.info(f"**Aktif Agent:** {status['active_agent']} | **Araç:** {pending['tool_name']}")
            
            collected_params: Dict[str, Any] = {}
            
            # Her parametre için input alanı oluştur
            for i, param in enumerate(pending["missing_params"]):
                question = pending["questions"][i] if i < len(pending["questions"]) else f"Lütfen '{param}' değeri için bilgi verin:"
                
                # Özel input tipleri
                if param == "replicas":
                    collected_params[param] = st.number_input(
                        question, 
                        min_value=1, 
                        value=1, 
                        key=f"param_{param}_{i}"
                    )
                elif param == "values":
                    # JSON input için text area
                    values_input = st.text_area(
                        question + " (boş bırakabilirsiniz)", 
                        placeholder='{"key": "value"}',
                        key=f"param_{param}_{i}",
                        height=100
                    )
                    if values_input.strip():
                        try:
                            collected_params[param] = json.loads(values_input)
                        except json.JSONDecodeError:
                            st.error("Geçersiz JSON formatı!")
                            collected_params[param] = ""
                    else:
                        collected_params[param] = None
                else:
                    # Normal text input
                    collected_params[param] = st.text_input(
                        question, 
                        key=f"param_{param}_{i}",
                        placeholder=f"Örn: {param}_degeri"
                    )

            # Form butonları
            col1, col2 = st.columns([1, 1])
            with col1:
                submitted = st.form_submit_button("Bilgileri Gönder", type="primary")
            with col2:
                cancelled = st.form_submit_button("İptal Et")
            
            # İptal işlemi
            if cancelled:
                st.session_state.pending_action = None
                if st.session_state.agent_manager:
                    st.session_state.agent_manager.soft_reset_contexts()
                st.success("İşlem iptal edildi.")
                st.rerun()
            
            # Form submit işlemi    
            if submitted:
                # Boş parametreleri kontrol et
                empty_required_params = []
                for param_name, param_value in collected_params.items():
                    if param_value is None or (isinstance(param_value, str) and not param_value.strip()):
                        empty_required_params.append(param_name)
                
                if empty_required_params:
                    st.error(f"Şu parametreler boş bırakılamaz: {', '.join(empty_required_params)}")
                else:
                    # Parametreleri temizle ve execute et
                    cleaned_params = {}
                    for key, value in collected_params.items():
                        if value is not None and value != "":
                            cleaned_params[key] = value
                    
                    # Assistant mesajını ekle
                    with st.chat_message("assistant"):
                        with st.spinner("İşlem gerçekleştiriliyor..."):
                            try:
                                response_generator = st.session_state.agent_manager.finalize_request(
                                    pending["tool_name"],
                                    pending.get("extracted_params", {}),
                                    cleaned_params
                                )
                                full_response_content = st.write_stream(response_generator)
                                
                                # Mesajları kaydet
                                st.session_state.messages.append({
                                    "role": "assistant", 
                                    "content": full_response_content
                                })
                                
                                # Pending action'ı temizle
                                st.session_state.pending_action = None
                                st.rerun()
                                
                            except Exception as e:
                                st.error(f"İşlem sırasında hata oluştu: {str(e)}")
                                st.session_state.pending_action = None

    # DURUM 2: Normal sohbet girişi
    else:
        # Sadece cluster seçiliyse chat input'u aktif et
        chat_disabled = not getattr(st.session_state.agent_manager, 'active_cluster_id', None)
        chat_placeholder = "Cluster seçin..." if chat_disabled else "Kubernetes ile ilgili bir soru sorun..."

        if prompt := st.chat_input(chat_placeholder, disabled=chat_disabled):
            # User mesajını ekle
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Assistant yanıtını al
            with st.chat_message("assistant"):
                try:
                    response = st.session_state.agent_manager.route_request(prompt)

                    if isinstance(response, dict) and response.get("status") == "needs_parameters":
                        # Parametre gerekiyor - pending action olarak kaydet
                        st.session_state.pending_action = response
                        st.info("Ek bilgilere ihtiyacım var. Lütfen aşağıdaki formu doldurun.")
                        st.rerun() 
                    else:
                        # Normal response - stream olarak göster
                        response_placeholder = st.empty()
                        full_response_content = ""
                        
                        for chunk in response:
                            full_response_content += chunk
                            with response_placeholder.container():
                                parse_and_display_response(full_response_content)

                        # Mesajı kaydet
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": full_response_content
                        })
                        
                except Exception as e:
                    error_msg = f"Bir hata oluştu: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": error_msg
                    })

else:
    st.info("👈 Lütfen önce kenar çubuğundan Ollama sunucusuna bağlanın.")