from typing import Dict, Any

class RepositoryToolManager:
    """Helm Repository ve Chart araçlarını yöneten API tool manager"""
    
    def __init__(self, active_cluster_id: str):
        self.active_cluster_id = active_cluster_id
        self.tools = self._define_tools()
    
    def _define_tools(self) -> Dict[str, Any]:
        """Helm Repository ve Chart işlemleri için mevcut araçları tanımlar"""
        return {
            "list_repositories": {
                "summary": "Cluster'a eklenmiş olan tüm Helm repository'lerini listeler.",
                "description": (
                    "Bu araç, Kubernetes cluster'ına daha önce 'add_repository' aracı ile eklenmiş olan tüm Helm "
                    "repository'lerinin bir listesini döndürür. Her repository için kısa adını (name) ve kaynak "
                    "URL'ini gösterir. Kullanıcı, hangi chart kaynaklarının mevcut olduğunu görmek istediğinde bu araç kullanılır. "
                    "Örneğin: 'Hangi repolar ekli?' veya 'Mevcut Helm repository'lerini göster.'"
                ),
                "method": "GET",
                "path": f"/repositories/{self.active_cluster_id}/list",
                "parameters": []
            },
            
            "add_repository": {
                "summary": "Cluster'a yeni bir Helm chart repository'si ekler.",
                "description": (
                    "Bu araç, belirtilen URL'deki Helm chart deposunu, cluster'da kullanılabilir hale getirmek için "
                    "bir kısa ad ile kaydeder. Bu işlemden sonra, bu repository içindeki chart'lar kuruluma hazır olur. "
                    "Örneğin, 'prometheus-community repo'sunu ekle' gibi bir talep için kullanılır."
                ),
                "method": "POST",
                "path": f"/repositories/{self.active_cluster_id}/add",
                "parameters": [
                    {
                        "name": "name",
                        "in": "body",
                        "required": True,
                        "type": "string",
                        "description": "Repository için kullanılacak benzersiz ve kısa ad. Örneğin: 'prometheus-community', 'bitnami'."
                    },
                    {
                        "name": "url",
                        "in": "body",
                        "required": True,
                        "type": "string",
                        "description": "Repository'nin barındırıldığı URL adresi. Örneğin: 'https://prometheus-community.github.io/helm-charts'."
                    }
                ]
            },
            
            "delete_repository": {
                "summary": "İsmi belirtilen Helm repository'sini cluster'dan siler.",
                "description": (
                    "Bu araç, daha önce eklenmiş olan bir Helm repository'sini cluster'ın kaynak listesinden kaldırır. "
                    "Bu işlemden sonra, o repository'ye ait chart'lar artık yüklenemez. Örneğin, 'bitnami repo'sunu sil'."
                ),
                "method": "DELETE",
                "path": f"/repositories/{self.active_cluster_id}/{'{repository_name}'}",
                "parameters": [
                    {
                        "name": "repository_name",
                        "in": "path",
                        "required": True,
                        "type": "string",
                        "description": "Silinecek olan repository'nin 'add_repository' ile eklenirken kullanılan kısa adı."
                    }
                ]
            },
            
            "update_repositories": {
                "summary": "Tüm Helm repository'lerindeki chart listelerini günceller.",
                "description": (
                    "Bu araç, ekli olan tüm Helm repository'lerine bağlanarak en güncel chart ve versiyon bilgilerini "
                    "getirir. Bu, `helm repo update` komutuna eşdeğerdir. Yeni bir chart yüklemeden önce en son "
                    "versiyonların kullanılabilir olduğundan emin olmak için bu aracın çalıştırılması önerilir. "
                    "Örneğin, 'chart listelerini güncelle' veya 'repoları yenile'."
                ),
                "method": "POST",
                "path": f"/repositories/{self.active_cluster_id}/update",
                "parameters": []
            },
            
            "install_chart": {
                "summary": "Belirtilen Helm chart'ını bir uygulama olarak cluster'a yükler (deploy eder).",
                "description": (
                    "Bu araç, bir Helm chart'ını kullanarak bir uygulamayı veya servisi Kubernetes cluster'ına kurar. "
                    "Bu işlem sonucunda bir 'release' (yüklemenin belirli bir örneği) oluşur. "
                    "Örneğin: 'prometheus-community/kube-prometheus-stack chart'ını kube-prometheus namespace'ine 'monitoring' adıyla kur'."
                ),
                "method": "POST",
                "path": f"/repositories/{self.active_cluster_id}/install",
                "parameters": [
                    {
                        "name": "chart",
                        "in": "body",
                        "required": True,
                        "type": "string",
                        "description": "Yüklenecek olan chart'ın tam adı. 'repository_adı/chart_adı' formatında olmalıdır. Örneğin: 'prometheus-community/kube-prometheus-stack'."
                    },
                    {
                        "name": "name",
                        "in": "body",
                        "required": True,
                        "type": "string",
                        "description": "Bu yüklemeye verilecek benzersiz release adı. Örneğin: 'monitoring-stack', 'my-prometheus'."
                    },
                    {
                        "name": "namespace",
                        "in": "body",
                        "required": True,
                        "type": "string",
                        "description": "Uygulamanın kaynaklarının (pod, service vb.) oluşturulacağı Kubernetes namespace'i."
                    },
                    {
                        "name": "values",
                        "in": "body",
                        "required": False,
                        "type": "object",
                        "description": "Chart'ın varsayılan ayarlarını değiştirmek için kullanılan JSON formatında bir objedir. Örneğin: '{\"replicaCount\": 3, \"service\":{\"type\":\"LoadBalancer\"}}'."
                    }
                ]
            },
            
            "check_health": {
                "summary": "Helm operasyonlarını yöneten servisin sağlık durumunu kontrol eder.",
                "description": (
                    "Bu araç, Helm ile ilgili işlemleri (listeleme, ekleme, yükleme vb.) yürüten arka plan servisinin "
                    "ayakta ve çalışır durumda olup olmadığını teyit etmek için kullanılır. Diğer Helm araçları hata "
                    "verdiğinde bir sorun olup olmadığını anlamak için ilk olarak bu kontrol yapılabilir."
                ),
                "method": "GET",
                "path": "/repositories/health",
                "parameters": []
            }
        }