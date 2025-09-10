import yaml
from typing import Dict, Any, List

# Kullanıcı tarafından sağlanan OpenAPI spesifikasyonu
# Gerçek bir uygulamada bu bir dosyadan okunabilir.
OPENAPI_SPEC_YAML = """
openapi: 3.0.0
info:
  title: KUBEX Cluster API
  version: 1.0.0
paths:
  /clusters:
    get:
      tags: [Clusters]
      summary: Mevcut tüm cluster'ları listeler.
      description: Index
      operationId: list_clusters
      responses: {'200': {description: 'Cluster listesi.'}}
    post:
      tags: [Clusters]
      summary: Yeni bir cluster oluşturur.
      description: Create
      operationId: create_cluster
      requestBody:
        content:
          application/json:
            schema:
              type: object
              required: [name] # Body içinde hangi parametrenin zorunlu olduğunu belirtiyoruz
              properties:
                name: {type: string, example: 'Faz1 Cluster', description: 'Oluşturulacak cluster için benzersiz bir isim.'}
      responses: {'200': {description: 'Oluşturulan cluster.'}}
  /clusters/{cluster_id}:
    get:
      tags: [Clusters]
      summary: Belirli bir cluster'ın detaylarını gösterir.
      description: Show
      operationId: get_cluster_details
      parameters:
        - name: cluster_id
          in: path
          required: true
          schema: {type: string}
          description: Detayları gösterilecek cluster'ın ID'si.
      responses: {'200': {description: 'Cluster detayları.'}}
    patch:
      tags: [Clusters]
      summary: Bir cluster'ı günceller (örneğin kubeconfig ekler).
      description: Update
      operationId: update_cluster
      parameters:
        - name: cluster_id
          in: path
          required: true
          schema: {type: string}
          description: Güncellenecek cluster'ın ID'si.
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                kubeconfigs: {type: array, items: {type: object}, description: 'Cluster''a eklenecek Kubeconfig dosyalarının listesi.'}
      responses: {'200': {description: 'Güncellenmiş cluster.'}}
  /clusters/summary/{cluster_id}:
    get:
      tags: [Clusters]
      summary: Bir cluster'ın özet kaynak bilgilerini (node, deployment sayısı vb.) getirir.
      description: Summary
      operationId: get_cluster_summary
      parameters:
        - name: cluster_id
          in: path
          required: true
          schema: {type: string}
          description: Özet bilgisi alınacak cluster'ın ID'si.
      responses: {'200': {description: 'Cluster özeti.'}}
"""

class ToolManager:
    def __init__(self,active_cluster_id):
        self.spec = yaml.safe_load(OPENAPI_SPEC_YAML)
        self.tools = self._parse_spec()

    def _parse_spec(self) -> Dict[str, Any]:
        """OpenAPI spek'ini ayrıştırarak araç sözlüğü oluşturur."""
        tools = {}
        paths = self.spec.get("paths", {})
        for path, methods in paths.items():
            for method, details in methods.items():
                if "operationId" in details:
                    op_id = details["operationId"]
                    tools[op_id] = {
                        "summary": details.get("summary", "No summary available."),
                        "method": method.upper(),
                        "path": path,
                        "parameters": self._get_params(details)
                    }
        return tools

    def _get_params(self, details: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Bir operasyon için gerekli parametreleri ve detaylarını çıkarır."""
        params = []
        # Path, query, etc. parametreleri
        if "parameters" in details:
            for param in details["parameters"]:
                params.append({
                    "name": param["name"],
                    "in": param["in"],
                    "required": param.get("required", False),
                    "type": param.get("schema", {}).get("type", "string"),
                    "description": param.get("description", "")
                })
        # requestBody içindeki parametreler
        if "requestBody" in details:
            schema = details["requestBody"]["content"]["application/json"]["schema"]
            if schema.get("type") == "object":
                required_props = schema.get("required", [])
                for prop_name, prop_details in schema.get("properties", {}).items():
                    params.append({
                        "name": prop_name,
                        "in": "body",
                        "required": prop_name in required_props,
                        "type": prop_details.get("type", "string"),
                        "description": prop_details.get("description", "")
                    })
        return params

    def get_tool(self, name: str) -> Dict[str, Any]:
        """Belirtilen isimdeki aracı döndürür."""
        return self.tools.get(name)

    def get_tools_for_llm(self) -> List[Dict[str, Any]]:
        """
        Araçları, LLM'in fonksiyon çağırma formatına uygun bir listeye dönüştürür.
        """
        formatted_tools = []
        for name, details in self.tools.items():
            properties = {}
            required = []
            
            for param in details["parameters"]:
                # Parametreler için özellikler sözlüğünü oluştur
                properties[param["name"]] = {
                    "type": param.get("type", "string"),
                    "description": param.get("description", f"{param['name']} parametresi.")
                }
                # Zorunlu parametreleri listeye ekle
                if param.get("required"):
                    required.append(param["name"])
            
            # Fonksiyon tanımını oluştur
            function_def = {
                "type": "function",
                "function": {
                    "name": name,
                    "description": details["summary"],
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                    },
                },
            }

            # Eğer zorunlu parametre varsa, 'required' anahtarını ekle
            if required:
                function_def["function"]["parameters"]["required"] = required
                
            formatted_tools.append(function_def)
            
        return formatted_tools

