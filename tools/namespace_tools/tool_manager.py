from typing import Dict, Any

class NamespaceToolManager:
    """Namespace araçlarını yöneten API tool manager"""
    
    def __init__(self, active_cluster_id: str):
        self.active_cluster_id = active_cluster_id
        self.tools = self._define_tools()

    def _define_tools(self) -> Dict[str, Any]:
        """Namespace işlemleri için mevcut araçları tanımlar"""
        return {
            "list_namespaces": {
                "summary": "Aktif Kubernetes cluster'ındaki tüm namespace'lerin isimlerini listeler.",
                "description": (
                    "Bu araç, belirtilen ve aktif olan Kubernetes cluster'ı içerisindeki tüm namespace'lerin "
                    "sadece isimlerinden oluşan bir liste döndürür. Kullanıcı, cluster'da hangi namespace'lerin "
                    "mevcut olduğunu öğrenmek istediğinde bu araç kullanılmalıdır. Örneğin, 'Hangi namespace'ler var?' "
                    "veya 'Mevcut namespace'leri listele' gibi talepler için idealdir."
                ),
                "method": "GET",
                "path": f"/namespaces/{self.active_cluster_id}/instant",
                "parameters": []
            },
            
            "get_namespace_summary": {
                "summary": "Tüm namespace'ler için pod ve kaynak kullanım özetlerini getirir.",
                "description": (
                    "Bu araç, cluster'daki her bir namespace için pod'ların durumlarına göre (örneğin; çalışan, bekleyen, "
                    "başarısız olan pod sayıları) bir özet rapor sunar. Cluster'ın genel sağlık durumunu hızlıca "
                    "gözden geçirmek veya hangi namespace'de anormal bir durum olduğunu tespit etmek için kullanılır. "
                    "Örneğin, 'Tüm namespace'lerdeki pod durumlarını özetle' veya 'Hangi namespace'de sorunlu pod var?' "
                    "gibi talepler için uygundur."
                ),
                "method": "GET", 
                "path": f"/namespaces/summary/{self.active_cluster_id}",
                "parameters": []
            },
            
            "show_namespace": {
                "summary": "İsmi belirtilen tek bir namespace'in ayrıntılı yapılandırma ve durum bilgilerini gösterir.",
                "description": (
                    "Bu araç, belirli bir namespace'in tüm detaylarını getirir. Bu detaylar arasında namespace'in "
                    "mevcut durumu (phase, örn: 'Active'), etiketleri (labels), notasyonları (annotations) ve "
                    "oluşturulma tarihi (creation timestamp) gibi yapılandırma bilgileri bulunur. Kullanıcı tek bir "
                    "namespace hakkında derinlemesine bilgi almak istediğinde bu araç seçilmelidir. "
                    "Örneğin, 'varsayılan (default) namespace'inin etiketlerini göster' veya 'kube-system namespace'inin "
                    "detayları nelerdir?' gibi spesifik talepler için kullanılır."
                ),
                "method": "GET",
                "path": "/namespaces/show",
                "parameters": [
                    {
                        "name": "namespace_name",
                        "in": "query",
                        "required": True,
                        "type": "string", 
                        "description": (
                            "Detayları görüntülenecek olan namespace'in tam adı. Örneğin: 'default', 'production', 'kube-public'."
                        )
                    },
                ]
            }
        }