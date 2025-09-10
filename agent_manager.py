# agent_manager.py

import logging
import json
from typing import Dict, Any, List, Generator, Union, Optional
from ollama import OllamaClient
from agents.cluster_agent import ClusterAgent
from agents.namespace_agent import NamespaceAgent
from agents.deployment_agent import DeploymentAgent
from agents.repository_agent import RepositoryAgent


logger = logging.getLogger(__name__)

class AgentManager:
    """Tüm agent'ları yöneten merkezi sınıf - İyileştirilmiş global context yönetimi ile"""
    
    def __init__(self, client: OllamaClient):
        self.client = client
        
        self.global_conversation_context = []
        self.session_active = True
        self.active_cluster_id: Optional[str] = "None"
        self.active_cluster_name: Optional[str] = None 

        self.agents = self._initialize_agents()
        self.current_agent = None
        self.waiting_for_parameters = False
        self.router_system_prompt = self._build_router_system_prompt()
    
    def _initialize_agents(self) -> Dict[str, Any]:
        """Mevcut agent'ları başlat"""
        return {
            "cluster": ClusterAgent(self.client, manager=self, active_cluster_id=self.active_cluster_id),
            "namespace": NamespaceAgent(self.client, manager=self, active_cluster_id=self.active_cluster_id),
            "deployment": DeploymentAgent(self.client, manager=self, active_cluster_id=self.active_cluster_id),
            "repository": RepositoryAgent(self.client, manager=self, active_cluster_id=self.active_cluster_id)

        }
    
    def _build_router_system_prompt(self) -> str:
        """Router LLM için system prompt oluştur - iyileştirilmiş context ile"""
        agent_descriptions = []
        for agent_key, agent in self.agents.items():
            agent_descriptions.append(f"- {agent_key}: {agent.category} - {agent.description}")

        agents_text = "\n".join(agent_descriptions)

        # Global context bilgisi eklendi
        context_info = ""
        if self.global_conversation_context:
            context_info = f"\n\n### SON SOHBET OZETI ###\n{self._get_global_context_summary()}\n"

        # --- YENİ İYİLEŞTİRİLMİŞ PROMPT ---
        return (
            "### ROL VE GÖREV ###\n"
            "Sen, KUBEX sisteminin Merkezi Komut Yönlendiricisisin (Triage Expert). Ana görevin, kullanıcının isteğini analiz ederek "
            "bu isteği yerine getirebilecek en uygun uzmanlık kategorisini (agent) belirlemektir.\n"

            "Görevin sadece anahtar kelimelere bakmak değil, kullanıcının asıl niyetini ve ihtiyaç duyduğu eylem türünü anlamaktır.\n\n"
            f"### MEVCUT UZMANLIK KATEGORİLERİ (AGENTLAR) ###\n{agents_text}\n"
            f"{context_info}"
            "### KARAR VERME KURALLARI ###\n"
            "1. **Niyet Analizi:** Kullanıcının isteğini dikkatlice incele. Kullanıcı bir kaynağı \"görmek/listelemek\" mi, "
            "\"oluşturmak/değiştirmek\" mi yoksa \"silmek\" mi istiyor? İsteğin odağındaki kaynak nedir (Cluster, Deployment, Namespace, Repository)?\n"
            "2. **Bağlam Takibi (Context Continuity):**\n"
            "   - Eğer sohbet geçmişi (\"SON SOHBET OZETI\") incelendiğinde, kullanıcının son etkileşimin devamı niteliğinde bir soru sorduğu açıksa "
            "(örn: \"Peki o deployment'ı ölçekle\"), yönlendirmeyi mevcut aktif agent üzerinden devam ettir. Yeni bir kategori seçimi yapma.\n"
            "   - Eğer kullanıcı açıkça konuyu değiştirirse (örn: \"Tamam, şimdi de repoları listeleyelim\"), yeni konuya uygun kategoriyi seç.\n"
            "3. **Chat Modu Kullanımı:** Eğer istek teknik bir Kubernetes işlemi (CRUD - Create, Read, Update, Delete) değilse VEYA "
            "belirsiz bir selamlama/soru ise (örn: \"Merhaba\", \"Ne yapabiliyorsun?\"), \"chat\" kategorisini seç.\n\n"
            "### ÇIKIŞ FORMATI ###\n"
            "Kararını ve gerekçeni (reasoning) içeren, YALNIZCA bir JSON objesi döndür:\n\n"
            "1. Belirli bir kategori seçeceksen:\n"
            '{"agent": "kategori_adi", "reasoning": "Kullanıcı deploymentları listelemek istediği için \'deployment\' kategorisi seçildi."}\n\n'
            "2. Genel sohbet edeceksen:\n"
            '{"agent": "chat", "reasoning": "Kullanıcı genel bir soru sordu, spesifik bir eylem talebi yok.", "response": "Ben bir Kubernetes yardımcısıyım ve yalnızca bu konuda çalışabilirim. Size nasıl yardımcı olabilirim?"}\n\n'
            "Yanıtında JSON objesi dışında KESİNLİKLE hiçbir metin veya açıklama olmasın."
        )
    
    def _get_global_context_summary(self) -> str:
        """YENI: Global conversation context'in özetini döndür"""
        if not self.global_conversation_context:
            return "Henuz bir sohbet gecmisi yok."
        
        summary_parts = []
        for i, interaction in enumerate(self.global_conversation_context[-3:], 1):  # Son 3 etkileşim
            user_msg = interaction["user"][:80] + "..." if len(interaction["user"]) > 80 else interaction["user"]
            assistant_msg = interaction["assistant"][:80] + "..." if len(interaction["assistant"]) > 80 else interaction["assistant"]
            agent_info = f"[{interaction.get('agent', 'Router')}]"
            summary_parts.append(f"{i}. {agent_info} Kullanici: {user_msg}\n   Asistan: {assistant_msg}")
        
        return "\n".join(summary_parts)
    
    def add_to_global_context(self, user_message: str, assistant_response: str, agent_name: str = "Router"):
        """YENI: Global conversation context'e yeni etkileşim ekle"""
        self.global_conversation_context.append({
            "user": user_message,
            "assistant": assistant_response,
            "agent": agent_name,
            "timestamp": "recent"
        })
        
        # Memory limitini koru (son 10 etkileşim)
        if len(self.global_conversation_context) > 10:
            self.global_conversation_context = self.global_conversation_context[-10:]
    
    def route_request(self, prompt: str) -> Union[Dict[str, Any], Generator[str, None, None]]:
        """İsteği uygun agent'a yönlendir - iyileştirilmiş context yönetimi ile"""
        print(f"[Router] İstek yönlendiriliyor: {prompt}")
        
        # Eğer aktif bir agent var ve parametre bekleniyorsa, o agent'a devam et
        if self.current_agent and self.current_agent.waiting_for_parameters:
            print(f"[Router] Mevcut agent ({self.current_agent.category}) parametre bekliyor, yönlendiriliyor")
            return self.current_agent.process_request(prompt)
        
        # YENI: Eğer aktif agent var ve kullanıcı previous response hakkında soru soruyorsa
        if self.current_agent and self._is_referring_to_previous_response(prompt):
            print(f"[Router] Kullanıcı önceki yanıt hakkında soru soruyor, mevcut agent'a yönlendiriliyor")
            return self.current_agent.process_request(prompt)
        
        # Router LLM'den kategori seçimi iste
        routing_decision = self._call_router_llm(prompt)
        selected_agent_key = routing_decision.get("agent")
        reasoning = routing_decision.get("reasoning", "")
        
        print(f"[Router] Seçilen kategori: {selected_agent_key}, Neden: {reasoning}")
        
        # Chat seçildiyse direkt yanıt ver
        if selected_agent_key == "chat":
            response_text = routing_decision.get("response", "Ben bir Kubernetes yardımcısıyım ve yalnızca bu konuda çalışabilirim. Size nasıl yardımcı olabilirim?")
            
            # YENI: Chat response'u global context'e ekle
            self.add_to_global_context(prompt, response_text, "Chat")
            
            # Current agent'ı değiştirme - context korunsun
            # self.current_agent = None  # KALDIRILDI
            
            def stream_response():
                yield response_text
            return stream_response()
        
        # Seçilen agent'ı bul ve işlemi devret
        if selected_agent_key in self.agents:
            self.current_agent = self.agents[selected_agent_key]
            
            # YENI: Agent değişiminde global context'i agent'a aktar
            self._sync_context_to_agent(self.current_agent)
            
            return self.current_agent.process_request(prompt)
        else:
            logger.warning(f"[Router] Bilinmeyen agent seçildi: {selected_agent_key}")
            error_msg = f"'{selected_agent_key}' kategorisi bulunamadı. Lütfen cluster, namespace gibi geçerli bir kategori belirtin."
            
            # YENI: Error'u da global context'e ekle
            self.add_to_global_context(prompt, error_msg, "Error")
            
            self.current_agent = None
            def error_response():
                yield error_msg
            return error_response()
    
    def _is_referring_to_previous_response(self, prompt: str) -> bool:
        """YENI: Kullanıcının önceki yanıta referans verip vermediğini kontrol et"""
        referral_keywords = [
            "bu", "bunlar", "yukarıdaki", "önceki", "az önce", "방금", "daha detay",
            "bu sonuç", "bu bilgi", "bu liste", "detayını", "açıkla", "nasıl",
            "neden", "bu cluster", "bu namespace", "hangisi", "kaç", "ne zaman",
            "daha fazla", "hakkında", "için nasıl", "bu durumda"
        ]
        
        prompt_lower = prompt.lower()
        return any(keyword in prompt_lower for keyword in referral_keywords)
    
    def _sync_context_to_agent(self, agent):
        """YENI: Global context'i agent'ın local context'ine aktar"""
        if not self.global_conversation_context:
            return
            
        # Son bir kaç etkileşimi agent'a aktar
        for interaction in self.global_conversation_context[-3:]:
            agent.add_to_conversation_context(
                interaction["user"], 
                interaction["assistant"]
            )
    
    def finalize_request(self, tool_name: str, extracted_params: dict, collected_params: dict) -> Generator[str, None, None]:
        """Parametre toplama tamamlandıktan sonra mevcut agent'a devret"""
        if self.current_agent:
            # Tool response'u collect et ve global context'e ekle
            response_generator = self.current_agent.finalize_request(tool_name, extracted_params, collected_params)
            
            full_response = ""
            for chunk in response_generator:
                full_response += chunk
                yield chunk
            
            # YENI: Tool response'u global context'e ekle
            original_request = getattr(self.current_agent, 'last_user_request', 'Tool execution')
            self.add_to_global_context(original_request, full_response, self.current_agent.category)
        else:
            error_msg = "Aktif agent bulunamadı. İşlem iptal edildi."
            self.add_to_global_context("Tool finalization", error_msg, "Error")
            def error_response():
                yield error_msg
            return error_response()
    
    def _call_router_llm(self, prompt: str) -> Dict[str, Any]:
        """Router LLM'den kategori seçimi iste - iyileştirilmiş context ile"""
        try:
            # YENI: Router için de history kullan ama sınırlı tut
            response = self.client.chat(
                user_prompt=prompt, 
                system_prompt=self.router_system_prompt, 
                use_history=True  # DEĞIŞTI: False yerine True
            )
            
            content = response.get("message", {}).get("content", "{}")
            first_brace_index = content.find('{')
            if first_brace_index == -1:
                raise ValueError("JSON bulunamadı")
            
            json_str_with_trailing_junk = content[first_brace_index:]
            decoded_json, _ = json.JSONDecoder().raw_decode(json_str_with_trailing_junk)
            return decoded_json
            
        except Exception as e:
            print(f"[Router] LLM'den geçerli yanıt alınamadı: {e}")
            return {
                "agent": "chat", 
                "reasoning": "Routing hatası",
                "response": "İsteğinizi anlayamadım, lütfen daha net ifade eder misiniz?"
            }
    
    def reset_all_contexts(self):
        """Tüm agent'ların bağlamını sıfırla - iyileştirilmiş reset"""
        for agent in self.agents.values():
            agent.reset_context()
        self.current_agent = None
        self.waiting_for_parameters = False
        
        # YENI: Global context'i tamamen sıfırlama, sadece işaret et
        self.global_conversation_context = []
        
        # YENI: Client history'yi tamamen temizle
        self.client.clear_chat_history()
        
        print("[Router] Tüm agent bağlamları ve global context sıfırlandı")
    
    def soft_reset_contexts(self):
        """YENI: Soft reset - sadece current operations'ı sıfırla, conversation memory'yi koru"""
        if self.current_agent:
            self.current_agent.waiting_for_parameters = False
            self.current_agent.current_tool_context = None
        
        self.waiting_for_parameters = False
        print("[Router] Soft reset tamamlandı - conversation memory korundu")
    
    def get_current_status(self) -> Dict[str, Any]:
        """Mevcut durumu döndür - iyileştirilmiş status bilgisi"""
        base_status = {
            "active_agent": self.current_agent.category if self.current_agent else None,
            "waiting_for_parameters": self.current_agent.waiting_for_parameters if self.current_agent else False,
            "tool_context": self.current_agent.current_tool_context if self.current_agent else None,
            "global_context_size": len(self.global_conversation_context),  # YENI
            "last_interactions": len([ctx for ctx in self.global_conversation_context if ctx.get("agent") != "Chat"])  # YENI
        }
        
        return base_status
    
    def get_available_categories(self) -> List[str]:
        """Mevcut kategorileri listele"""
        return list(self.agents.keys())
    
    def get_conversation_summary(self) -> str:
        if not self.global_conversation_context:
            return "Henüz bir sohbet geçmişi bulunmamaktadır."
        
        summary = f"Toplam {len(self.global_conversation_context)} etkileşim gerçekleşti.\n\n"
        summary += "Son etkileşimler:\n"
        summary += self._get_global_context_summary()
        
        return summary
    
    def set_active_cluster(self, cluster_id: str, cluster_name: Optional[str] = None):
        """Aktif cluster ID'yi merkezi olarak ayarlar."""
        self.active_cluster_id = cluster_id
        self.active_cluster_name = cluster_name
        print(f"[AgentManager] Aktif cluster UI tarafından ayarlandı: ID={cluster_id}, Adı={cluster_name}")

        # YENİ EKLENTİ: Agent'ları güncelle
        for agent in self.agents.values():
            if hasattr(agent, 'update_active_cluster'):
                agent.update_active_cluster(cluster_id)

    def get_cluster_list_for_ui(self) -> List[Dict[str, Any]]:
        """LLM olmadan doğrudan cluster listesini çeker."""
        try:
            cluster_agent: ClusterAgent = self.agents.get("cluster")
            if not cluster_agent:
                print("Cluster agent bulunamadı.")
                return []

            api_response = cluster_agent.cluster_api.list_clusters()

            if isinstance(api_response, dict):
                if "records" in api_response and isinstance(api_response.get("records"), list):
                    return api_response["records"]
                
                elif "data" in api_response and isinstance(api_response.get("data"), list):
                    logger.warning("API formatı 'data' anahtarını kullanıyor. Beklenen 'records' idi.")
                    return api_response["data"]
                
                elif "items" in api_response and isinstance(api_response.get("items"), list):
                    logger.warning("API formatı 'items' anahtarını kullanıyor. Beklenen 'records' idi.")
                    return api_response["items"]
                
                else:
                    print(f"API yanıtı sözlük formatında ancak beklenen liste anahtarı ('records', 'data', 'items') bulunamadı. Anahtarlar: {api_response.keys()}")
                    return []

            elif isinstance(api_response, list):
                return api_response

        except Exception as e:
            print(f"UI için cluster listesi çekilemedi: {e}")
            return []
        
        return []

    # --- YENİ METOD: Otomatik Enjeksiyon İçin ---
    def get_contextual_parameters(self) -> Dict[str, Any]:
        """Diğer agent'ların kullanması için bağlamsal parametreleri döndürür."""
        params = {}
        if self.active_cluster_id:
            params["cluster_id"] = self.active_cluster_id
        return params