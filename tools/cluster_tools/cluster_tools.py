import requests
import json
from typing import Dict, Any

class ClusterAPITools:
    def __init__(self, base_url: str = "http://10.67.67.195:8000"):
        self.base_url = base_url

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        print(f"API Çağrısı -> {method} {self.base_url}{endpoint} with {kwargs}")
        
     
        try:
            response = requests.request(method, f"{self.base_url}{endpoint}", **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}

        """# Şimdilik başarılı bir yanıtı simüle ediyoruz.
        return {
            "status": "success",
            "message": f"'{endpoint}' endpoint'i başarıyla çağrıldı.",
            "data": kwargs
        }"""

    def list_clusters(self, **kwargs) -> Dict[str, Any]:
        return self._make_request("GET", "/clusters")

    def create_cluster(self, name: str, **kwargs) -> Dict[str, Any]:
        return self._make_request("POST", "/clusters", json={"name": name})

    def get_cluster_details(self, cluster_id: str, **kwargs) -> Dict[str, Any]:
        return self._make_request("GET", f"/clusters/{cluster_id}")
    
    def get_cluster_summary(self, cluster_id: str, **kwargs) -> Dict[str, Any]:
        return self._make_request("GET", f"/clusters/summary/{cluster_id}")
    
    def update_cluster(self, cluster_id: str, kubeconfigs: list, **kwargs) -> Dict[str, Any]:
        return self._make_request("PATCH", f"/clusters/{cluster_id}", json={"kubeconfigs": kubeconfigs})
