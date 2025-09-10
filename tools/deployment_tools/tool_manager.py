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
                "summary": "Tüm namespace'lerdeki veya belirli bir namespace'deki deployment'ları özet bilgileriyle listeler.",
                "description": (
                    "Bu araç, cluster'daki tüm deployment'ların bir listesini döndürür. Her bir deployment için adı, "
                    "bulunduğu namespace, istenen ve hazır olan replica sayıları (örn: 3/3) ve ne kadar süredir çalıştığı "
                    "gibi temel durum bilgilerini içerir. Cluster'daki uygulamaların genel bir görünümünü elde etmek için "
                    "kullanılır. Örneğin, 'Tüm deployment'ları listele' veya 'default namespace'indeki deployment'lar nelerdir?'"
                    "gibi talepler için idealdir."
                ),
                "method": "GET",
                "path": f"/deployments/{self.active_cluster_id}/instant",
                "parameters": []
            },
            
            "show_deployment": {
                "summary": "Belirli bir deployment'ın genel durumunu ve üst düzey bilgilerini gösterir.",
                "description": (
                    "Bu araç, ismi ve namespace'i belirtilen tek bir deployment hakkında özet durum bilgisi sağlar. "
                    "Döndürdüğü bilgiler arasında etiketler (labels), seçiciler (selectors), replica durumu ve son olaylar (events) "
                    "gibi genel veriler bulunur. Bir deployment'ın sağlığını hızlıca kontrol etmek için kullanılır. "
                    "Daha teknik ve detaylı konfigürasyon (örn: environment variable'lar) için 'get_deployment_config' aracı kullanılmalıdır."
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
                "summary": "Bir deployment'ın replica sayısını (çalışan pod kopyası) değiştirir.",
                "description": (
                    "Bu araç, bir deployment'ın pod sayısını (replica) belirtilen sayıya ayarlar. Bu işlem, uygulamayı "
                    "daha fazla trafik için büyütmek (scale up) veya kaynak tasarrufu için küçültmek (scale down) amacıyla kullanılır. "
                    "Kullanıcı 'nginx deployment'ını 5 pod'a çıkar' gibi bir talepte bulunduğunda bu araç seçilmelidir."
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
                    "ve yerlerine yenileri oluşturulur. Bu işlem, konfigürasyon değişikliklerini uygulamak veya "
                    "uygulamanın takıldığı/yanıt vermediği durumlarda 'temiz bir başlangıç' yapmak için kullanılır. "
                    "Örneğin, 'frontend-api deployment'ını yeniden başlat' talebi için idealdir."
                ),
                "method": "POST",
                "path": "/deployments/redeploy",
                "parameters": [
                    {
                        "name": "deployment_name",
                        "in": "body",
                        "required": True,
                        "type": "string",
                        "description": "Yeniden dağıtılacak (restart edilecek) deployment'ın adı."
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
                    "Bu araç, bir deployment'ın kaynak tanımının (resource definition) tamamını döndürür. Bu, kullanılan "
                    "container imajı, ortam değişkenleri (environment variables), volume bağlantıları, kaynak limitleri "
                    "gibi tüm teknik ayarları içerir. Hata ayıklama veya bir deployment'ın nasıl yapılandırıldığını "
                    "derinlemesine anlamak için kullanılır. 'show_deployment' aracından çok daha detaylıdır."
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
                    "bir listesini döndürür. Her pod için isim, mevcut durum (Running, Pending, CrashLoopBackOff vb.), "
                    "IP adresi ve ne kadar süredir çalıştığı gibi bilgileri içerir. Uygulamanın bireysel kopyalarında "
                    "hata ayıklamak için kullanılır."
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
                "summary": "Bir deployment'ın kullandığı container imajını (versiyonunu) günceller.",
                "description": (
                    "Bu araç, bir deployment'ın pod'larında çalışan uygulamanın container imajını yeni bir versiyonla "
                    "değiştirmek için kullanılır. Bu işlem, yeni bir uygulama sürümüne geçmek için standart yöntemdir ve "
                    "yeni imajla pod'ların güncellendiği bir 'rolling update' tetikler. Örneğin, 'backend-api'nin imajını 'app:v1.2' yap'."
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
                        "description": "Kullanılacak yeni container imajının tam adı ve etiketi (tag). Örneğin: 'harbor.bulut.ai/liman/app:v1.2'"
                    }
                ]
            }
        }