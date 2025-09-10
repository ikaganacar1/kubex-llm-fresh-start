from typing import Dict, Any

class ClusterToolManager:
    """Cluster araçlarını yöneten API tool manager"""

    def __init__(self, active_cluster_id: str):
        """
        active_cluster_id: Üzerinde işlem yapılacak olan aktif cluster'ın ID'si.
                           Bu ID, path'lerdeki {cluster_id} yerine otomatik olarak kullanılır.
        """
        self.active_cluster_id = active_cluster_id
        self.tools = self._define_tools()

    def _define_tools(self) -> Dict[str, Any]:
        """Cluster işlemleri için mevcut araçları manuel olarak ve detaylı bir şekilde tanımlar."""
        return {
            "list_clusters": {
                "summary": "Sistemde kayıtlı olan tüm Kubernetes cluster'larını listeler.",
                "description": (
                    "Bu araç, kullanıcının erişebileceği, sisteme daha önceden tanımlanmış tüm Kubernetes "
                    "cluster'larının bir listesini döndürür. Her cluster için isim ve ID gibi temel bilgileri içerir. "
                    "Kullanıcı 'Hangi cluster'lar var?' veya 'Mevcut cluster'ları göster' gibi bir talepte "
                    "bulunduğunda bu araç kullanılmalıdır."
                ),
                "method": "GET",
                "path": "/clusters",
                "parameters": []
            },
            "create_cluster": {
                "summary": "Sisteme yeni bir Kubernetes cluster'ı kaydı oluşturur.",
                "description": (
                    "Bu araç, yönetilecek yeni bir Kubernetes cluster'ı için sistemde bir kayıt oluşturur. "
                    "Bu işlem fiziksel olarak yeni bir cluster kurmaz, sadece mevcut bir cluster'ın yönetilebilmesi "
                    "için bir 'tanım' ekler. Örneğin, 'Faz1 adında yeni bir cluster ekle' talebi için kullanılır."
                ),
                "method": "POST",
                "path": "/clusters",
                "parameters": [
                    {
                        "name": "name",
                        "in": "body",
                        "required": True,
                        "type": "string",
                        "description": "Oluşturulacak cluster kaydı için benzersiz ve açıklayıcı bir isim. Örneğin: 'production-cluster'."
                    }
                ]
            },
            "get_cluster_details": {
                "summary": "Aktif olan cluster'ın yapılandırma ve kimlik detaylarını gösterir.",
                "description": (
                    "Bu araç, şu anda aktif olarak seçili olan cluster'ın kayıt bilgilerini getirir. Bu bilgiler "
                    "arasında cluster'ın adı, ID'si, oluşturulma tarihi gibi statik veriler bulunur. Cluster'ın "
                    "içindeki canlı kaynakları (pod, node sayısı vb.) görmek için 'get_cluster_summary' aracı kullanılmalıdır."
                ),
                "method": "GET",
                "path": f"/clusters/{self.active_cluster_id}",
                "parameters": []
            },
            "get_cluster_summary": {
                "summary": "Aktif cluster'ın canlı kaynak kullanım özetini (node, pod, deployment sayısı) getirir.",
                "description": (
                    "Bu araç, aktif olan cluster'a bağlanarak anlık kaynak durumunu özetler. Döndürdüğü bilgiler "
                    "arasında toplam node sayısı, çalışan/bekleyen pod sayısı, deployment ve service sayıları gibi "
                    "canlı metrikler bulunur. Cluster'ın genel sağlık durumunu ve yoğunluğunu anlamak için kullanılır. "
                    "Örneğin, 'aktif cluster'ın durumu nasıl?' veya 'cluster'daki pod sayılarını özetle'."
                ),
                "method": "GET",
                "path": f"/clusters/summary/{self.active_cluster_id}",
                "parameters": []
            },
            "update_cluster": {
                "summary": "Aktif cluster'ın bağlantı bilgilerini (kubeconfig) günceller.",
                "description": (
                    "Bu araç, aktif olan cluster'a erişim için gerekli olan Kubeconfig dosyasını veya dosyalarını "
                    "sisteme eklemek/güncellemek için kullanılır. Cluster'a bağlantı kurulamadığında veya bağlantı "
                    "bilgileri değiştiğinde bu araç kullanılır. Örneğin, 'aktif cluster için yeni kubeconfig ekle'."
                ),
                "method": "PATCH",
                "path": f"/clusters/{self.active_cluster_id}",
                "parameters": [
                    {
                        "name": "kubeconfigs",
                        "in": "body",
                        "required": True,
                        "type": "array",
                        "description": "Cluster'a eklenecek Kubeconfig dosyalarının içeriğini içeren bir liste."
                    }
                ]
            }
        }