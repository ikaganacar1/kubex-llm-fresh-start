# agent_manager.py

import logging
from typing import Dict, Any, Generator, Union, Optional, List
from ollama import OllamaClient
from agents.cluster_agent import ClusterAgent
from agents.namespace_agent import NamespaceAgent
from agents.deployment_agent import DeploymentAgent
from agents.repository_agent import RepositoryAgent

from llm_services.router_llm_service import RouterLLMService

logger = logging.getLogger(__name__)

class AgentManager:
    def __init__(self, client: OllamaClient):
        self.client = client
        self.global_conversation_context = []
        self.session_active = True
        self.active_cluster_id: Optional[str] = "None"
        self.active_cluster_name: Optional[str] = None
        
        self.router_llm_service = RouterLLMService(self.client)
        
        self.agents = self._initialize_agents()
        self.current_agent = None
        self.waiting_for_parameters = False

    def _initialize_agents(self) -> Dict[str, Any]:
        agent_classes = {
            "cluster": ClusterAgent,
            "namespace": NamespaceAgent,
            "deployment": DeploymentAgent,
            "repository": RepositoryAgent
        }
        initialized_agents = {}
        for name, agent_class in agent_classes.items():
            initialized_agents[name] = agent_class(
                client=self.client, 
                manager=self, 
                active_cluster_id=self.active_cluster_id
            )
        return initialized_agents
    
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
        print("\n" + "="*50)
        print(f"[Router] İstek yönlendiriliyor: {prompt}")
        print("="*50 + "\n")
        
        # Eğer aktif bir agent var ve parametre bekleniyorsa, o agent'a devam et
        if self.current_agent and self.current_agent.waiting_for_parameters:
            print(f"[Router] Mevcut agent ({self.current_agent.category}) parametre bekliyor, yönlendiriliyor")
            return self.current_agent.process_request(prompt)
        
        
        routing_decision = self.router_llm_service.get_routing_decision(
            user_prompt=prompt,
            agents=self.agents,
            context_summary=self._get_global_context_summary()
        )
        selected_agent_key = routing_decision.get("agent")
        reasoning = routing_decision.get("reasoning", "")
        
        print(f"[Router] Seçilen kategori: {selected_agent_key}, Neden: {reasoning}")
        
        # Chat seçildiyse direkt yanıt ver
        if selected_agent_key == "chat":
            response_text = routing_decision.get("response", "Ben bir Kubernetes yardımcısıyım ve yalnızca bu konuda çalışabilirim. Size nasıl yardımcı olabilirim?")
            
            self.add_to_global_context(prompt, response_text, "Chat")
                        
            def stream_response():
                yield response_text
            return stream_response()
        
        if selected_agent_key in self.agents:
            self.current_agent = self.agents[selected_agent_key]
            
            self._sync_context_to_agent(self.current_agent)
            
            return self.current_agent.process_request(prompt)
        else:
            logger.warning(f"[Router] Bilinmeyen agent seçildi: {selected_agent_key}")
            error_msg = f"'{selected_agent_key}' kategorisi bulunamadı. Lütfen cluster, namespace gibi geçerli bir kategori belirtin."
            
            self.add_to_global_context(prompt, error_msg, "Error")
            
            self.current_agent = None
            def error_response():
                yield error_msg
            return error_response()
    
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
        print("\n" + "="*50)
        print("[Router] Tüm agent bağlamları ve global context sıfırlandı")
        print("="*50 + "\n")
    
    def soft_reset_contexts(self):
        """YENI: Soft reset - sadece current operations'ı sıfırla, conversation memory'yi koru"""
        if self.current_agent:
            self.current_agent.waiting_for_parameters = False
            self.current_agent.current_tool_context = None
        
        self.waiting_for_parameters = False
        print("\n" + "="*50)
        print("[Router] Soft reset tamamlandı - conversation memory korundu")
        print("="*50 + "\n")
    
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
        print("\n" + "="*50)
        print(f"[AgentManager] Aktif cluster UI tarafından ayarlandı: ID={cluster_id}, Adı={cluster_name}")
        print("="*50 + "\n")
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
                clusters_data = api_response.get("clusters")
                clusters_data = clusters_data["records"]
                
                if isinstance(clusters_data, list):
                    return clusters_data
                else:
                    data_type = type(clusters_data).__name__
                    print(f"HATA: API yanıtındaki 'clusters' anahtarının değeri bir liste değil. Gelen veri tipi: {data_type}.")
                    return []
            
            elif isinstance(api_response, list):
                return api_response

        except Exception as e:
            print(f"UI için cluster listesi çekilemedi: {e}")
            return []
        
        return []
