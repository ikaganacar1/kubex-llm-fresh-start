# llm_services/tool_calling_llm_service.py

import json
import re
from typing import Dict, Any, Optional

class ToolCallingLLMService:
    """
    Bir agent'ın araç setinden kullanıcı talebine en uygun aracı seçmekle sorumlu LLM servisi.
    """
    def __init__(self, client: Any):
        self.client = client

    def _build_system_prompt(self, agent_category: str, tools: Dict[str, Any], conversation_summary: str) -> str:
        """Araç seçimi LLM'i için sistem komutunu oluşturur."""
        tools_description_lines = []
        for name, details in tools.items():
            param_list = [f"{p['name']} ({p.get('in', 'N/A')})" for p in details.get("parameters", []) if p.get('name') != "cluster_id"]
            params_str = ", ".join(param_list) if param_list else "Yok"
            tools_description_lines.append(
                f"  - Arac Adi: '{name}'\n"
                f"  - Aciklama: {details.get('summary', '')}\n"
                f"  - Gerekli Parametreler: {params_str}"
            )
        tools_prompt = "\n".join(tools_description_lines)

        context_info = f"\n\n### SON SOHBET OZETI ###\n{conversation_summary}\n" if conversation_summary else ""

        return (
            f"### KİMLİK VE UZMANLIK ALANI ###\n"
            f"Sen, KUBEX platformunda **{agent_category}** konusunda uzmanlaşmış bir asistansın. "
            "Görevin, kullanıcı talebini analiz ederek en uygun ARAÇ'ı seçmek ve mümkün olan parametreleri çıkarmaktır.\n\n"
            f"### ARAÇ SETİ: {agent_category} ###\n{tools_prompt}\n"
            f"{context_info}\n"
            "### GÖREV AKIŞI VE KURALLAR ###\n"
            "1. **Talep Analizi:** Kullanıcı talebini analiz et ve hangi eylemi yapmak istediğini belirle.\n"
            "2. **Araç Seçimi:** Eğer talep ARAÇ SETİ'ndeki bir araçla yapılabiliyorsa, o aracı seç.\n"
            "3. **Parametre Çıkarma:** Kullanıcının verdiği bilgilerden mümkün olan parametreleri çıkar.\n"
            "4. **Sohbet İstisnası:** SADECE eylem yapmayan genel sohbet için 'chat' kullan.\n\n"
            "### ÖNEMLİ: PARAMETRE EKSİKLİĞİ İLE İLGİLİ ###\n"
            "- Eğer bir araç için BAZI parametreler eksikse, yine o aracı seç ve mevcut parametreleri çıkar.\n"
            "- Eksik parametreler için 'chat' kullanma - sistem sonra eksik parametreleri soracak.\n"
            "- Örnek: 'nginx deploymentını 5 pod yap' → scale_deployment aracını seç, replicas=5 ver, deployment_name eksik olsa bile.\n\n"
            "### ÇIKTI FORMATI ###\n"
            "Yanıtını SADECE aşağıdaki JSON formatında ver. Başka hiçbir metin ekleme:\n\n"
            '{"tool_name": "GERCEK_ARAC_ADI", "parameters": {"parametre_adi": "deger"}}\n\n'
            "### GERÇEK ARAÇ ÖRNEKLERI ###\n"
            "- Deployment listesi: get_deployment_config\n"
            "- Config alma: get_deployment_config  \n"
            "- Ölçeklendirme: scale_deployment\n"
            "- Yeniden başlatma: redeploy_deployment\n"
            "- Namespace bilgisi: show_namespace\n"
            "- Sohbet: chat\n\n"
            "### GERÇEK SENARYOLAR ###\n"
            "Kullanıcı: 'metrics-server deploymentının configini istiyorum'\n"
            'Yanıt: {"tool_name": "get_deployment_config", "parameters": {"deployment_name": "metrics-server"}}\n\n'
            "Kullanıcı: 'nginx deploymentını 3 pod yap'\n"
            'Yanıt: {"tool_name": "scale_deployment", "parameters": {"deployment_name": "nginx", "replicas": 3}}\n\n'
            "### KESİN KURAL ###\n"
            "- ASLA 'secilen_aracin_adi' yazma, gerçek araç adını kullan\n"
            "- ASLA 'param1', 'deger1' yazma, gerçek parametre adlarını kullan\n"
            "- Parametre eksikliği nedeniyle 'chat' kullanma\n"
            "- Sadece JSON yanıtı ver, açıklama ekleme"
        )

    def select_tool(self, user_prompt: str, agent_category: str, tools: Dict[str, Any], conversation_summary: str, context_reminder: Optional[str] = None) -> Dict[str, Any]:
        """LLM'den araç seçimi yapmasını ister."""
        system_prompt = self._build_system_prompt(agent_category, tools, conversation_summary)
        
        final_user_prompt = user_prompt
        if context_reminder:
            final_user_prompt = f"{context_reminder}\n\nKullanici mesaji: {user_prompt}"

        print("\n" + "="*50)
        print(f"[{agent_category}] Kullanıcı İsteği: {final_user_prompt}")
        print("="*50 + "\n")

        try:
            response = self.client.chat(
                user_prompt=final_user_prompt, 
                system_prompt=system_prompt, 
                use_history=False  # Tool seçimi için history kullanmayalım
            )
            content = response.get("message", {}).get("content", "{}")

            # Geliştirilmiş JSON çıkarma mantığı
            json_obj = self._extract_json_from_content(content)
            if json_obj:
                return json_obj
            else:
                raise ValueError("Geçerli JSON formatı bulunamadı")

        except Exception as e:
            print(f"[{agent_category}] LLM'den geçerli JSON alınamadı: {e}")
            return {"tool_name": "chat", "parameters": {"response": "Ne istediğinizi anlayamadım, lütfen daha net bir şekilde ifade eder misiniz?"}}

    def _extract_json_from_content(self, content: str) -> Optional[Dict[str, Any]]:
        """İçerikten JSON objesini çıkarmaya çalışır - geliştirilmiş versiyon"""
        
        # Method 1: Standart JSON regex
        json_patterns = [
            r'\{[^{}]*"tool_name"[^{}]*\}',  # Single line JSON
            r'\{.*?"tool_name".*?\}',        # Multi-line JSON
            r'\{.*\}',                       # Any JSON object
        ]
        
        for pattern in json_patterns:
            matches = re.finditer(pattern, content, re.DOTALL | re.IGNORECASE)
            for match in matches:
                json_str = match.group(0)
                try:
                    decoded_json = json.loads(json_str)
                    if "tool_name" in decoded_json:
                        return decoded_json
                except json.JSONDecodeError:
                    continue
        
        # Method 2: Line by line parsing for malformed JSON
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line.startswith('{') and line.endswith('}'):
                try:
                    decoded_json = json.loads(line)
                    if "tool_name" in decoded_json:
                        return decoded_json
                except json.JSONDecodeError:
                    continue
        
        # Method 3: Manual key extraction as fallback
        tool_name_match = re.search(r'"tool_name"\s*:\s*"([^"]+)"', content)
        if tool_name_match:
            tool_name = tool_name_match.group(1)
            # Try to extract parameters if they exist
            params = {}
            params_match = re.search(r'"parameters"\s*:\s*\{([^}]*)\}', content)
            if params_match:
                params_str = params_match.group(1)
                # Simple parameter extraction
                param_matches = re.findall(r'"([^"]+)"\s*:\s*"([^"]+)"', params_str)
                for key, value in param_matches:
                    params[key] = value
            
            return {"tool_name": tool_name, "parameters": params}
        
        return None