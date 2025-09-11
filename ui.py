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
    st.session_state.show_welcome = True # Karşılama ekranı kontrolü

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
            
def stream_with_parse(response_generator):
    """Streaming generator'ı sararak parse uyumlu hale getirir"""
    response_container = st.empty()
    full_response = ""
    
    for chunk in response_generator:
        full_response += chunk
        
        # Her chunk'ta sadece ana içeriği göster (think tag'leri gizle)
        import re
        display_content = re.sub(r"<think>.*?</think>", "", full_response, flags=re.DOTALL).strip()
        
        response_container.empty()
        with response_container.container():
            st.markdown(display_content)
    
    # Streaming bitince final parse et
    response_container.empty()
    with response_container.container():
        parse_and_display_response(full_response)
    
    return full_response

def show_welcome_screen():
    """Karşılama ekranı - mevcut araçları ve kategorileri gösterir"""
    st.markdown("---")
    
    if not st.session_state.connected or not st.session_state.agent_manager:
        st.info("👈 Başlamak için lütfen kenar çubuğundan Ollama sunucusuna bağlanın.")
        return
    
    active_cluster_name = getattr(st.session_state.agent_manager, 'active_cluster_name', None)
    
    
    st.success(f"✅ **Aktif Cluster:** {active_cluster_name}")
    st.markdown("### 🔧 Mevcut Agent Kategorileri ve Araçları")
    
    # Tüm kategorileri ve araçlarını göster
    categories = st.session_state.agent_manager.get_available_categories()
    
    # Emoji mapping
    emoji_map = {
        "cluster": "🖥️",
        "namespace": "📦", 
        "deployment": "🚀",
        "repository": "📚"
    }
    
    # 2x2 grid layout
    col1, col2 = st.columns(2)
    
    for i, category in enumerate(categories):
        agent = st.session_state.agent_manager.agents[category]
        tools = agent.get_tools()
        emoji = emoji_map.get(category, "🔧")
        
        # Alternate between columns
        current_col = col1 if i % 2 == 0 else col2
        
        with current_col:
            with st.container():
                st.markdown(f"#### {emoji} {agent.category}")
                st.markdown(f"*{agent.description}*")
                
                # Araçları listele
                with st.expander(f"📋 Araçlar ({len(tools)})", expanded=False):
                    for tool_name, tool_info in tools.items():
                        # Araç adı ve özet
                        summary = tool_info.get('summary', 'Açıklama yok')
                        if len(summary) > 100:
                            summary = summary[:97] + "..."
                        
                        st.markdown(f"**`{tool_name}`**")
                        st.markdown(f"↳ {summary}")
                        
                        # Parametreler
                        params = tool_info.get('parameters', [])
                        if params:
                            required_params = [p['name'] for p in params if p.get('required') and p.get('name') != 'cluster_id']
                            optional_params = [p['name'] for p in params if not p.get('required') and p.get('name') != 'cluster_id']
                            
                            param_text = ""
                            if required_params:
                                param_text += f"**Gerekli:** {', '.join(required_params)}"
                            if optional_params:
                                if param_text:
                                    param_text += " | "
                                param_text += f"*Opsiyonel:* {', '.join(optional_params)}"
                            
                            if param_text:
                                st.caption(f"📝 {param_text}")
                        
                        st.markdown("---")
                
                st.markdown("")  # Add some spacing
    
    st.markdown("---")
    st.markdown("### 💬 Nasıl Kullanılır?")
    st.markdown("""
    1. **Doğal dil ile soru sorun:** "prometheus repository'sini ekle", "deployment'ları listele"
    2. **Agent otomatik seçilir:** Sistem ihtiyacınıza göre uygun agent'ı seçer
    3. **Gerekli parametreler sorulur:** Eksik bilgiler form ile toplanır
    4. **İşlem gerçekleştirilir:** API çağrıları yapılır ve sonuçlar gösterilir
    """)
        
    return True
# --- Kenar Çubuğu (Sidebar) ---
with st.sidebar:
    st.header("⚙️ Yapılandırma")
    ollama_url = st.text_input("Ollama URL", value="http://ai.ikaganacar.com")
    kubex_url = st.text_input("Kubex URL", value="http://10.67.67.195:8000")
    model_name = st.text_input("Model Adı", value="qwen3:8b")

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

        if st.session_state.agent_manager.current_agent:
            st.divider()
            st.subheader("🔧 Aktif Araçlar")
            current_agent = st.session_state.agent_manager.current_agent
            
            # Agent kategorisi göster
            st.info(f"**Aktif Agent:** {current_agent.category}")
            
            # Araçları göster
            tools = current_agent.get_tools()
            
            # Accordion ile her kategorinin araçlarını göster
            with st.expander(f"📋 {current_agent.category} Araçları ({len(tools)})", expanded=False):
                for tool_name, tool_info in tools.items():
                    # Araç adı ve kısa açıklama
                    st.caption(f"**`{tool_name}`**")
                    summary = tool_info.get('summary', 'Açıklama yok')
                    # Özeti kısalt
                    if len(summary) > 80:
                        summary = summary[:77] + "..."
                    st.write(f"↳ {summary}")
                    
                    # Parametreler varsa göster
                    params = tool_info.get('parameters', [])
                    if params:
                        required_params = [p['name'] for p in params if p.get('required')]
                        optional_params = [p['name'] for p in params if not p.get('required') and p.get('name') != 'cluster_id']
                        
                        param_text = ""
                        if required_params:
                            param_text += f"**Gerekli:** {', '.join(required_params)}"
                        if optional_params:
                            if param_text:
                                param_text += " | "
                            param_text += f"*Opsiyonel:* {', '.join(optional_params)}"
                        
                        if param_text:
                            st.write(f"  📝 {param_text}")
                    
                    st.write("---")
        
        
        st.divider()
        
        # Karşılama ekranı toggle
        if st.button("🏠 Karşılama Ekranı", help="Araçları ve kullanım kılavuzunu göster"):
            st.session_state.show_welcome = not st.session_state.show_welcome
            st.rerun()
        
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
                st.session_state.show_welcome = True  # Karşılama ekranını tekrar göster
                if st.session_state.agent_manager:
                    st.session_state.agent_manager.reset_all_contexts()
                # Cluster listesini de sıfırla ki tekrar çekilsin
                st.session_state.cluster_list = [] 
                st.success("Tüm bağlamlar temizlendi!")
                st.rerun()

# --- Ana Sohbet Arayüzü ---
st.title("🧩 KUBEX Multi-Agent Asistanı")


# Karşılama ekranı veya geçmiş sohbet mesajları
if st.session_state.show_welcome and len(st.session_state.messages) == 0:
    show_welcome_screen()
else:
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
                                
                                # Streaming with parse
                                full_response_content = stream_with_parse(response_generator)
                                
                                st.session_state.messages.append({
                                    "role": "assistant", 
                                    "content": full_response_content
                                })
                                
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
            # Karşılama ekranını gizle
            st.session_state.show_welcome = False
            
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                try:
                    response = st.session_state.agent_manager.route_request(prompt)

                    if isinstance(response, dict) and response.get("status") == "needs_parameters":
                        st.session_state.pending_action = response
                        st.info("Ek bilgilere ihtiyacım var. Lütfen aşağıdaki formu doldurun.")
                        st.rerun() 
                    else:
                        # Streaming with parse
                        full_response_content = stream_with_parse(response)
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

