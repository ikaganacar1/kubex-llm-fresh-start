import logging
import json
from typing import Dict, Any, List, Generator, Union, Optional
from ollama import OllamaClient
from agents.cluster_agent import ClusterAgent
from agents.namespace_agent import NamespaceAgent

logger = logging.getLogger(__name__)

class AgentManager:
    """Tüm agent'ları yöneten merkezi sınıf - İyileştirilmiş global context yönetimi ile"""
    
    def __init__(self, client: OllamaClient):
        self.client = client
        
        self.global_conversation_context = []
        self.session_active = True
        
        self.agents = self._initialize_agents()
        self.current_agent = None
        self.waiting_for_parameters = False
        self.router_system_prompt = self._build_router_system_prompt()
    
    def _initialize_agents(self) -> Dict[str, Any]:
        """Mevcut agent'ları başlat"""
        return {
            "cluster": ClusterAgent(self.client),
            "namespace": NamespaceAgent(self.client),
            # Gelecekte eklenecekler:
            # "deployment": DeploymentAgent(self.client),
            # "service": ServiceAgent(self.client),
            # "pod": PodAgent(self.client),
        }
    
    def _build_router_system_prompt(self) -> str:
        """Router LLM için system prompt oluştur - iyileştirilmiş context ile"""
        agent_descriptions = []
        for agent_key, agent in self.agents.items():
            agent_descriptions.append(f"- {agent_key}: {agent.category} - {agent.description}")
        
        agents_text = "\n".join(agent_descriptions)
        
        # YENI: Global context bilgisi eklendi
        context_info = ""
        if self.global_conversation_context:
            context_info = f"\n\nSON SOHBET OZETI:\n{self._get_global_context_summary()}\n"
        
        return (
            "Sen bir Kubernetes uzmanı router asistanısın. Görevi, kullanıcının isteğini analiz ederek "
            "hangi kategorideki işlemlerin yapılacağını belirlemektir.\n\n"
            f"Mevcut kategoriler:\n{agents_text}\n\n"
            f"{context_info}"
            "ONEMLI: Kullanicinin onceki sohbet baglamini ve referanslarini unutma!\n"
            "Eger kullanici onceki bir yanıta referans veriyor veya soru soruyor ise, "
            "mevcut aktif agent varsa ona yonlendir, yoksa chat modunda cevapla.\n\n"
            "Kullanıcının isteğini analiz ettikten sonra, YALNIZCA bir JSON objesi döndür:\n\n"
            "1. Belirli bir kategori seçeceksen:\n"
            '{"agent": "kategori_adi", "reasoning": "neden_bu_kategori_secildi"}\n\n'
            "2. Genel sohbet edeceksen:\n"
            '{"agent": "chat", "reasoning": "genel_sohbet_nedeni", "response": "kullaniciya_verilecek_cevap"}\n\n'
            "Yanıtında JSON objesi dışında KESİNLİKLE hiçbir metin, açıklama veya formatlama işareti olmasın."
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
        logger.info(f"[Router] İstek yönlendiriliyor: {prompt}")
        
        # Eğer aktif bir agent var ve parametre bekleniyorsa, o agent'a devam et
        if self.current_agent and self.current_agent.waiting_for_parameters:
            logger.info(f"[Router] Mevcut agent ({self.current_agent.category}) parametre bekliyor, yönlendiriliyor")
            return self.current_agent.process_request(prompt)
        
        # YENI: Eğer aktif agent var ve kullanıcı previous response hakkında soru soruyorsa
        if self.current_agent and self._is_referring_to_previous_response(prompt):
            logger.info(f"[Router] Kullanıcı önceki yanıt hakkında soru soruyor, mevcut agent'a yönlendiriliyor")
            return self.current_agent.process_request(prompt)
        
        # Router LLM'den kategori seçimi iste
        routing_decision = self._call_router_llm(prompt)
        selected_agent_key = routing_decision.get("agent")
        reasoning = routing_decision.get("reasoning", "")
        
        logger.info(f"[Router] Seçilen kategori: {selected_agent_key}, Neden: {reasoning}")
        
        # Chat seçildiyse direkt yanıt ver
        if selected_agent_key == "chat":
            response_text = routing_decision.get("response", "Size nasıl yardımcı olabilirim?")
            
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
            logger.error(f"[Router] LLM'den geçerli yanıt alınamadı: {e}")
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
        
        logger.info("[Router] Tüm agent bağlamları ve global context sıfırlandı")
    
    def soft_reset_contexts(self):
        """YENI: Soft reset - sadece current operations'ı sıfırla, conversation memory'yi koru"""
        if self.current_agent:
            self.current_agent.waiting_for_parameters = False
            self.current_agent.current_tool_context = None
        
        self.waiting_for_parameters = False
        logger.info("[Router] Soft reset tamamlandı - conversation memory korundu")
    
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
        """YENI: Kullanıcı için conversation summary döndür"""
        if not self.global_conversation_context:
            return "Henüz bir sohbet geçmişi bulunmamaktadır."
        
        summary = f"Toplam {len(self.global_conversation_context)} etkileşim gerçekleşti.\n\n"
        summary += "Son etkileşimler:\n"
        summary += self._get_global_context_summary()
        
        return summary