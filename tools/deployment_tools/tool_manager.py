# tools/deployment_tools/tool_manager.py - Test için düzeltilmiş versiyon

from typing import Dict, Any

class DeploymentToolManager:
    """Deployment araçlarını yöneten API tool manager"""
    
    def __init__(self, active_cluster_id: str):
        self.active_cluster_id = active_cluster_id
        self.tools = self._define_tools()

    def _define_tools(self) -> Dict[str, Any]:
        """Deployment işlemleri için mevcut araçları tanımlar"""
        return {
            "list_deployments": {
                "summary": "Tüm namespace'lerdeki deployment'ları özet bilgileriyle listeler.",
                "description": (
                    "Bu araç, cluster'daki tüm deployment'ların bir listesini döndürür. Her bir deployment için adı, "
                    "bulunduğu namespace, istenen ve hazır olan replica sayıları (örn: 3/3) ve ne kadar süredir çalıştığı "
                    "gibi temel durum bilgilerini içerir."
                ),
                "method": "GET",
                "path": f"/deployments/{self.active_cluster_id}/instant",
                "parameters": []
            },
            
            "show_deployment": {
                "summary": "Belirli bir deployment'ın genel durumunu ve üst düzey bilgilerini gösterir.",
                "description": (
                    "Bu araç, ismi ve namespace'i belirtilen tek bir deployment hakkında özet durum bilgisi sağlar."
                ),
                "method": "GET",
                "path": "/deployments/show",
                "parameters": [
                    {
                        "name": "deployment_name",
                        "in": "query",
                        "required": True,
                        "type": "string",
                        "description": "Detayları görüntülenecek deployment'ın tam adı."
                    },
                    {
                        "name": "namespace",
                        "in": "query", 
                        "required": True,
                        "type": "string",
                        "description": "Deployment'ın bulunduğu namespace'in adı, örneğin 'default'."
                    }
                ]
            },
            
            "scale_deployment": {
                "summary": "Bir deployment'ın replica sayısını değiştirir.",
                "description": (
                    "Bu araç, bir deployment'ın pod sayısını (replica) belirtilen sayıya ayarlar. Bu işlem, uygulamayı "
                    "daha fazla trafik için büyütmek veya kaynak tasarrufu için küçültmek amacıyla kullanılır."
                ),
                "method": "POST",
                "path": "/deployments/scale",
                "parameters": [
                    {
                        "name": "deployment_name",
                        "in": "body",
                        "required": True,
                        "type": "string",
                        "description": "Ölçeklendirilecek deployment'ın adı."
                    },
                    {
                        "name": "namespace",
                        "in": "body",
                        "required": True, 
                        "type": "string",
                        "description": "Deployment'ın bulunduğu namespace'in adı."
                    },
                    {
                        "name": "replicas",
                        "in": "body",
                        "required": True,
                        "type": "integer",
                        "description": "Ulaşılması hedeflenen yeni replica sayısı. Örneğin: 3, 5, 10."
                    }
                ]
            },
            
            "redeploy_deployment": {
                "summary": "Bir deployment'ı yeniden başlatarak çalışan tüm pod'ları yeniler.",
                "description": (
                    "Bu araç, bir deployment için 'rolling restart' işlemi tetikler. Mevcut pod'lar sırayla sonlandırılır "
                    "ve yerlerine yenileri oluşturulur."
                ),
                "method": "POST",
                "path": "/deployments/redeploy",
                "parameters": [
                    {
                        "name": "deployment_name",
                        "in": "body",
                        "required": True,
                        "type": "string",
                        "description": "Yeniden dağıtılacak deployment'ın adı."
                    },
                    {
                        "name": "namespace",
                        "in": "body",
                        "required": True,
                        "type": "string", 
                        "description": "Deployment'ın bulunduğu namespace'in adı."
                    }
                ]
            },
            
            "get_deployment_config": {
                "summary": "Bir deployment'ın tam ve detaylı YAML/JSON yapılandırmasını alır.",
                "description": (
                    "Bu araç, bir deployment'ın kaynak tanımının tamamını döndürür. Bu, kullanılan "
                    "container imajı, ortam değişkenleri, volume bağlantıları, kaynak limitleri "
                    "gibi tüm teknik ayarları içerir."
                ),
                "method": "GET",
                "path": "/deployments/config",
                "parameters": [
                    {
                        "name": "deployment_name",
                        "in": "query",
                        "required": True,
                        "type": "string",
                        "description": "Konfigürasyonu alınacak deployment'ın adı."
                    },
                    {
                        "name": "namespace",
                        "in": "query",
                        "required": True,
                        "type": "string",
                        "description": "Deployment'ın bulunduğu namespace'in adı."
                    }
                ]
            },
            
            "get_deployment_pods": {
                "summary": "Belirli bir deployment tarafından yönetilen tüm pod'ları listeler.",
                "description": (
                    "Bu araç, belirtilen deployment'a ait olan ve şu anda çalışan veya çalışmaya çalışan tüm pod'ların "
                    "bir listesini döndürür."
                ),
                "method": "GET",
                "path": "/deployments/{deployment_name}/pods",
                "parameters": [
                    {
                        "name": "namespace_name",
                        "in": "query",
                        "required": True,
                        "type": "string",
                        "description": "Deployment'ın ve pod'ların bulunduğu namespace'in adı."
                    },
                    {
                        "name": "deployment_name",
                        "in": "path",
                        "required": True,
                        "type": "string",
                        "description": "Pod'ları listelenecek olan deployment'ın adı."
                    }
                ]
            },
            
            "update_deployment_image": {
                "summary": "Bir deployment'ın kullandığı container imajını günceller.",
                "description": (
                    "Bu araç, bir deployment'ın pod'larında çalışan uygulamanın container imajını yeni bir versiyonla "
                    "değiştirmek için kullanılır."
                ),
                "method": "PATCH",
                "path": "/deployments/image",
                "parameters": [
                    {
                        "name": "deployment_name",
                        "in": "body",
                        "required": True,
                        "type": "string",
                        "description": "İmajı güncellenecek deployment'ın adı."
                    },
                    {
                        "name": "namespace",
                        "in": "body",
                        "required": True,
                        "type": "string",
                        "description": "Deployment'ın bulunduğu namespace'in adı."
                    },
                    {
                        "name": "image",
                        "in": "body",
                        "required": True,
                        "type": "string",
                        "description": "Kullanılacak yeni container imajının tam adı ve etiketi. Örneğin: 'harbor.bulut.ai/liman/app:v1.2'"
                    }
                ]
            }
        }