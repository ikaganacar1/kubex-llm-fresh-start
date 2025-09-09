import logging
import json
from typing import Dict, Any, List, Generator, Union, Optional
from ollama import OllamaClient
from agents.cluster_agent import ClusterAgent
from agents.namespace_agent import NamespaceAgent

logger = logging.getLogger(__name__)

class AgentManager:
    """Tüm agent'ları yöneten merkezi sınıf"""
    
    def __init__(self, client: OllamaClient):
        self.client = client
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
        """Router LLM için system prompt oluştur"""
        agent_descriptions = []
        for agent_key, agent in self.agents.items():
            agent_descriptions.append(f"- {agent_key}: {agent.category} - {agent.description}")
        
        agents_text = "\n".join(agent_descriptions)
        
        return (
            "Sen bir Kubernetes uzmanı router asistanısın. Görevi, kullanıcının isteğini analiz ederek "
            "hangi kategorideki işlemlerin yapılacağını belirlemektir.\n\n"
            f"Mevcut kategoriler:\n{agents_text}\n\n"
            "Kullanıcının isteğini analiz ettikten sonra, YALNIZCA bir JSON objesi döndür:\n\n"
            "1. Belirli bir kategori seçeceksen:\n"
            '{"agent": "kategori_adi", "reasoning": "neden_bu_kategori_secildi"}\n\n'
            "2. Genel sohbet edeceksen:\n"
            '{"agent": "chat", "reasoning": "genel_sohbet_nedeni", "response": "kullaniciya_verilecek_cevap"}\n\n'
            "Yanıtında JSON objesi dışında KESİNLİKLE hiçbir metin, açıklama veya formatlama işareti olmasın."
        )
    
    def route_request(self, prompt: str) -> Union[Dict[str, Any], Generator[str, None, None]]:
        """İsteği uygun agent'a yönlendir"""
        logger.info(f"[Router] İstek yönlendiriliyor: {prompt}")
        
        # Eğer aktif bir agent var ve parametre bekleniyorsa, o agent'a devam et
        if self.current_agent and self.current_agent.waiting_for_parameters:
            logger.info(f"[Router] Mevcut agent ({self.current_agent.category}) parametre bekliyor, yönlendiriliyor")
            return self.current_agent.process_request(prompt)
        
        # Router LLM'den kategori seçimi iste
        routing_decision = self._call_router_llm(prompt)
        selected_agent_key = routing_decision.get("agent")
        reasoning = routing_decision.get("reasoning", "")
        
        logger.info(f"[Router] Seçilen kategori: {selected_agent_key}, Neden: {reasoning}")
        
        # Chat seçildiyse direkt yanıt ver
        if selected_agent_key == "chat":
            response_text = routing_decision.get("response", "Size nasıl yardımcı olabilirim?")
            self.current_agent = None
            def stream_response():
                yield response_text
            return stream_response()
        
        # Seçilen agent'ı bul ve işlemi devret
        if selected_agent_key in self.agents:
            self.current_agent = self.agents[selected_agent_key]
            return self.current_agent.process_request(prompt)
        else:
            logger.warning(f"[Router] Bilinmeyen agent seçildi: {selected_agent_key}")
            self.current_agent = None
            def error_response():
                yield f"'{selected_agent_key}' kategorisi bulunamadı. Lütfen cluster, namespace gibi geçerli bir kategori belirtin."
            return error_response()
    
    def finalize_request(self, tool_name: str, extracted_params: dict, collected_params: dict) -> Generator[str, None, None]:
        """Parametre toplama tamamlandıktan sonra mevcut agent'a devret"""
        if self.current_agent:
            return self.current_agent.finalize_request(tool_name, extracted_params, collected_params)
        else:
            def error_response():
                yield "Aktif agent bulunamadı. İşlem iptal edildi."
            return error_response()
    
    def _call_router_llm(self, prompt: str) -> Dict[str, Any]:
        """Router LLM'den kategori seçimi iste"""
        try:
            response = self.client.chat(
                user_prompt=prompt, 
                system_prompt=self.router_system_prompt, 
                use_history=False  # Router için history kullanmıyoruz
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
        """Tüm agent'ların bağlamını sıfırla"""
        for agent in self.agents.values():
            agent.reset_context()
        self.current_agent = None
        self.waiting_for_parameters = False
        self.client.clear_chat_history()
        logger.info("[Router] Tüm agent bağlamları sıfırlandı")
    
    def get_current_status(self) -> Dict[str, Any]:
        """Mevcut durumu döndür"""
        if self.current_agent:
            return {
                "active_agent": self.current_agent.category,
                "waiting_for_parameters": self.current_agent.waiting_for_parameters,
                "tool_context": self.current_agent.current_tool_context
            }
        else:
            return {
                "active_agent": None,
                "waiting_for_parameters": False,
                "tool_context": None
            }
    
    def get_available_categories(self) -> List[str]:
        """Mevcut kategorileri listele"""
        return list(self.agents.keys())
