from typing import Dict, Any, Generator, Optional
from base_agent import BaseAgent
from tools.namespace_tools.namespace_tools import NamespaceAPITools
from tools.namespace_tools.tool_manager import NamespaceToolManager
import logging

logger = logging.getLogger(__name__)

class NamespaceAgent(BaseAgent):
    """Kubernetes Namespace işlemleri için özelleşmiş agent - İyileştirilmiş context yönetimi ile"""
    
    def __init__(self, client, manager: Optional[Any] = None):
        super().__init__(
            client=client,
            category="Kubernetes Namespace",
            description="Kubernetes namespace'lerini yönetir, listeler ve detaylarını gösterir.",
            manager=manager 
        )
        self.tool_manager = NamespaceToolManager()
        # Client'tan base_url'i al veya default kullan
        base_url = getattr(client, 'base_url', 'http://10.67.67.195:8000')
        self.namespace_api = NamespaceAPITools(base_url=base_url)
    
    def get_tools(self) -> Dict[str, Any]:
        """Namespace işlemleri için mevcut araçları döndürür"""
        return self.tool_manager.tools
    
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any], original_request: str = None) -> Generator[str, None, None]:
        """Namespace aracını çalıştırır - iyileştirilmiş context ile"""
        logger.info(f"[{self.category}] Araç çalıştırılıyor: '{tool_name}', Parametreler: {parameters}")
        
        # Original request'i güncelle
        if original_request:
            self.last_user_request = original_request
        
        tool_function = getattr(self.namespace_api, tool_name, None)
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