from typing import Dict, Any

class NamespaceToolManager:
    """Namespace tool'larını yönetin API tool manager"""
    
    def __init__(self):
        self.tools = self._define_tools()
    
    def _define_tools(self) -> Dict[str, Any]:
        """Namespace işlemleri için mevcut tool'ları tanımla"""
        return {
            "list_namespaces": {
                "summary": "Belirtilen cluster'daki tüm namespace'leri listeler",
                "description": "Kubernetes cluster'ındaki tüm namespace'lerin listesini alır",
                "method": "GET",
                "path": "/namespaces/{cluster_id}/instant",
                "parameters": [
                    {
                        "name": "cluster_id",
                        "in": "path",
                        "required": True,
                        "type": "string",
                        "description": "Cluster'ın benzersiz kimliği (UUID formatında)"
                    }
                ]
            },
            
            "get_namespace_summary": {
                "summary": "Namespace'lerin pod durumu özet bilgilerini alır",
                "description": "Her namespace için pod sayıları, durumları ve genel istatistikleri gösterir",
                "method": "GET", 
                "path": "/namespaces/summary/{cluster_id}",
                "parameters": [
                    {
                        "name": "cluster_id",
                        "in": "path",
                        "required": True,
                        "type": "string",
                        "description": "Cluster'ın benzersiz kimliği (UUID formatında)"
                    }
                ]
            },
            
            "show_namespace": {
                "summary": "Belirli bir namespace'in detaylarını gösterir",
                "description": "Belirtilen namespace'in ayrıntılı bilgilerini ve yapılandırmasını alır",
                "method": "GET",
                "path": "/namespaces/show",
                "parameters": [
                    {
                        "name": "namespace_name",
                        "in": "query",
                        "required": True,
                        "type": "string", 
                        "description": "Detayları görüntülenecek namespace'in adı"
                    },
                    {
                        "name": "cluster_id",
                        "in": "query",
                        "required": True,
                        "type": "string",
                        "description": "Cluster'ın benzersiz kimliği (UUID formatında)"
                    }
                ]
            }
        }