from typing import Dict, Any, Generator, Optional
from base_agent import BaseAgent
from tools.repository_tools.repository_tools import RepositoryAPITools
from tools.repository_tools.tool_manager import RepositoryToolManager
import logging

logger = logging.getLogger(__name__)

class RepositoryAgent(BaseAgent):
    """Kubernetes Helm Repository işlemleri için özelleşmiş agent - İyileştirilmiş context yönetimi ile"""
    
    def __init__(self, client,active_cluster_id, manager: Optional[Any] = None):
        super().__init__(
            client=client,
            category="Helm Repository",
            description="Helm repository'lerini yönetir, chart'ları listeler ve yükler.",
            manager=manager 
        )
        self.active_cluster_id = active_cluster_id
        self.tool_manager = RepositoryToolManager(active_cluster_id = active_cluster_id)
        # Client'tan base_url'i al veya default kullan
        base_url = getattr(client, 'base_url', 'http://10.67.67.195:8000')
        self.repository_api = RepositoryAPITools(base_url=base_url, active_cluster_id = active_cluster_id)

    def update_active_cluster(self, cluster_id: str):
        self.active_cluster_id = cluster_id
        self.tool_manager = RepositoryToolManager(active_cluster_id=cluster_id)
        self.repository_api.active_cluster_id = cluster_id
        print(f"[{self.category}] Active cluster updated.")


    def get_tools(self) -> Dict[str, Any]:
        """Repository işlemleri için mevcut araçları döndürür"""
        return self.tool_manager.tools
    
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any], original_request: str = None) -> Generator[str, None, None]:
        """Repository aracını çalıştırır - iyileştirilmiş context ile"""
        print("\n" + "="*50)
        print(f"[{self.category}] Araç çalıştırılıyor: '{tool_name}', Parametreler: {parameters}")
        print("="*50 + "\n")
        
        # Original request'i güncelle
        if original_request:
            self.last_user_request = original_request
        
        tool_function = getattr(self.repository_api, tool_name, None)
        if not tool_function:
            logger.error(f"[{self.category}] '{tool_name}' aracı için fonksiyon bulunamadı.")
            error_msg = f"'{tool_name}' adlı aracın çalıştırma metodu bulunamadı."
            return self._create_error_response(error_msg)
        
        try:
            result = tool_function(**parameters)
            
            # Tool result'u context ile birlikte summarize et
            response_generator = self._summarize_result_for_user(result, self.last_user_request)
            
            # Response'u collect et ve context'e ekle
            full_response = ""
            for chunk in response_generator:
                full_response += chunk
                yield chunk
            
            # Tool execution'ı conversation context'e ekle
            if self.last_user_request:
                self.add_to_conversation_context(self.last_user_request, full_response)
                
        except Exception as e:
            logger.error(f"[{self.category}] Araç çalıştırılırken hata oluştu ({tool_name}): {e}")
            error_msg = f"Araç çalıştırılırken hata oluştu: {str(e)}"
            
            # Error'u da context'e ekle
            if self.last_user_request:
                self.add_to_conversation_context(self.last_user_request, error_msg)
                
            return self._create_error_response(error_msg)